import os
import json
import re
import uuid
import requests
from typing import Optional, Dict, Any, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.tools import tool, BaseTool
from langchain_core.messages import HumanMessage
from datetime import datetime
from decimal import Decimal
import base64

from app.models.llm_model import LLMModel
from app.services.dish import DishService
from app.services.intake import IntakeService
from app.schemas.intake import IntakeCreateByName
from app.schemas.chat import DishCard, DishSelectionWidget, WidgetType, WidgetStatus
from app.core.config import settings
from app.utils.logger import agent_logger


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Decimal objects."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class AgentService:
    """AI agent service for handling intelligent interactions using LangChain."""
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY)
        self.vision_llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY)
        self.tools = []  # Will be populated during run_agent
        self.tool_dict = {}
        self.parser = JsonOutputParser()
        
        agent_logger.info("AgentService initialized", "INIT", 
                         model="gpt-4o-mini", vision_enabled=True)
        
        # Clear and focused prompt template for current workflow
        self.prompt_template = ChatPromptTemplate.from_template("""
You are BiteWise, a helpful AI assistant for nutrition and health tracking. 
You help users with general questions and have access to specialized tools for dish searching and YouTube videos.

User message: {message}
{image_context}

Available tools:
{tool_descriptions}

You may call a tool by responding in JSON:
{{
  "use_tool": true,
  "tool_name": "tool_name_here",
  "tool_input": {{...tool input as JSON...}}
}}

If no tool is needed, respond with:
{{
  "use_tool": false,
  "response": "Final natural language response"
}}

FOOD INTAKE WORKFLOW:
When users mention eating or consuming food (e.g., "I ate 2 pizzas", "I had chicken breast", "I consumed some pasta"), follow this workflow:

1. Use the `search_dishes_for_intake` tool to find matching dishes
2. This creates an interactive dish selection widget that shows the user multiple options
3. The user will then select their preferred dish and confirm the portion size
4. The actual intake logging happens after user confirmation (you don't handle this step)

TOOL USAGE GUIDELINES:
- `search_dishes_for_intake`: When users mention eating/consuming food for intake tracking
- `search_dishes`: When users ask about finding dishes, recipes, or nutritional information (not for intake)
- `search_youtube_videos`: When users ask for cooking tutorials, recipe videos, workout instructions, or educational content

Be conversational, friendly, and focus on helping users with their health and nutrition goals.
If images show food items, consider using search tools to help identify or provide information about the foods.
""")

        # Template for final response generation
        self.final_response_template = ChatPromptTemplate.from_template("""
You are BiteWise, a helpful AI assistant for nutrition and health tracking.
A user asked: {original_message}
{image_context}

You used a tool and got this result: {tool_result}

Please provide a friendly, conversational response to the user based on the tool result.
Be helpful and explain what happened. Do not use JSON format - just respond naturally.
Reference the images if they were relevant to the tool usage.

If you created a dish selection widget, explain that you found multiple matching dishes and ask the user to select which one they actually consumed from the options provided.
""")

    @staticmethod
    def extract_portion_from_message(message: str) -> Optional[Decimal]:
        """Extract portion size from user message."""
        # Common portion indicators
        portion_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:x|times|servings?|portions?)',
            r'(\d+(?:\.\d+)?)\s*(?:cups?|tablespoons?|teaspoons?|grams?|ounces?)',
            r'(\d+(?:\.\d+)?)\s*(?:slices?|pieces?|chunks?)',
            r'(\d+(?:\.\d+)?)\s*(?:bowls?|plates?|containers?)',
        ]
        
        for pattern in portion_patterns:
            match = re.search(pattern, message.lower())
            if match:
                try:
                    return Decimal(match.group(1))
                except (ValueError, TypeError):
                    continue
        
        # Default to 1 if no portion specified
        return Decimal('1.0')

    @staticmethod
    def extract_food_terms_from_message(message: str) -> List[str]:
        """Extract food-related terms from user message."""
        # Common food-related words and phrases
        food_indicators = [
            'ate', 'had', 'consumed', 'eaten', 'drank', 'drank', 'snacked on',
            'breakfast', 'lunch', 'dinner', 'meal', 'snack', 'food', 'dish',
            'pizza', 'pasta', 'rice', 'chicken', 'beef', 'fish', 'salad',
            'soup', 'sandwich', 'burger', 'steak', 'curry', 'stir fry',
            'noodles', 'bread', 'toast', 'cereal', 'oatmeal', 'yogurt',
            'fruit', 'vegetables', 'salad', 'smoothie', 'juice', 'coffee',
            'tea', 'water', 'milk', 'soda', 'beer', 'wine', 'cocktail'
        ]
        
        message_lower = message.lower()
        found_terms = []
        
        for term in food_indicators:
            if term in message_lower:
                found_terms.append(term)
        
        return found_terms

    @staticmethod
    def create_dish_card(dish) -> DishCard:
        """Create a dish card for the widget."""
        return DishCard(
            id=dish.id,
            name=dish.name,
            calories=dish.calories,
            protein=dish.protein,
            carbs=dish.carbs,
            fat=dish.fat,
            fiber=dish.fiber,
            image_url=dish.image_url,
            description=dish.description,
            ingredients=dish.ingredients,
            cooking_time=dish.cooking_time,
            difficulty_level=dish.difficulty_level,
            cuisine_type=dish.cuisine_type,
            dietary_tags=dish.dietary_tags,
            allergens=dish.allergens
        )

    def _analyze_image(self, image_data: str, content_type: str = "image/jpeg") -> str:
        """Analyze image content using vision model."""
        try:
            # Create a message with image
            message = HumanMessage(content=[
                {
                    "type": "text",
                    "text": "What food items do you see in this image? Please describe them in detail, including any visible ingredients, cooking methods, and portion sizes. Focus on nutritional information if visible."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{content_type};base64,{image_data}"
                    }
                }
            ])
            
            # Get response from vision model
            response = self.vision_llm.invoke([message])
            
            agent_logger.debug("Image analysis completed", "VISION", 
                             response_length=len(response.content))
            
            return response.content
            
        except Exception as e:
            agent_logger.error(f"Image analysis failed: {str(e)}", "VISION", error=str(e))
            return "I can see there are images, but I'm having trouble analyzing them in detail."

    def _process_image_attachments(self, attachments: Optional[Dict[str, Any]]) -> str:
        """Process image attachments and return analysis context."""
        if not attachments or "images" not in attachments:
            return ""
        
        images = attachments["images"]
        if not images:
            return ""
        
        agent_logger.debug("Processing image attachments", "VISION", 
                         image_count=len(images))
        
        image_analyses = []
        for image in images:
            try:
                # Extract base64 data
                base64_data = image.get("base64_data", "")
                content_type = image.get("content_type", "image/jpeg")
                
                if base64_data:
                    analysis = self._analyze_image(base64_data, content_type)
                    image_analyses.append(analysis)
                else:
                    # Fallback to URL if base64 not available
                    image_url = image.get("url", "")
                    if image_url:
                        image_analyses.append(f"I can see an image at {image_url}, but I need more details to analyze it properly.")
                    
            except Exception as e:
                agent_logger.error(f"Failed to process image: {str(e)}", "VISION", error=str(e))
                image_analyses.append("I can see an image, but I'm having trouble analyzing it.")
        
        if image_analyses:
            combined_analysis = "\n\n".join(image_analyses)
            return f"\n\nImage Analysis:\n{combined_analysis}\n\n"
        
        return ""

    def _create_tools_with_context(self, db: Optional[AsyncSession], current_user_id: Optional[int]) -> List[BaseTool]:
        """Create tools with database and user context."""
        agent_logger.debug("Creating tools with context", "TOOLS", 
                         has_db=db is not None, has_user_id=current_user_id is not None)
        
        @tool
        def search_dishes(search_term: str) -> Dict[str, Any]:
            """Search for dishes by name or description. Use this when users ask about finding dishes, recipes, or nutritional information."""
            try:
                agent_logger.info(f"🔍 Searching dishes for: '{search_term}'", "TOOLS", search_term=search_term)
                
                # Store the async call for later execution
                import asyncio
                loop = asyncio.get_event_loop()
                
                # Create a task for the async call
                async def _search_dishes():
                    return await DishService.search_dishes_by_name(
                        db=db,
                        search_term=search_term,
                        limit=10
                    )
                
                # Run the async function
                result = loop.run_until_complete(_search_dishes())
                
                if not result or not result.get("dishes"):
                    return {
                        "success": False,
                        "message": f"No dishes found matching '{search_term}'",
                        "dishes": []
                    }
                
                dishes = result["dishes"]
                agent_logger.success(f"Found {len(dishes)} dishes", "TOOLS", 
                                   dish_count=len(dishes), search_term=search_term)
                
                # Format dishes for response
                dish_info = []
                for dish in dishes:
                    dish_info.append({
                        "id": dish.id,
                        "name": dish.name,
                        "calories": float(dish.calories) if dish.calories else None,
                        "protein": float(dish.protein) if dish.protein else None,
                        "carbs": float(dish.carbs) if dish.carbs else None,
                        "fat": float(dish.fat) if dish.fat else None,
                        "description": dish.description,
                        "image_url": dish.image_url
                    })
                
                return {
                    "success": True,
                    "message": f"Found {len(dishes)} dishes matching '{search_term}'",
                    "dishes": dish_info
                }
                
            except Exception as e:
                agent_logger.error(f"Dish search failed: {str(e)}", "TOOLS", error=str(e))
                return {
                    "success": False,
                    "message": f"Error searching dishes: {str(e)}",
                    "dishes": []
                }

        @tool  
        def search_dishes_for_intake(search_term: str, user_message: str) -> Dict[str, Any]:
            """Search for dishes to log as food intake. Use this when users mention eating or consuming food."""
            try:
                agent_logger.info(f"🍽️ Searching dishes for intake: '{search_term}'", "TOOLS", 
                               search_term=search_term, user_message=user_message)
                
                # Store the async call for later execution
                import asyncio
                loop = asyncio.get_event_loop()
                
                # Create a task for the async call
                async def _search_dishes_for_intake():
                    return await DishService.search_dishes_by_name(
                        db=db,
                        search_term=search_term,
                        limit=5
                    )
                
                # Run the async function
                result = loop.run_until_complete(_search_dishes_for_intake())
                
                if not result or not result.get("dishes"):
                    return {
                        "success": False,
                        "message": f"No dishes found matching '{search_term}'",
                        "widget": None
                    }
                
                dishes = result["dishes"]
                agent_logger.info(f"🎯 Creating dish selection widget for: '{search_term}'", "WIDGET")
                
                try:
                    # Create dish cards
                    dish_cards = [AgentService.create_dish_card(dish) for dish in dishes]
                    
                    # Create widget
                    widget = DishSelectionWidget(
                        widget_id=str(uuid.uuid4()),
                        widget_type=WidgetType.DISH_SELECTION,
                        title=f"Select your {search_term}",
                        description=f"I found {len(dishes)} dishes matching '{search_term}'. Please select the one you actually consumed:",
                        dishes=dish_cards,
                        status=WidgetStatus.PENDING,
                        search_term=search_term,
                        user_message=user_message
                    )
                    
                    agent_logger.success(f"✅ Dish selection widget created", "WIDGET", 
                                       widget_id=widget.widget_id, dish_count=len(dishes))
                    
                    return {
                        "success": True,
                        "message": f"Found {len(dishes)} dishes matching '{search_term}'",
                        "widget": widget.model_dump()
                    }
                    
                except Exception as e:
                    agent_logger.error(f"Failed to create dish selection widget: {str(e)}", "WIDGET", 
                                     search_term=search_term, error=str(e))
                    return {
                        "success": False,
                        "message": f"Error creating dish selection widget: {str(e)}",
                        "widget": None
                    }
                
            except Exception as e:
                agent_logger.error(f"Dish search for intake failed: {str(e)}", "TOOLS", error=str(e))
                return {
                    "success": False,
                    "message": f"Error searching dishes for intake: {str(e)}",
                    "widget": None
                }

        @tool
        def search_youtube_videos(query: str, max_results: int = 5) -> Dict[str, Any]:
            """Search for YouTube videos related to cooking, recipes, workouts, or nutrition education."""
            try:
                agent_logger.info(f"📺 Searching YouTube for: '{query}'", "TOOLS", query=query, max_results=max_results)
                
                # YouTube Data API search
                api_key = settings.YOUTUBE_API_KEY
                if not api_key:
                    return {
                        "success": False,
                        "message": "YouTube API key not configured",
                        "videos": []
                    }
                
                url = "https://www.googleapis.com/youtube/v3/search"
                params = {
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "maxResults": max_results,
                    "key": api_key,
                    "videoDuration": "medium",  # 4-20 minutes
                    "relevanceLanguage": "en"
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                videos = []
                for item in data.get("items", []):
                    snippet = item.get("snippet", {})
                    video_id = item.get("id", {}).get("videoId")
                    
                    if video_id and snippet:
                        videos.append({
                            "id": video_id,
                            "title": snippet.get("title", ""),
                            "description": snippet.get("description", ""),
                            "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                            "channel": snippet.get("channelTitle", ""),
                            "published_at": snippet.get("publishedAt", ""),
                            "url": f"https://www.youtube.com/watch?v={video_id}"
                        })
                
                agent_logger.success(f"Found {len(videos)} YouTube videos", "TOOLS", 
                                   video_count=len(videos), query=query)
                
                return {
                    "success": True,
                    "message": f"Found {len(videos)} YouTube videos for '{query}'",
                    "videos": videos
                }
                
            except Exception as e:
                agent_logger.error(f"YouTube search failed: {str(e)}", "TOOLS", error=str(e))
                return {
                    "success": False,
                    "message": f"Error searching YouTube: {str(e)}",
                    "videos": []
                }

        # Store tools for access
        self.tools = [search_dishes, search_dishes_for_intake, search_youtube_videos]
        self.tool_dict = {
            "search_dishes": search_dishes,
            "search_dishes_for_intake": search_dishes_for_intake,
            "search_youtube_videos": search_youtube_videos
        }
        
        agent_logger.success(f"Created {len(self.tools)} tools", "TOOLS", 
                           tool_names=[tool.name for tool in self.tools])
        
        return self.tools

    def _get_tool_descriptions(self) -> str:
        """Get tool descriptions for the prompt."""
        descriptions = [
            "search_dishes(search_term: str) - Search for dishes by name or description. Use for finding recipes and nutritional info.",
            "search_dishes_for_intake(search_term: str, user_message: str) - Search for dishes to log as food intake. Use when users mention eating food.",
            "search_youtube_videos(query: str, max_results: int = 5) - Search for YouTube videos about cooking, workouts, or nutrition education."
        ]
        return "\n".join(descriptions)

    async def run_agent(
        self, 
        user_message: str, 
        attachments: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None, 
        current_user_id: Optional[int] = None
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Run the AI agent with optional tool usage and image handling."""
        agent_logger.section_start("Agent Processing", "AGENT")
        agent_logger.info(f"📩 Processing message: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'", "INPUT",
                         user_id=current_user_id, has_attachments=bool(attachments))
        
        try:
            # Process image attachments
            image_context = self._process_image_attachments(attachments)
            
            # Create tools with context
            agent_logger.separator("┈", 40, "SETUP")
            agent_logger.debug("Creating tools with context", "SETUP", 
                             has_db=db is not None, has_user_id=current_user_id is not None)
            
            tools = self._create_tools_with_context(db, current_user_id)
            
            # Get tool descriptions
            tool_descriptions = self._get_tool_descriptions()
            
            # Generate initial prompt
            agent_logger.separator("┈", 40, "LLM")
            agent_logger.debug("Generating prompt and calling LLM", "LLM")
            
            prompt = self.prompt_template.format(
                message=user_message,
                image_context=image_context,
                tool_descriptions=tool_descriptions
            )
            
            # Get LLM response
            response = self.llm.invoke(prompt)
            response_content = response.content
            
            agent_logger.debug("Received LLM response", "LLM", 
                             response_length=len(response_content))
            
            # Parse response
            try:
                parsed_response = json.loads(response_content)
                agent_logger.debug("Parsed LLM response successfully", "LLM", 
                                 use_tool=parsed_response.get("use_tool", False))
            except json.JSONDecodeError:
                # Fallback to natural language response
                agent_logger.debug("LLM response not in JSON format, using as natural language", "LLM")
                return response_content, None
            
            # Handle tool usage
            if parsed_response.get("use_tool", False):
                tool_name = parsed_response.get("tool_name")
                tool_input = parsed_response.get("tool_input", {})
                
                agent_logger.separator("┈", 40, "TOOL")
                agent_logger.info(f"🔧 Executing tool: {tool_name}", "TOOL", 
                               tool_input=tool_input)
                
                if tool_name in self.tool_dict:
                    try:
                        agent_logger.debug("Invoking tool", "TOOL", tool_name=tool_name)
                        
                        # Handle tools (all are now synchronous)
                        tool_func = self.tool_dict[tool_name]
                        
                        # LangChain tools expect a single string input, not keyword arguments
                        if tool_name == "search_dishes":
                            search_term = tool_input.get("search_term", "") if isinstance(tool_input, dict) else str(tool_input)
                            tool_result = tool_func.invoke(search_term)
                        elif tool_name == "search_dishes_for_intake":
                            # For this tool, we need to pass both arguments
                            if isinstance(tool_input, dict):
                                search_term = tool_input.get("search_term", "")
                                user_message = tool_input.get("user_message", "")
                            else:
                                # If tool_input is a string, use it as search_term and empty user_message
                                search_term = str(tool_input)
                                user_message = ""
                            tool_result = tool_func.invoke(search_term, user_message)
                        else:
                            # For other tools, pass the input as is
                            tool_result = tool_func.invoke(str(tool_input))
                        
                        agent_logger.success("Tool execution completed", "TOOL", 
                                           tool_name=tool_name, success=tool_result.get("success", False))
                        
                        # Prepare tool attachments
                        tool_attachments = {
                            "tool_calls": [{
                                "tool_name": tool_name,
                                "tool_input": tool_input,
                                "tool_response": tool_result
                            }]
                        }
                        
                        # Add widgets if present
                        if tool_result.get("widget"):
                            tool_attachments["widgets"] = [tool_result["widget"]]
                        
                        agent_logger.debug("Tool attachments prepared", "TOOL",
                                         has_widgets="widgets" in tool_attachments,
                                         attachment_keys=list(tool_attachments.keys()))
                        
                        # Generate final response
                        agent_logger.separator("┈", 40, "RESPONSE")
                        agent_logger.debug("Generating final response", "RESPONSE")
                        
                        final_prompt = self.final_response_template.format(
                            original_message=user_message,
                            image_context=image_context,
                            tool_result=json.dumps(tool_result, cls=DecimalEncoder)
                        )
                        
                        final_response = self.llm.invoke(final_prompt)
                        final_content = final_response.content
                        
                        # Add image context if present
                        if image_context:
                            final_content = f"I can see the images you've shared. {final_content}"
                        
                        agent_logger.success("Agent response completed", "RESPONSE", 
                                           final_length=len(final_content), tool_used=tool_name, tool_success=tool_result.get("success", False))
                        
                        agent_logger.section_end("Agent Processing", "AGENT", success=tool_result.get("success", False))
                        
                        return final_content, tool_attachments
                        
                    except Exception as e:
                        agent_logger.error(f"Tool execution failed: {str(e)}", "TOOL", 
                                         tool_name=tool_name, error=str(e))
                        error_response = f"I encountered an issue while processing your request: {str(e)}"
                        return error_response, {"tool_calls": [{"tool_name": tool_name, "error": str(e)}]}
                else:
                    agent_logger.error(f"Unknown tool: {tool_name}", "TOOL", tool_name=tool_name)
                    error_response = f"I don't have access to the tool '{tool_name}'."
                    return error_response, {"tool_calls": [{"tool_name": tool_name, "error": "Unknown tool"}]}
            else:
                # No tool usage, return direct response
                response_text = parsed_response.get("response", response_content)
                
                # Add image context if present
                if image_context:
                    response_text = f"I can see the images you've shared. {response_text}"
                
                agent_logger.success("Agent response completed (no tools)", "RESPONSE", 
                                   final_length=len(response_text))
                
                agent_logger.section_end("Agent Processing", "AGENT", success=True)
                
                return response_text, None
                
        except Exception as e:
            agent_logger.error(f"Agent processing failed: {str(e)}", "AGENT", error=str(e))
            agent_logger.section_end("Agent Processing", "AGENT", success=False)
            raise e

    @staticmethod
    async def generate_response(
        user_message: str,
        conversation_context: Optional[str] = None,
        attachments: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None,
        current_user_id: Optional[int] = None
    ) -> Tuple[str, int, int, Optional[Dict[str, Any]]]:
        """
        Generate an AI response with optional tool usage and image handling.
        
        Returns:
            Tuple of (response_content, input_tokens, output_tokens, attachments)
        """
        try:
            agent = AgentService()
            
            # Generate response with image analysis
            response_content, tool_attachments = await agent.run_agent(
                user_message=user_message,
                attachments=attachments,
                db=db,
                current_user_id=current_user_id
            )
            
            # Estimate token usage (rough approximation)
            input_tokens = len(user_message.split()) + 100  # Message + prompt overhead
            
            # Add tokens for image analysis if images are present
            if attachments and "images" in attachments and attachments["images"]:
                # Rough estimation: ~100-200 tokens per image for vision analysis
                image_count = len(attachments["images"])
                input_tokens += image_count * 150  # Conservative estimate for image processing
            
            output_tokens = len(response_content.split()) + 50  # Response + overhead
            
            # Log attachment details
            agent_logger.debug("Final attachments preparation", "RESPONSE",
                             has_tool_attachments=bool(tool_attachments),
                             has_input_attachments=bool(attachments))
            
            # Merge tool attachments with image attachments
            final_attachments = tool_attachments or {}
            if attachments:
                if "images" in attachments:
                    final_attachments["images"] = attachments["images"]
                if "tool_results" in attachments:
                    final_attachments["tool_results"] = attachments.get("tool_results", {})
            
            # Log final attachments
            if final_attachments:
                agent_logger.success("Final attachments prepared", "RESPONSE",
                                   has_widgets="widgets" in final_attachments,
                                   has_images="images" in final_attachments,
                                   has_tool_calls="tool_calls" in final_attachments,
                                   attachment_keys=list(final_attachments.keys()))
            
            return response_content, input_tokens, output_tokens, final_attachments
            
        except Exception as e:
            # Fallback response
            agent_logger.error(f"Agent generate_response failed: {str(e)}", "RESPONSE", error=str(e))
            error_response = f"I'm experiencing some technical difficulties, but I'm here to help with your nutrition and health questions. You asked: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'"
            
            # Still acknowledge images if they were uploaded
            if attachments and "images" in attachments and attachments["images"]:
                error_response = "📷 I can see you've uploaded images! " + error_response
            
            return error_response, 0, 0, attachments
    
    @staticmethod
    async def get_default_model(db: AsyncSession) -> Optional[LLMModel]:
        """Get the default LLM model."""
        # modified for asyncio
        result = await db.execute(
            select(LLMModel).where(LLMModel.is_available == True)
        )
        return result.scalars().first()
    
    @staticmethod
    def calculate_cost(
        input_tokens: int, 
        output_tokens: int, 
        model: LLMModel
    ) -> float:
        """Calculate the cost of the interaction."""
        if not model:
            return 0.0
        
        input_cost = (input_tokens / 1_000_000) * float(model.cost_per_million_input_tokens)
        output_cost = (output_tokens / 1_000_000) * float(model.cost_per_million_output_tokens)
        return input_cost + output_cost 