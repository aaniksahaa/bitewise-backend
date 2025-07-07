import os
import json
import re
import uuid
import requests
from typing import Optional, Dict, Any, Tuple, List
from sqlalchemy.orm import Session
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
        """Extract portion information from user message using regex patterns."""
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
    
    @staticmethod
    def extract_food_terms_from_message(message: str) -> List[str]:
        """Extract potential food terms from user message."""
        # Common intake keywords that suggest food consumption
        intake_keywords = ['ate', 'consumed', 'had', 'eating', 'finished', 'took']
        
        # Check if message contains intake keywords
        message_lower = message.lower()
        if not any(keyword in message_lower for keyword in intake_keywords):
            return []
        
        # Simple extraction - look for nouns after intake keywords
        # This is a basic implementation - in production you'd use NLP libraries
        words = message.split()
        food_terms = []
        
        for i, word in enumerate(words):
            if word.lower() in intake_keywords and i + 1 < len(words):
                # Look for the next few words as potential food terms
                for j in range(i + 1, min(i + 4, len(words))):
                    next_word = words[j].lower().strip('.,!?')
                    if len(next_word) > 2 and next_word not in ['the', 'a', 'an', 'some', 'my']:
                        food_terms.append(next_word)
        
        return food_terms
    
    @staticmethod
    def create_dish_card(dish) -> DishCard:
        """Convert a dish object to a DishCard for widgets."""
        # Get first image URL if available
        image_url = None
        if dish.image_urls and len(dish.image_urls) > 0:
            image_url = dish.image_urls[0]
        
        # Truncate description
        description = dish.description
        if description and len(description) > 100:
            description = description[:97] + "..."
        
        return DishCard(
            id=dish.id,
            name=dish.name,
            description=description,
            cuisine=dish.cuisine,
            image_url=image_url,
            calories=dish.calories,
            protein_g=dish.protein_g,
            carbs_g=dish.carbs_g,
            fats_g=dish.fats_g,
            servings=dish.servings
        )
    
    def _analyze_image(self, image_data: str, content_type: str = "image/jpeg") -> str:
        """
        Analyze an image using OpenAI's vision model to get a compact description.
        
        Args:
            image_data: Base64-encoded image data
            content_type: MIME type of the image
            
        Returns:
            Compact description of the image (under 30 words)
        """
        agent_logger.debug("Analyzing image with vision model", "VISION", 
                          content_type=content_type, data_size=len(image_data))
        
        try:
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
            
            response = self.vision_llm.invoke([message])
            description = response.content.strip()
            
            # Ensure the description is under 30 words
            words = description.split()
            if len(words) > 30:
                description = " ".join(words[:30]) + "..."
            
            agent_logger.success("Image analyzed successfully", "VISION", 
                               description=description, word_count=len(words))
            return description
            
        except Exception as e:
            # Fallback description
            error_msg = f"analysis unavailable: {str(e)[:50]}"
            agent_logger.error("Image analysis failed", "VISION", error=error_msg)
            return f"Image uploaded ({error_msg})"
    
    def _process_image_attachments(self, attachments: Optional[Dict[str, Any]]) -> str:
        """
        Process image attachments and return formatted context string.
        
        Args:
            attachments: Dictionary containing image attachments with base64_data
            
        Returns:
            Formatted string with image descriptions
        """
        if not attachments or "images" not in attachments or not attachments["images"]:
            agent_logger.debug("No image attachments to process", "IMAGES")
            return ""
        
        images = attachments["images"]
        agent_logger.info(f"Processing {len(images)} image attachment(s)", "IMAGES")
        
        image_descriptions = []
        
        for i, img in enumerate(images, 1):
            try:
                # Check if we have base64 data
                base64_data = img.get("base64_data", "")
                content_type = img.get("content_type", "image/jpeg")
                
                if base64_data:
                    description = self._analyze_image(base64_data, content_type)
                    image_descriptions.append(f"Image {i}: {description}")
                    agent_logger.debug(f"Processed image {i}", "IMAGES", description=description)
                else:
                    # Fallback: try URL if no base64 data (for backward compatibility)
                    image_url = img.get("url", "")
                    if image_url:
                        # Convert URL to base64 if needed
                        try:
                            response = requests.get(image_url, timeout=10)
                            if response.status_code == 200:
                                import base64
                                base64_encoded = base64.b64encode(response.content).decode('utf-8')
                                description = self._analyze_image(base64_encoded, content_type)
                                image_descriptions.append(f"Image {i}: {description}")
                                agent_logger.debug(f"Fetched and processed image {i} from URL", "IMAGES")
                            else:
                                image_descriptions.append(f"Image {i}: Image file (could not fetch)")
                                agent_logger.warning(f"Failed to fetch image {i} from URL", "IMAGES", 
                                                   status_code=response.status_code)
                        except Exception as e:
                            image_descriptions.append(f"Image {i}: Image file (fetch failed)")
                            agent_logger.error(f"Error fetching image {i}", "IMAGES", error=str(e))
                    else:
                        image_descriptions.append(f"Image {i}: Image file (no data available)")
                        agent_logger.warning(f"Image {i} has no data or URL", "IMAGES")
            except Exception as e:
                image_descriptions.append(f"Image {i}: Image file (analysis failed)")
                agent_logger.error(f"Failed to process image {i}", "IMAGES", error=str(e))
        
        if image_descriptions:
            result = f"\nAttached images:\n" + "\n".join(image_descriptions) + "\n"
            agent_logger.success("Image attachments processed", "IMAGES", 
                               total_processed=len(image_descriptions))
            return result
        
        return ""
    
    def _create_tools_with_context(self, db: Optional[Session], current_user_id: Optional[int]) -> List[BaseTool]:
        """Create tools with proper context access."""
        
        agent_logger.debug("Creating tools with context", "TOOLS", 
                          has_db=bool(db), has_user_id=bool(current_user_id))
        
        @tool
        def search_dishes(search_term: str) -> Dict[str, Any]:
            """Search for dishes by name or keywords. Use this when the user asks about finding dishes, recipes, or specific foods (but NOT when they mention eating something). Parameter: search_term (string)"""
            agent_logger.info(f"🔍 Searching dishes for: '{search_term}'", "SEARCH")
            
            if db:
                try:
                    result = DishService.search_dishes_by_name(
                        db=db,
                        search_term=search_term,
                        page=1,
                        page_size=10
                    )
                    
                    dishes = []
                    for dish in result.dishes:
                        dishes.append({
                            "id": dish.id,
                            "name": dish.name,
                            "description": dish.description,
                            "cuisine": dish.cuisine,
                            "calories": float(dish.calories) if dish.calories else None,
                            "protein_g": float(dish.protein_g) if dish.protein_g else None
                        })
                    
                    agent_logger.success(f"Found {len(dishes)} dishes", "SEARCH", 
                                       search_term=search_term, total_found=result.total_count)
                    
                    if dishes:
                        dish_names = [dish["name"] for dish in dishes[:3]]
                        agent_logger.info(f"Top results: {', '.join(dish_names)}" + 
                                        (f" (and {len(dishes)-3} more)" if len(dishes) > 3 else ""), 
                                        "SEARCH")
                    
                    return {
                        "success": True,
                        "dishes": dishes,
                        "total_found": result.total_count,
                        "search_term": search_term
                    }
                except Exception as e:
                    agent_logger.error(f"Dish search failed: {str(e)}", "SEARCH", search_term=search_term)
                    return {
                        "success": False,
                        "error": str(e),
                        "search_term": search_term,
                        "dishes": []
                    }
            else:
                agent_logger.error("Database not available for dish search", "SEARCH")
                return {
                    "success": False,
                    "error": "Database not available",
                    "search_term": search_term,
                    "dishes": []
                }

        @tool  
        def search_dishes_for_intake(search_term: str, user_message: str) -> Dict[str, Any]:
            """Search for dishes and create a dish selection widget for intake logging. Use this when users mention eating/consuming food. Parameters: search_term (string), user_message (string - the original user message for portion extraction)"""
            agent_logger.info(f"🍽️ Creating dish selection widget for: '{search_term}'", "WIDGET")
            
            if db:
                try:
                    # Search for dishes
                    result = DishService.search_dishes_by_name(
                        db=db,
                        search_term=search_term,
                        page=1,
                        page_size=5  # Get top 5 for selection
                    )
                    
                    if not result.dishes:
                        agent_logger.warning("No dishes found for intake widget", "WIDGET", search_term=search_term)
                        return {
                            "success": False,
                            "error": f"No dishes found matching '{search_term}'",
                            "search_term": search_term
                        }
                    
                    # Extract portion from user message
                    extracted_portion = AgentService.extract_portion_from_message(user_message)
                    
                    # Convert dishes to dish cards (take top 3)
                    dish_cards = []
                    for dish in result.dishes[:3]:
                        dish_card = AgentService.create_dish_card(dish)
                        dish_cards.append(dish_card)
                    
                    # Create dish selection widget
                    widget_id = f"dish_sel_{uuid.uuid4().hex[:8]}"
                    widget = DishSelectionWidget(
                        widget_id=widget_id,
                        title="Which dish did you consume?",
                        description=f"I found several dishes matching '{search_term}'. Please select the one you actually ate:",
                        search_term=search_term,
                        extracted_portion=extracted_portion,
                        dishes=dish_cards,
                        created_at=datetime.now().isoformat()
                    )
                    
                    agent_logger.success(f"Created dish selection widget with {len(dish_cards)} options", "WIDGET",
                                       widget_id=widget_id, dish_count=len(dish_cards))
                    
                    return {
                        "success": True,
                        "widget": widget.model_dump(),
                        "search_term": search_term,
                        "dishes_found": len(result.dishes)
                    }
                    
                except Exception as e:
                    agent_logger.error(f"Failed to create dish selection widget: {str(e)}", "WIDGET", 
                                     search_term=search_term, error=str(e))
                    return {
                        "success": False,
                        "error": str(e),
                        "search_term": search_term
                    }
            else:
                agent_logger.error("Database not available for dish selection widget", "WIDGET")
                return {
                    "success": False,
                    "error": "Database not available",
                    "search_term": search_term
                }
        
        @tool
        def search_youtube_videos(query: str, max_results: int = 5) -> Dict[str, Any]:
            """Search for YouTube videos by query. Use this when the user asks for cooking tutorials, recipe videos, workout videos, or any educational content that would benefit from video demonstrations. Parameters: query (string), max_results (int, default 5)"""
            agent_logger.info(f"🎥 Searching YouTube for: '{query}'", "YOUTUBE", max_results=max_results)
            
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
                
                agent_logger.debug("Making YouTube API request", "YOUTUBE")
                
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
                    
                    agent_logger.success(f"Found {len(videos)} YouTube videos", "YOUTUBE", 
                                       query=query, total_results=total_results)
                    
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
                    agent_logger.error(f"YouTube API error", "YOUTUBE", 
                                     status_code=response.status_code, query=query)
                    return {
                        "success": False,
                        "error": f"YouTube API returned status code {response.status_code}",
                        "query": query,
                        "videos": []
                    }
                    
            except requests.exceptions.Timeout:
                agent_logger.error("YouTube API request timed out", "YOUTUBE", query=query)
                return {
                    "success": False,
                    "error": "Request to YouTube API timed out",
                    "query": query,
                    "videos": []
                }
            except Exception as e:
                agent_logger.error(f"YouTube search failed: {str(e)}", "YOUTUBE", query=query)
                return {
                    "success": False,
                    "error": str(e),
                    "query": query,
                    "videos": []
                }
        
        tools = [search_dishes, search_dishes_for_intake, search_youtube_videos]
        agent_logger.success(f"Created {len(tools)} tools", "TOOLS", 
                           tool_names=[t.name for t in tools])
        
        return tools
    
    def _get_tool_descriptions(self) -> str:
        """Get formatted tool descriptions."""
        return "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])
    
    def run_agent(
        self, 
        user_message: str, 
        attachments: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None, 
        current_user_id: Optional[int] = None
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Run the agent with a single-pass execution.
        
        Args:
            user_message: The user's text message
            attachments: Optional image attachments and other data
            db: Database session
            current_user_id: Current user ID
            
        Returns:
            Tuple of (response_content, tool_attachments)
        """
        # Start agent processing
        agent_logger.section_start("Agent Processing", "AGENT")
        
        # Log the incoming request
        truncated_message = user_message[:100] + "..." if len(user_message) > 100 else user_message
        agent_logger.info(f"📩 Processing message: '{truncated_message}'", "INPUT",
                         user_id=current_user_id, has_attachments=bool(attachments))
        
        # Process image attachments to get descriptions
        if attachments:
            agent_logger.separator("┈", 30, "VISION")
            image_context = self._process_image_attachments(attachments)
        else:
            image_context = ""
        
        # Create tools with proper context
        agent_logger.separator("┈", 30, "SETUP")
        self.tools = self._create_tools_with_context(db, current_user_id)
        self.tool_dict = {t.name: t for t in self.tools}
        tool_descriptions = self._get_tool_descriptions()
        
        # Prepare input data with image context
        input_data = {
            "message": user_message,
            "image_context": image_context,
            "tool_descriptions": tool_descriptions
        }
        
        # Generate prompt and get LLM response
        agent_logger.separator("┈", 30, "LLM")
        agent_logger.debug("Generating prompt and calling LLM", "LLM")
        prompt = self.prompt_template.format(**input_data)
        response = self.llm.invoke(prompt)
        
        agent_logger.debug("Received LLM response", "LLM", 
                          response_length=len(response.content))
        
        try:
            parsed = self.parser.invoke(response.content)
            agent_logger.debug("Parsed LLM response successfully", "LLM",
                             use_tool=parsed.get("use_tool", False))
        except Exception as e:
            # Fallback if JSON parsing fails
            agent_logger.warning(f"Failed to parse LLM response as JSON: {str(e)}", "LLM")
            fallback_response = f"I'm here to help with your nutrition and health questions! You asked: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'"
            if image_context:
                fallback_response = f"I can see you've shared some images with me. {fallback_response}"
            agent_logger.section_end("Agent Processing", "AGENT", success=False)
            return fallback_response, None
        
        # Check if tool use is requested
        if not parsed.get("use_tool", False):
            response_text = parsed.get("response", "I'm here to help with your nutrition and health questions!")
            if image_context and "I can see" not in response_text and "image" not in response_text.lower():
                response_text = f"I can see the images you've shared. {response_text}"
            
            agent_logger.success("Responding without tool use", "LLM")
            agent_logger.section_end("Agent Processing", "AGENT", success=True)
            return response_text, None
        
        # Execute tool
        tool_name = parsed.get("tool_name", "")
        tool_input = parsed.get("tool_input", {})
        
        agent_logger.separator("┈", 30, "TOOL")
        agent_logger.info(f"🔧 Executing tool: {tool_name}", "TOOL",
                         tool_input=tool_input)
        
        if tool_name not in self.tool_dict:
            agent_logger.error(f"Unknown tool requested: {tool_name}", "TOOL",
                             available_tools=list(self.tool_dict.keys()))
            error_response = f"I wanted to help you with that, but I encountered an issue with the tool '{tool_name}'. How can I assist you with your nutrition questions?"
            if image_context:
                error_response = f"I can see the images you've shared. {error_response}"
            agent_logger.section_end("Agent Processing", "AGENT", success=False)
            return error_response, None
        
        # Execute the tool
        tool = self.tool_dict[tool_name]
        try:
            agent_logger.debug(f"Invoking tool: {tool_name}", "TOOL")
            
            # Handle both old dict format and new direct parameter format
            if isinstance(tool_input, dict):
                tool_output = tool.invoke(tool_input)
            else:
                tool_output = tool.invoke({"input": tool_input})
                
            tool_success = tool_output.get("success", True)
            agent_logger.success(f"Tool execution completed: {tool_name}", "TOOL",
                               success=tool_success)
        except Exception as e:
            agent_logger.error(f"Tool execution failed: {tool_name}", "TOOL", error=str(e))
            tool_output = {"success": False, "error": str(e)}
            tool_success = False
        
        # Prepare tool attachments - handle widgets specially
        tool_attachments = {
            "tool_calls": [{
                "tool_name": tool_name,
                "tool_response": tool_output
            }]
        }
        
        # If this is a dish selection widget, add it to attachments
        if tool_name == "search_dishes_for_intake" and tool_output.get("success") and "widget" in tool_output:
            widget_data = tool_output["widget"]
            # Parse the widget back into DishSelectionWidget object for proper formatting
            widget = DishSelectionWidget(**widget_data)
            tool_attachments["widgets"] = [widget.model_dump()]
            agent_logger.success(f"🎯 Widget added to attachments", "WIDGET",
                               widget_id=widget.widget_id, dishes_count=len(widget.dishes))
        
        agent_logger.debug(f"Tool attachments prepared", "TOOL", 
                         has_widgets="widgets" in tool_attachments,
                         attachment_keys=list(tool_attachments.keys()))
        
        # Generate final response using the natural language template
        agent_logger.separator("┈", 30, "RESPONSE")
        agent_logger.debug("Generating final response", "RESPONSE")
        
        final_input = {
            "original_message": user_message,
            "image_context": image_context,
            "tool_result": json.dumps(tool_output, indent=2, cls=DecimalEncoder)
        }
        
        final_prompt = self.final_response_template.format(**final_input)
        final_response = self.llm.invoke(final_prompt)
        
        # Clean response (remove any potential JSON artifacts)
        final_content = final_response.content.strip()
        
        # Fallback response generation if the final response is too short or seems like an error
        if len(final_content) < 10 or final_content.startswith("{"):
            if tool_output.get("success"):
                if tool_name == "search_dishes":
                    dishes_count = len(tool_output.get("dishes", []))
                    final_content = f"I found {dishes_count} dishes matching your search for '{tool_output.get('search_term', 'your query')}'!"
                elif tool_name == "search_dishes_for_intake":
                    dish_count = tool_output.get("dishes_found", 0)
                    search_term = tool_output.get("search_term", "your query")
                    final_content = f"I found {dish_count} dishes matching '{search_term}'. Please select which one you actually consumed from the options below so I can log your intake accurately!"
                elif tool_name == "search_youtube_videos":
                    videos_count = len(tool_output.get("videos", []))
                    final_content = f"I found {videos_count} YouTube videos for '{tool_output.get('query', 'your search')}'! These videos should be helpful for your request."
                else:
                    final_content = "I've completed your request!"
                    
                # Add image acknowledgment if present
                if image_context:
                    final_content = f"Based on the images you shared, {final_content.lower()}"
            else:
                final_content = f"I tried to help you with that, but encountered an issue: {tool_output.get('error', 'Unknown error')}. How else can I assist you?"
                if image_context:
                    final_content = f"I can see the images you've shared. {final_content}"
        
        agent_logger.success("Agent response completed", "RESPONSE", 
                           final_length=len(final_content), tool_used=tool_name, tool_success=tool_success)
        
        agent_logger.section_end("Agent Processing", "AGENT", success=tool_success)
        
        return final_content, tool_attachments
    
    @staticmethod
    def generate_response(
        user_message: str,
        conversation_context: Optional[str] = None,
        attachments: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None,
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
            response_content, tool_attachments = agent.run_agent(
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
    def get_default_model(db: Session) -> Optional[LLMModel]:
        """Get the default LLM model."""
        return db.query(LLMModel).filter(
            LLMModel.is_available == True
        ).first()
    
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