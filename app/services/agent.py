"""
Agent service for handling AI-powered chat responses.
"""

import json
import logging
import os
import uuid
import requests
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
from langchain_core.messages import HumanMessage
from app.core.config import settings

logger = logging.getLogger(__name__)

class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Decimal objects."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

class AgentService:
    """
    AI Agent service for generating intelligent responses to user queries.
    
    This service handles:
    - General nutrition and health questions
    - Dish search and recommendations
    - Food intake logging assistance with widgets
    - YouTube video search for tutorials
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
                    model="gpt-4o-mini",
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
    def _analyze_image(cls, image_data: str, content_type: str = "image/jpeg") -> str:
        """
        Analyze an image using OpenAI's vision model to get a compact description.
        
        Args:
            image_data: Base64-encoded image data
            content_type: MIME type of the image
            
        Returns:
            Compact description of the image (under 30 words)
        """
        logger.debug(f"🖼️ [AGENT/VISION] Analyzing image with vision model (size: {len(image_data)} chars)")
        
        try:
            # Initialize LLM if needed
            cls._initialize_llm()
            
            # Create a specialized prompt for food image analysis
            analysis_prompt = """
            Analyze this image and provide a very compact description (under 30 words) focusing on:
            - Food items if visible (type, preparation style, portions)
            - Key visual characteristics that would help in food search
            
            Format: "A [adjective] [food item] with [key characteristics]" or similar.
            Be specific about food types but concise. If no food is visible, describe what you see briefly.
            """
            
            # Create data URL for base64 image
            data_url = f"data:{content_type};base64,{image_data}"
            
            # Use HumanMessage with proper content structure for vision
            message = HumanMessage(
                content=[
                    {"type": "text", "text": analysis_prompt},
                    {"type": "image_url", "image_url": {"url": data_url}}
                ]
            )
            
            response = cls.vision_llm.invoke([message])
            description = response.content.strip()
            
            # Ensure the description is under 30 words
            words = description.split()
            if len(words) > 30:
                description = " ".join(words[:30]) + "..."
            
            logger.debug(f"✅ [AGENT/VISION] Image analyzed successfully: '{description}' ({len(words)} words)")
            return description
            
        except Exception as e:
            # Fallback description
            error_msg = f"analysis unavailable: {str(e)[:50]}"
            logger.error(f"❌ [AGENT/VISION] Image analysis failed: {error_msg}")
            return f"Image uploaded ({error_msg})"
    
    @classmethod
    def _process_image_attachments(cls, attachments: Optional[Dict[str, Any]]) -> str:
        """
        Process image attachments and return formatted context string.
        
        Args:
            attachments: Dictionary containing image attachments with base64_data
            
        Returns:
            Formatted string with image descriptions
        """
        if not attachments or "images" not in attachments or not attachments["images"]:
            logger.debug("🖼️ [AGENT/IMAGES] No image attachments to process")
            return ""
        
        images = attachments["images"]
        logger.info(f"🖼️ [AGENT/IMAGES] Processing {len(images)} image attachment(s)")
        
        image_descriptions = []
        
        for i, img in enumerate(images, 1):
            try:
                # Check if we have base64 data
                base64_data = img.get("base64_data", "")
                content_type = img.get("content_type", "image/jpeg")
                
                if base64_data:
                    description = cls._analyze_image(base64_data, content_type)
                    image_descriptions.append(f"Image {i}: {description}")
                    logger.debug(f"🖼️ [AGENT/IMAGES] Processed image {i}: {description}")
                else:
                    # Fallback: try URL if no base64 data
                    image_url = img.get("url", "")
                    if image_url:
                        try:
                            response = requests.get(image_url, timeout=10)
                            if response.status_code == 200:
                                base64_encoded = base64.b64encode(response.content).decode('utf-8')
                                description = cls._analyze_image(base64_encoded, content_type)
                                image_descriptions.append(f"Image {i}: {description}")
                                logger.debug(f"🖼️ [AGENT/IMAGES] Fetched and processed image {i} from URL")
                            else:
                                image_descriptions.append(f"Image {i}: Image file (could not fetch)")
                                logger.warning(f"⚠️ [AGENT/IMAGES] Failed to fetch image {i} from URL (status: {response.status_code})")
                        except Exception as e:
                            image_descriptions.append(f"Image {i}: Image file (fetch failed)")
                            logger.error(f"❌ [AGENT/IMAGES] Error fetching image {i}: {e}")
                    else:
                        image_descriptions.append(f"Image {i}: Image file (no data available)")
                        logger.warning(f"⚠️ [AGENT/IMAGES] Image {i} has no data or URL")
            except Exception as e:
                image_descriptions.append(f"Image {i}: Image file (analysis failed)")
                logger.error(f"❌ [AGENT/IMAGES] Failed to process image {i}: {e}")
        
        if image_descriptions:
            result = f"\nAttached images:\n" + "\n".join(image_descriptions) + "\n"
            logger.info(f"✅ [AGENT/IMAGES] Successfully processed {len(image_descriptions)} images")
            return result
        
        return ""
    
    @classmethod
    def _extract_portion_from_message(cls, message: str) -> Optional[Decimal]:
        """Extract portion information from user message using regex patterns."""
        import re
        
        # Common portion patterns
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:pieces?|slices?|portions?|servings?)',
            r'(\d+(?:\.\d+)?)\s*(?:cups?|bowls?)',
            r'(\d+(?:\.\d+)?)\s*(?:small|medium|large)',
            r'(\d+(?:\.\d+)?)\s*x\s*',  # "2x pizza"
            r'(\d+(?:\.\d+)?)\s+(?:\w+)',  # "2 pizza", "1.5 chicken"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                try:
                    return Decimal(match.group(1))
                except:
                    continue
        
        return None
    
    @classmethod
    def _create_dish_card(cls, dish) -> 'DishCard':
        """Convert a dish object to a DishCard for widgets."""
        from app.schemas.chat import DishCard
        
        # Get first image URL if available
        image_url = None
        if dish.image_urls and len(dish.image_urls) > 0:
            image_url = dish.image_urls[0]
        
        # Truncate description to 2-3 lines (approximately 120 characters)
        description = dish.description
        if description and len(description) > 120:
            description = description[:117] + "..."
        
        # Convert calories to integer if available
        calories = None
        if dish.calories:
            try:
                calories = int(float(dish.calories))
            except (ValueError, TypeError):
                calories = None
        
        return DishCard(
            id=dish.id,
            name=dish.name,
            description=description,
            cuisine=dish.cuisine,
            image_url=image_url,
            calories=calories,
            servings=dish.servings
        )
    
    @classmethod
    def _create_tools_with_context(cls, db: Optional[AsyncSession]) -> List[BaseTool]:
        """Create tools with proper database context."""
        logger.debug("🔧 [AGENT/TOOLS] Creating tools with database context")
        
        @tool
        def search_dishes(search_term: str) -> Dict[str, Any]:
            """Search for dishes by name or keywords. Use this when the user asks about finding dishes, recipes, or specific foods (but NOT when they mention eating something). Parameter: search_term (string)"""
            logger.info(f"🔍 [TOOL/SEARCH] Searching dishes for: '{search_term}'")
            
            return {
                "success": True,
                "search_term": search_term,
                "action": "search_dishes_in_database",
                "message": f"Will search database for dishes matching '{search_term}'"
            }

        @tool  
        def search_dishes_for_intake(search_term: str, user_message: str) -> Dict[str, Any]:
            """Search for dishes and create a dish selection widget for intake logging. Use this when users mention eating/consuming food. Parameters: search_term (string), user_message (string - the original user message for portion extraction)"""
            logger.info(f"🍽️ [TOOL/INTAKE] Creating dish selection widget for: '{search_term}'")
            
            return {
                "success": True,
                "search_term": search_term,
                "user_message": user_message,
                "action": "create_dish_selection_widget",
                "message": f"Will create dish selection widget for '{search_term}'"
            }
        
        @tool
        def search_youtube_videos(query: str, max_results: int = 5) -> Dict[str, Any]:
            """Search for YouTube videos by query. Use this when the user asks for cooking tutorials, recipe videos, workout videos, or any educational content that would benefit from video demonstrations. Parameters: query (string), max_results (int, default 5)"""
            logger.info(f"🎥 [TOOL/YOUTUBE] Searching YouTube for: '{query}' (max: {max_results})")
            
            try:
                url = "https://youtube-v311.p.rapidapi.com/search/"
                
                querystring = {
                    "part": "snippet",
                    "maxResults": str(max_results),
                    "order": "relevance",
                    "q": query,
                    "safeSearch": "moderate",
                    "type": "video",
                    "videoDuration": "medium",
                    "videoEmbeddable": "true"
                }
                
                headers = {
                    "x-rapidapi-key": settings.YOUTUBE_V3_API_KEY,
                    "x-rapidapi-host": "youtube-v311.p.rapidapi.com"
                }
                
                logger.debug("🎥 [TOOL/YOUTUBE] Making YouTube API request")
                
                response = requests.get(url, headers=headers, params=querystring, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    videos = []
                    
                    # Extract video information from the response
                    if "items" in data:
                        for item in data["items"]:
                            snippet = item.get("snippet", {})
                            video_info = {
                                "video_id": item.get("id", {}).get("videoId", ""),
                                "title": snippet.get("title", ""),
                                "description": snippet.get("description", "")[:200] + "..." if len(snippet.get("description", "")) > 200 else snippet.get("description", ""),
                                "channel_title": snippet.get("channelTitle", ""),
                                "channel_id": snippet.get("channelId", ""),
                                "published_at": snippet.get("publishedAt", ""),
                                "publish_time": snippet.get("publishTime", ""),
                                "thumbnail_url": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                                "video_url": f"https://www.youtube.com/watch?v={item.get('id', {}).get('videoId', '')}"
                            }
                            videos.append(video_info)
                    
                    # Extract metadata from API response
                    page_info = data.get("pageInfo", {})
                    total_results = page_info.get("totalResults", len(videos))
                    results_per_page = page_info.get("resultsPerPage", len(videos))
                    next_page_token = data.get("nextPageToken", "")
                    region_code = data.get("regionCode", "")
                    
                    logger.info(f"✅ [TOOL/YOUTUBE] Found {len(videos)} YouTube videos for '{query}'")
                    
                    return {
                        "success": True,
                        "videos": videos,
                        "query": query,
                        "total_results": total_results,
                        "results_per_page": results_per_page,
                        "returned_count": len(videos),
                        "next_page_token": next_page_token,
                        "region_code": region_code
                    }
                else:
                    logger.error(f"❌ [TOOL/YOUTUBE] YouTube API error (status: {response.status_code})")
                    return {
                        "success": False,
                        "error": f"YouTube API returned status code {response.status_code}",
                        "query": query,
                        "videos": []
                    }
                    
            except requests.exceptions.Timeout:
                logger.error("❌ [TOOL/YOUTUBE] YouTube API request timed out")
                return {
                    "success": False,
                    "error": "Request to YouTube API timed out",
                    "query": query,
                    "videos": []
                }
            except Exception as e:
                logger.error(f"❌ [TOOL/YOUTUBE] YouTube search failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "query": query,
                    "videos": []
                }
        
        tools = [search_dishes, search_dishes_for_intake, search_youtube_videos]
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
            
            # Process image attachments if present
            image_context = ""
            if attachments and "images" in attachments:
                logger.info(f"🖼️ [AGENT/IMAGE] Processing {len(attachments['images'])} image attachments")
                image_context = cls._process_image_attachments(attachments)
            
            # Create tools with database context
            tools = cls._create_tools_with_context(db)
            tool_dict = {t.name: t for t in tools}
            tool_descriptions = cls._get_tool_descriptions(tools)
            
            # Build conversation context
            context_str = ""
            if conversation_context:
                logger.debug(f"📝 [AGENT/CONTEXT] Including {len(conversation_context)} previous messages")
                context_str = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in conversation_context[-3:]])
            
            # Create the agent prompt template
            agent_prompt = ChatPromptTemplate.from_template("""
You are BiteWise, a helpful AI assistant for nutrition and health tracking. 
You help users with general questions and have access to specialized tools for dish searching and YouTube videos.

{context}

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
                if image_context and "I can see" not in response_text and "image" not in response_text.lower():
                    response_text = f"I can see the images you've shared. {response_text}"
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
                widget_result = await cls._create_intake_widget(
                    tool_input.get("search_term", ""), 
                    tool_input.get("user_message", ""),
                    db
                )
                if widget_result:
                    tool_attachments = widget_result
                    logger.info(f"✅ [AGENT/WIDGET] Dish selection widget created successfully")
            
            # Create video widget for YouTube search results
            if tool_name == "search_youtube_videos" and tool_output.get("success"):
                logger.info(f"🎥 [AGENT/VIDEO] Creating video selection widget for YouTube results")
                video_widget_result = cls._create_video_widget(
                    tool_output.get("videos", []),
                    tool_output.get("query", ""),
                    tool_output.get("total_results")
                )
                if video_widget_result:
                    tool_attachments = video_widget_result
                    logger.info(f"✅ [AGENT/VIDEO] Video selection widget created successfully")
            
            # Generate final response using the tool result
            logger.info(f"📝 [AGENT/FINAL] Generating final response with tool result")
            
            final_prompt = ChatPromptTemplate.from_template("""
You are BiteWise, a helpful AI assistant for nutrition and health tracking.

The user asked: {original_message}
{image_context}

You used the tool '{tool_name}' and got this result: {tool_result}

Please provide a friendly, conversational response to the user based on the tool result.
Be helpful and explain what happened. Do not use JSON format - just respond naturally.
Reference the images if they were relevant to the tool usage.

If you created a dish selection widget, explain that you found multiple matching dishes and ask the user to select which one they actually consumed from the options provided.

If you found YouTube videos, mention the number of videos found and encourage the user to browse through the interactive video gallery below. Mention that they can click any video to watch it on YouTube.

If you found dishes for search, mention the variety and nutritional information available.
""")
            
            final_input = {
                "original_message": user_message,
                "image_context": image_context,
                "tool_name": tool_name,
                "tool_result": json.dumps(tool_output, indent=2, cls=DecimalEncoder)
            }
            
            final_prompt_formatted = final_prompt.format(**final_input)
            final_response = cls.llm.invoke(final_prompt_formatted)
            final_content = final_response.content.strip()
            
            # Fallback response generation if the final response is too short or seems like an error
            if len(final_content) < 10 or final_content.startswith("{"):
                if tool_output.get("success"):
                    if tool_name == "search_dishes":
                        dishes_count = len(tool_output.get("dishes", []))
                        final_content = f"I found {dishes_count} dishes matching your search for '{tool_output.get('search_term', 'your query')}'! These dishes offer a great variety of nutritional options for your health goals."
                    elif tool_name == "search_dishes_for_intake":
                        dish_count = tool_output.get("dishes_found", 0)
                        search_term = tool_output.get("search_term", "your query")
                        final_content = f"Great! I found {dish_count} dishes matching '{search_term}'. Please select which one you actually consumed from the options below so I can log your intake accurately and track your nutrition!"
                    elif tool_name == "search_youtube_videos":
                        videos_count = len(tool_output.get("videos", []))
                        final_content = f"Perfect! I found {videos_count} helpful cooking videos for '{tool_output.get('query', 'your search')}'! Browse through the interactive video gallery below - you can click on any video to watch it directly on YouTube. These videos should be really helpful for your cooking needs!"
                    else:
                        final_content = "I've completed your request!"
                        
                    # Add image acknowledgment if present
                    if image_context:
                        final_content = f"Based on the images you shared, {final_content.lower()}"
                else:
                    final_content = f"I tried to help you with that, but encountered an issue: {tool_output.get('error', 'Unknown error')}. How else can I assist you with your nutrition and health goals?"
                    if image_context:
                        final_content = f"I can see the images you've shared. {final_content}"
            
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
            
            # Merge with input attachments if present
            if attachments:
                if "images" in attachments:
                    final_attachments["images"] = attachments["images"]
            
            # Calculate token usage
            input_tokens = cls._estimate_tokens(prompt + final_prompt_formatted)
            if image_context:
                # Add tokens for image processing
                image_count = len(attachments.get("images", []))
                input_tokens += image_count * 150  # Conservative estimate for image processing
            
            output_tokens = cls._estimate_tokens(final_content)
            
            logger.info(f"📊 [AGENT/TOKENS] Token usage - Input: {input_tokens}, Output: {output_tokens}")
            logger.info(f"✅ [AGENT/COMPLETE] Response generated successfully (tool: {tool_name})")
            
            return final_content, input_tokens, output_tokens, final_attachments
            
        except Exception as e:
            logger.error(f"❌ [AGENT/ERROR] Error generating agent response: {e}")
            error_response = "I apologize, but I'm having trouble processing your request right now. Please try again later."
            # Still acknowledge images if they were uploaded
            if attachments and "images" in attachments and attachments["images"]:
                error_response = "📷 I can see you've uploaded images! " + error_response
            return error_response, 0, 0, attachments
    
    @classmethod
    async def _execute_dish_search(cls, search_term: str, db: Optional[AsyncSession]) -> Dict[str, Any]:
        """Execute actual database search for dishes using enhanced search logic."""
        if not db:
            return {
                "success": False,
                "error": "Database not available",
                "dishes": []
            }
        
        try:
            from app.services.async_dish import AsyncDishService
            
            # Use enhanced search from AsyncDishService
            logger.info(f"🔍 [AGENT/DB] Using enhanced search for: '{search_term}'")
            search_result = await AsyncDishService.search_dishes_by_name(
                db=db,
                search_term=search_term,
                page=1,
                page_size=10  # Limit to 10 results for agent responses
            )
            
            # Convert dishes to dictionary format for JSON serialization
            dish_list = []
            for dish in search_result.dishes:
                dish_dict = {
                    "id": dish.id,
                    "name": dish.name,
                    "description": dish.description,
                    "cuisine": dish.cuisine,
                    "image_url": dish.image_urls[0] if dish.image_urls else None,
                    "calories": int(float(dish.calories)) if dish.calories else 0,
                    "protein_g": float(dish.protein_g) if dish.protein_g else 0,
                    "carbs_g": float(dish.carbs_g) if dish.carbs_g else 0,
                    "fats_g": float(dish.fats_g) if dish.fats_g else 0,
                    "servings": dish.servings,
                    "prep_time_minutes": dish.prep_time_minutes,
                    "cook_time_minutes": dish.cook_time_minutes
                }
                dish_list.append(dish_dict)
            
            logger.info(f"✅ [AGENT/DB] Enhanced search found {len(dish_list)} dishes for '{search_term}' (total available: {search_result.total_count})")
            
            return {
                "success": True,
                "dishes": dish_list,
                "total_found": search_result.total_count,
                "search_term": search_term,
                "returned_count": len(dish_list)
            }
            
        except Exception as e:
            logger.error(f"❌ [AGENT/DB] Enhanced database search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "dishes": []
            }
    
    @classmethod
    async def _create_intake_widget(cls, search_term: str, user_message: str, db: Optional[AsyncSession]) -> Optional[Dict[str, Any]]:
        """Create a dish selection widget for intake logging using enhanced search."""
        if not db:
            return None
            
        try:
            from app.models.dish import Dish
            from app.schemas.chat import DishSelectionWidget, DishCard, WidgetType, WidgetStatus
            from app.services.async_dish import AsyncDishService
            
            # Use enhanced search from AsyncDishService for better results
            logger.info(f"🔍 [AGENT/WIDGET] Using enhanced search for intake widget: '{search_term}'")
            search_result = await AsyncDishService.search_dishes_by_name(
                db=db,
                search_term=search_term,
                page=1,
                page_size=5  # Limit to 5 results for the widget
            )
            
            # Get the actual dish objects from the search results
            dishes = []
            if search_result.dishes:
                # Convert DishListItem back to Dish objects for widget creation
                from sqlalchemy import select
                dish_ids = [dish.id for dish in search_result.dishes]
                stmt = select(Dish).where(Dish.id.in_(dish_ids))
                result = await db.execute(stmt)
                dishes_dict = {dish.id: dish for dish in result.scalars().all()}
                
                # Maintain the search result order
                dishes = [dishes_dict[dish.id] for dish in search_result.dishes if dish.id in dishes_dict]
            
            if not dishes:
                logger.warning(f"🚫 [AGENT/WIDGET] No dishes found for '{search_term}' using enhanced search")
                return None
            
            # Extract portion from user message
            extracted_portion = cls._extract_portion_from_message(user_message)
            
            # Convert dishes to DishCard format (take top 3)
            dish_cards = []
            for dish in dishes[:3]:
                dish_card = cls._create_dish_card(dish)
                dish_cards.append(dish_card)
            
            # Create widget
            widget_id = f"dish_sel_{uuid.uuid4().hex[:8]}"
            widget = DishSelectionWidget(
                widget_id=widget_id,
                widget_type=WidgetType.DISH_SELECTION,
                status=WidgetStatus.PENDING,
                title="Which dish did you consume?",
                description=f"I found several dishes matching '{search_term}'. Please select the one you actually ate:",
                search_term=search_term,
                extracted_portion=extracted_portion,
                dishes=dish_cards,
                created_at=datetime.utcnow().isoformat()
            )
            
            logger.info(f"✅ [AGENT/WIDGET] Enhanced search created widget with {len(dish_cards)} dishes for '{search_term}' (widget_id: {widget_id}, total_found: {search_result.total_count})")
            
            return {
                "widgets": [widget.dict()]
            }
            
        except Exception as e:
            logger.error(f"❌ [AGENT/WIDGET] Error creating intake widget with enhanced search: {e}")
            return None

    @classmethod
    def _create_video_widget(cls, videos_data: List[Dict[str, Any]], query: str, total_results: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Create a video selection widget for YouTube search results."""
        try:
            from app.schemas.chat import VideoSelectionWidget, VideoData, WidgetType, WidgetStatus
            import uuid
            from datetime import datetime
            
            if not videos_data:
                logger.warning(f"🚫 [AGENT/VIDEO] No videos provided for widget creation")
                return None
            
            # Convert video data to VideoData format
            video_objects = []
            for video in videos_data:
                video_obj = VideoData(
                    video_id=video.get("video_id", ""),
                    title=video.get("title", ""),
                    description=video.get("description", ""),
                    channel_title=video.get("channel_title", ""),
                    thumbnail_url=video.get("thumbnail_url", ""),
                    video_url=video.get("video_url", ""),
                    published_at=video.get("published_at", "")
                )
                video_objects.append(video_obj)
            
            # Create widget
            widget_id = f"video_sel_{uuid.uuid4().hex[:8]}"
            widget = VideoSelectionWidget(
                widget_id=widget_id,
                widget_type=WidgetType.VIDEO_SELECTION,
                status=WidgetStatus.RESOLVED,  # Videos are immediately available
                videos=video_objects,
                query=query,
                total_results=total_results,
                created_at=datetime.utcnow().isoformat()
            )
            
            logger.info(f"🎥 [AGENT/VIDEO] Created video widget with {len(video_objects)} videos for '{query}' (widget_id: {widget_id})")
            
            return {
                "widgets": [widget.dict()]
            }
            
        except Exception as e:
            logger.error(f"❌ [AGENT/VIDEO] Error creating video widget: {e}")
            return None

    @classmethod
    def _estimate_tokens(cls, text: str) -> int:
        """Estimate token count for text (rough approximation)."""
        # Rough estimation: ~4 characters per token for English text
        return max(1, len(text) // 4)
    
    @classmethod
    def get_health_status(cls) -> Dict[str, Any]:
        """Get the health status of the agent service."""
        try:
            # Check if OpenAI API key is available
            api_key_available = bool(os.getenv("OPENAI_API_KEY"))
            
            # Check if YouTube API key is available
            youtube_key_available = bool(getattr(settings, 'YOUTUBE_V3_API_KEY', None))
            
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
                "youtube_key_configured": youtube_key_available,
                "llm_initialized": llm_available,
                "service": "AgentService"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "service": "AgentService"
            }