"""
Agent service for handling AI-powered chat responses.
"""

import json
import logging
import os
import uuid
from typing import Dict, Any, Optional, Tuple, List
import base64
from io import BytesIO
from datetime import datetime
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain_core.tools import tool, BaseTool
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

class AgentService:
    """
    AI Agent service for generating intelligent responses to user queries.
    
    This service handles:
    - General nutrition and health questions
    - Dish search and recommendations
    - Food intake logging assistance
    - Image analysis for food identification
    """
    
    # Class-level LLM instances (will be initialized when needed)
    llm = None
    vision_llm = None
    
    @classmethod
    def _initialize_llm(cls):
        """Initialize the LLM instances if not already done."""
        if cls.llm is None:
            try:
                from langchain_openai import ChatOpenAI
                
                # Initialize text LLM
                cls.llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.7,
                    max_tokens=1000,
                    openai_api_key=os.getenv("OPENAI_API_KEY")
                )
                
                # Initialize vision LLM for image analysis
                cls.vision_llm = ChatOpenAI(
                    model="gpt-4o",
                    temperature=0.3,
                    max_tokens=500,
                    openai_api_key=os.getenv("OPENAI_API_KEY")
                )
                
                logger.info("✅ [AGENT/INIT] LLM instances initialized successfully")
                
            except ImportError as e:
                logger.error(f"❌ [AGENT/INIT] Failed to import required LLM libraries: {e}")
                raise
            except Exception as e:
                logger.error(f"❌ [AGENT/INIT] Failed to initialize LLM instances: {e}")
                raise
    
    @classmethod
    def _create_tools_with_context(cls, db: Optional[AsyncSession]) -> List[BaseTool]:
        """Create tools with proper database context."""
        logger.debug("🔧 [AGENT/TOOLS] Creating tools with database context")
        
        @tool
        def search_dishes(search_term: str) -> Dict[str, Any]:
            """Search for dishes by name or keywords. Use this when the user asks about finding dishes, recipes, or specific foods. Parameter: search_term (string)"""
            logger.info(f"🔍 [TOOL/SEARCH] Searching dishes for: '{search_term}'")
            
            if not db:
                logger.error("❌ [TOOL/SEARCH] Database not available for dish search")
                return {
                    "success": False,
                    "error": "Database not available",
                    "search_term": search_term,
                    "dishes": []
                }
            
            try:
                # Since this is a sync tool but we have async db, we need to handle this properly
                # We'll return a success indicator and let the async wrapper handle the actual DB call
                return {
                    "success": True,
                    "search_term": search_term,
                    "action": "search_dishes_in_database",
                    "message": f"Will search database for dishes matching '{search_term}'"
                }
                
            except Exception as e:
                logger.error(f"❌ [TOOL/SEARCH] Error in dish search: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "search_term": search_term,
                    "dishes": []
                }

        @tool  
        def search_dishes_for_intake(search_term: str) -> Dict[str, Any]:
            """Search for dishes to create a dish selection widget for intake logging. Use this when users mention eating/consuming food and want to log their intake. Parameter: search_term (string)"""
            logger.info(f"🍽️ [TOOL/INTAKE] Creating dish selection for: '{search_term}'")
            
            if not db:
                logger.error("❌ [TOOL/INTAKE] Database not available for intake search")
                return {
                    "success": False,
                    "error": "Database not available",
                    "search_term": search_term
                }
            
            try:
                # This will be handled by the async wrapper
                return {
                    "success": True,
                    "search_term": search_term,
                    "action": "create_dish_selection_widget",
                    "message": f"Will create dish selection widget for '{search_term}'"
                }
                
            except Exception as e:
                logger.error(f"❌ [TOOL/INTAKE] Error in intake search: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "search_term": search_term
                }
        
        tools = [search_dishes, search_dishes_for_intake]
        logger.info(f"✅ [AGENT/TOOLS] Created {len(tools)} tools: {[t.name for t in tools]}")
        
        return tools
    
    @classmethod
    def _get_tool_descriptions(cls, tools: List[BaseTool]) -> str:
        """Get formatted tool descriptions for the LLM."""
        descriptions = []
        for tool in tools:
            descriptions.append(f"- {tool.name}: {tool.description}")
        return "\n".join(descriptions)
    
    @classmethod
    async def generate_response(
        cls,
        user_message: str,
        attachments: Optional[Dict[str, Any]] = None,
        conversation_context: Optional[List[Dict[str, str]]] = None,
        db: Optional[AsyncSession] = None
    ) -> Tuple[str, int, int, Optional[Dict[str, Any]]]:
        """
        Generate an AI response to a user message using proper LLM agent pattern.
        
        Args:
            user_message: The user's message/question
            attachments: Optional attachments (images, etc.)
            conversation_context: Previous conversation messages for context
            db: Database session for real data queries
            
        Returns:
            Tuple of (response_text, input_tokens, output_tokens, response_attachments)
        """
        try:
            logger.info(f"🚀 [AGENT/START] Processing user message: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'")
            
            # Initialize LLM if needed
            cls._initialize_llm()
            
            # Handle empty or None messages
            if not user_message or not user_message.strip():
                logger.warning(f"⚠️ [AGENT/INPUT] Empty or None message received")
                return (
                    "I'd be happy to help! Please ask me a question about nutrition, food, or health.",
                    10, 20, None
                )
            
            # Create tools with database context
            tools = cls._create_tools_with_context(db)
            tool_dict = {t.name: t for t in tools}
            tool_descriptions = cls._get_tool_descriptions(tools)
            
            # Process image attachments if present
            image_context = ""
            if attachments and "images" in attachments:
                logger.info(f"🖼️ [AGENT/IMAGE] Processing {len(attachments['images'])} image attachments")
                image_context = cls._process_image_attachments(attachments["images"])
            
            # Build conversation context
            context_str = ""
            if conversation_context:
                logger.debug(f"📝 [AGENT/CONTEXT] Including {len(conversation_context)} previous messages")
                context_str = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in conversation_context[-3:]])
            
            # Create the agent prompt template
            agent_prompt = ChatPromptTemplate.from_template("""
You are BiteWise, a helpful AI assistant for nutrition and health tracking. You help users with general questions and have access to specialized tools.

{context}

{image_context}

User message: {message}

Available tools:
{tool_descriptions}

You may call a tool by responding in JSON:
{{
  "use_tool": true,
  "tool_name": "tool_name_here",
  "tool_input": {{"parameter_name": "parameter_value"}}
}}

If no tool is needed, respond with:
{{
  "use_tool": false,
  "response": "Your natural language response here"
}}

TOOL USAGE GUIDELINES:
- Use `search_dishes` when users ask about finding dishes, recipes, or nutritional information
- Use `search_dishes_for_intake` when users mention eating/consuming food and want to log their intake
- For general nutrition questions, health advice, or conversation, respond directly without tools

Be conversational, friendly, and focus on helping users with their health and nutrition goals.
""")
            
            # Prepare input data
            input_data = {
                "message": user_message,
                "image_context": image_context,
                "context": f"Previous conversation:\n{context_str}\n" if context_str else "",
                "tool_descriptions": tool_descriptions
            }
            
            # Generate initial response from LLM
            logger.info(f"🤖 [AGENT/LLM] Calling LLM for tool decision")
            prompt = agent_prompt.format(**input_data)
            response = cls.llm.invoke(prompt)
            
            logger.debug(f"✅ [AGENT/LLM] LLM response received (length: {len(response.content)})")
            
            # Parse the LLM response
            parser = JsonOutputParser()
            try:
                parsed = parser.invoke(response.content)
                logger.debug(f"📋 [AGENT/PARSE] Successfully parsed LLM response: use_tool={parsed.get('use_tool', False)}")
            except Exception as e:
                logger.error(f"❌ [AGENT/PARSE] Failed to parse LLM response as JSON: {e}")
                # Fallback to direct response
                fallback_response = "I'm here to help with your nutrition and health questions! How can I assist you today?"
                if image_context:
                    fallback_response = f"I can see you've shared some images with me. {fallback_response}"
                return fallback_response, cls._estimate_tokens(user_message), cls._estimate_tokens(fallback_response), None
            
            # Check if tool use is requested
            if not parsed.get("use_tool", False):
                response_text = parsed.get("response", "I'm here to help with your nutrition and health questions!")
                logger.info(f"💬 [AGENT/DIRECT] Responding without tool use")
                
                input_tokens = cls._estimate_tokens(prompt)
                output_tokens = cls._estimate_tokens(response_text)
                
                return response_text, input_tokens, output_tokens, None
            
            # Execute tool
            tool_name = parsed.get("tool_name", "")
            tool_input = parsed.get("tool_input", {})
            
            logger.info(f"🔧 [AGENT/TOOL] Executing tool: {tool_name} with input: {tool_input}")
            
            if tool_name not in tool_dict:
                logger.error(f"❌ [AGENT/TOOL] Unknown tool requested: {tool_name}")
                error_response = f"I wanted to help you with that, but I encountered an issue. How can I assist you with your nutrition questions?"
                return error_response, cls._estimate_tokens(prompt), cls._estimate_tokens(error_response), None
            
            # Execute the tool
            tool = tool_dict[tool_name]
            try:
                logger.debug(f"⚡ [AGENT/TOOL] Invoking tool: {tool_name}")
                tool_output = tool.invoke(tool_input)
                logger.info(f"✅ [AGENT/TOOL] Tool execution completed: {tool_name}")
            except Exception as e:
                logger.error(f"❌ [AGENT/TOOL] Tool execution failed: {tool_name} - {e}")
                tool_output = {"success": False, "error": str(e)}
            
            # Handle database operations for tools that need async DB access
            if tool_output.get("success") and tool_output.get("action") == "search_dishes_in_database":
                logger.info(f"🗃️ [AGENT/DB] Executing database search for dishes")
                search_result = await cls._execute_dish_search(tool_input.get("search_term", ""), db)
                tool_output.update(search_result)
            
            # Handle special case for intake tool - create widget
            tool_attachments = None
            if tool_name == "search_dishes_for_intake" and tool_output.get("success"):
                logger.info(f"🎯 [AGENT/WIDGET] Creating dish selection widget for intake")
                widget_result = await cls._create_intake_widget(tool_input.get("search_term", ""), db)
                if widget_result:
                    tool_attachments = widget_result
                    logger.info(f"✅ [AGENT/WIDGET] Dish selection widget created successfully")
            
            # Generate final response using the tool result
            logger.info(f"📝 [AGENT/FINAL] Generating final response with tool result")
            
            final_prompt = ChatPromptTemplate.from_template("""
You are BiteWise, a helpful AI assistant for nutrition and health tracking.

The user asked: {original_message}
{image_context}

You used the tool '{tool_name}' and got this result: {tool_result}

Please provide a friendly, conversational response to the user based on the tool result.
Be helpful and explain what happened. Do not use JSON format - just respond naturally.

If you created a dish selection widget, explain that you found multiple matching dishes and ask the user to select which one they actually consumed from the options provided.
""")
            
            final_input = {
                "original_message": user_message,
                "image_context": image_context,
                "tool_name": tool_name,
                "tool_result": json.dumps(tool_output, indent=2)
            }
            
            final_prompt_formatted = final_prompt.format(**final_input)
            final_response = cls.llm.invoke(final_prompt_formatted)
            final_content = final_response.content.strip()
            
            # Prepare final attachments
            final_attachments = {
                "tool_calls": [{
                    "tool_name": tool_name,
                    "tool_input": tool_input,
                    "tool_response": tool_output
                }]
            }
            
            # Add widget to attachments if created
            if tool_attachments:
                final_attachments.update(tool_attachments)
            
            # Calculate token usage
            input_tokens = cls._estimate_tokens(prompt + final_prompt_formatted)
            output_tokens = cls._estimate_tokens(final_content)
            
            logger.info(f"📊 [AGENT/TOKENS] Token usage - Input: {input_tokens}, Output: {output_tokens}")
            logger.info(f"✅ [AGENT/COMPLETE] Response generated successfully (tool: {tool_name})")
            
            return final_content, input_tokens, output_tokens, final_attachments
            
        except Exception as e:
            logger.error(f"❌ [AGENT/ERROR] Error generating agent response: {e}")
            error_response = "I apologize, but I'm having trouble processing your request right now. Please try again later."
            return error_response, 0, 0, None
    
    @classmethod
    async def _create_intake_widget(cls, search_term: str, db: Optional[AsyncSession]) -> Optional[Dict[str, Any]]:
        """Create a dish selection widget for intake logging."""
        if not db:
            return None
            
        try:
            from app.models.dish import Dish
            from app.schemas.chat import DishSelectionWidget, DishCard, WidgetType, WidgetStatus
            from sqlalchemy import or_, func
            
            # Search for dishes that match the search term
            search_term_lower = search_term.lower()
            
            stmt = select(Dish).where(
                or_(
                    func.lower(Dish.name).contains(search_term_lower),
                    func.lower(Dish.description).contains(search_term_lower)
                )
            ).limit(5)  # Limit to 5 results for the widget
            
            result = await db.execute(stmt)
            dishes = result.scalars().all()
            
            if not dishes:
                logger.warning(f"🚫 [AGENT/WIDGET] No dishes found for '{search_term}'")
                return None
            
            # Convert dishes to DishCard format
            dish_cards = []
            for dish in dishes:
                dish_card = DishCard(
                    id=dish.id,
                    name=dish.name,
                    description=dish.description,
                    cuisine=dish.cuisine,
                    image_url=dish.image_urls[0] if dish.image_urls else None,
                    calories=int(float(dish.calories)) if dish.calories else 0,
                    servings=dish.servings
                )
                dish_cards.append(dish_card)
            
            # Create widget
            widget = DishSelectionWidget(
                widget_id=str(uuid.uuid4()),
                widget_type=WidgetType.DISH_SELECTION,
                status=WidgetStatus.PENDING,
                title="Which dish did you consume?",
                description=f"I found several options matching '{search_term}'. Please select the one you had:",
                search_term=search_term,
                dishes=dish_cards,
                created_at=datetime.utcnow().isoformat()
            )
            
            logger.info(f"🎯 [AGENT/WIDGET] Created widget with {len(dish_cards)} dishes for '{search_term}'")
            
            return {
                "widgets": [widget.dict()]
            }
            
        except Exception as e:
            logger.error(f"❌ [AGENT/WIDGET] Error creating intake widget: {e}")
            return None
    
    @classmethod
    def _process_image_attachments(cls, images: List[Dict[str, Any]]) -> str:
        """Process image attachments and return analysis."""
        try:
            if not images:
                return ""
            
            # For now, return a placeholder response
            # In a full implementation, this would use the vision LLM to analyze images
            image_count = len(images)
            return f"I can see {image_count} image(s) that you've shared. While I can process images, the full image analysis feature is still being developed. Please describe what's in the image and I'll do my best to help!"
            
        except Exception as e:
            logger.error(f"❌ [AGENT/IMAGE] Error processing image attachments: {e}")
            return "I had trouble processing the image(s) you shared. Please describe what you'd like help with."
    
    @classmethod
    def _estimate_tokens(cls, text: str) -> int:
        """Estimate token count for text (rough approximation)."""
        # Rough estimation: ~4 characters per token for English text
        return max(1, len(text) // 4)
    
    @classmethod
    async def _execute_dish_search(cls, search_term: str, db: Optional[AsyncSession]) -> Dict[str, Any]:
        """Execute actual database search for dishes."""
        if not db:
            return {
                "success": False,
                "error": "Database not available",
                "dishes": []
            }
        
        try:
            from app.models.dish import Dish
            from sqlalchemy import or_, func
            
            # Search for dishes that match the search term
            search_term_lower = search_term.lower()
            
            stmt = select(Dish).where(
                or_(
                    func.lower(Dish.name).contains(search_term_lower),
                    func.lower(Dish.description).contains(search_term_lower)
                )
            ).limit(10)  # Limit to 10 results
            
            result = await db.execute(stmt)
            dishes = result.scalars().all()
            
            # Convert dishes to dictionary format
            dish_list = []
            for dish in dishes:
                dish_dict = {
                    "id": dish.id,
                    "name": dish.name,
                    "description": dish.description,
                    "cuisine": dish.cuisine,
                    "image_url": dish.image_urls[0] if dish.image_urls else None,
                    "calories": int(float(dish.calories)) if dish.calories else 0,
                    "protein_g": float(dish.protein_g) if dish.protein_g else 0,
                    "carbs_g": float(dish.carbs_g) if dish.carbs_g else 0,
                    "fat_g": float(dish.fat_g) if dish.fat_g else 0,
                    "servings": dish.servings
                }
                dish_list.append(dish_dict)
            
            logger.info(f"🗃️ [AGENT/DB] Found {len(dish_list)} dishes for '{search_term}'")
            
            return {
                "success": True,
                "dishes": dish_list,
                "total_found": len(dish_list),
                "search_term": search_term
            }
            
        except Exception as e:
            logger.error(f"❌ [AGENT/DB] Database search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "dishes": []
            }

    @classmethod
    def get_health_status(cls) -> Dict[str, Any]:
        """Get the health status of the agent service."""
        try:
            # Check if OpenAI API key is available
            api_key_available = bool(os.getenv("OPENAI_API_KEY"))
            
            # Check if LLM instances can be initialized
            llm_available = False
            try:
                cls._initialize_llm()
                llm_available = True
            except Exception:
                pass
            
            return {
                "status": "healthy" if (api_key_available and llm_available) else "degraded",
                "api_key_configured": api_key_available,
                "llm_initialized": llm_available,
                "service": "AgentService"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "service": "AgentService"
            }