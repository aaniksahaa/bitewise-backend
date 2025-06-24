import os
import json
import requests
from typing import Optional, Dict, Any, Tuple, List
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.tools import tool, BaseTool
from langchain_core.messages import HumanMessage
import base64

from app.models.llm_model import LLMModel
from app.services.dish import DishService
from app.services.intake import IntakeService
from app.schemas.intake import IntakeCreateByName
from app.core.config import settings


class AgentService:
    """AI agent service for handling intelligent interactions using LangChain."""
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY)
        self.vision_llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY)
        self.tools = []  # Will be populated during run_agent
        self.tool_dict = {}
        self.parser = JsonOutputParser()
        
        # Updated prompt template to include image context
        self.prompt_template = ChatPromptTemplate.from_template("""
You are BiteWise, a helpful AI assistant for nutrition and health tracking. 
You can help users with general questions and have access to tools for searching dishes, logging food intake, and finding YouTube videos.

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

Be conversational, friendly, and focus on helping users with their health and nutrition goals.
Use tools when appropriate based on the user's message and any attached images:
- If images show food items, consider using the search_dishes tool to find nutritional information or log_intake tool if the user mentions eating something.
- If users ask for cooking tutorials, recipe videos, workout instructions, or any educational content that would benefit from video demonstrations, use the search_youtube_videos tool.
- Use YouTube search for beginners asking how to cook specific dishes, exercise routines, or educational nutrition content.
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
""")
    
    def _analyze_image(self, image_data: str, content_type: str = "image/jpeg") -> str:
        """
        Analyze an image using OpenAI's vision model to get a compact description.
        
        Args:
            image_data: Base64-encoded image data
            content_type: MIME type of the image
            
        Returns:
            Compact description of the image (under 30 words)
        """
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
            
            return description
            
        except Exception as e:
            # Fallback description
            return f"Image uploaded (analysis unavailable: {str(e)[:50]})"
    
    def _process_image_attachments(self, attachments: Optional[Dict[str, Any]]) -> str:
        """
        Process image attachments and return formatted context string.
        
        Args:
            attachments: Dictionary containing image attachments with base64_data
            
        Returns:
            Formatted string with image descriptions
        """
        if not attachments or "images" not in attachments or not attachments["images"]:
            return ""
        
        images = attachments["images"]
        image_descriptions = []
        
        for i, img in enumerate(images, 1):
            try:
                # Check if we have base64 data
                base64_data = img.get("base64_data", "")
                content_type = img.get("content_type", "image/jpeg")
                
                if base64_data:
                    description = self._analyze_image(base64_data, content_type)
                    image_descriptions.append(f"Image {i}: {description}")
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
                            else:
                                image_descriptions.append(f"Image {i}: Image file (could not fetch)")
                        except Exception as e:
                            image_descriptions.append(f"Image {i}: Image file (fetch failed)")
                    else:
                        image_descriptions.append(f"Image {i}: Image file (no data available)")
            except Exception as e:
                image_descriptions.append(f"Image {i}: Image file (analysis failed)")
        
        if image_descriptions:
            return f"\nAttached images:\n" + "\n".join(image_descriptions) + "\n"
        
        return ""
    
    def _create_tools_with_context(self, db: Optional[Session], current_user_id: Optional[int]) -> List[BaseTool]:
        """Create tools with proper context access."""
        
        @tool
        def search_dishes(search_term: str) -> Dict[str, Any]:
            """Search for dishes by name or keywords. Use this when the user asks about finding dishes, recipes, or specific foods. Parameter: search_term (string)"""
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
                    
                    return {
                        "success": True,
                        "dishes": dishes,
                        "total_found": result.total_count,
                        "search_term": search_term
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "search_term": search_term,
                        "dishes": []
                    }
            else:
                return {
                    "success": False,
                    "error": "Database not available",
                    "search_term": search_term,
                    "dishes": []
                }

        @tool  
        def log_intake(dish_name: str, portion_size: float = 1.0) -> Dict[str, Any]:
            """Log a food intake for the user. Use this when the user mentions eating something or wants to track their food consumption. Parameters: dish_name (string), portion_size (float, default 1.0)"""
            if db and current_user_id:
                try:
                    from datetime import datetime
                    
                    intake_data = IntakeCreateByName(
                        dish_name=dish_name,
                        portion_size=portion_size,
                        intake_time=datetime.now(),
                        water_ml=None
                    )
                    
                    result = IntakeService.create_intake_by_name(
                        db=db,
                        intake_data=intake_data,
                        current_user_id=current_user_id
                    )
                    
                    return {
                        "success": True,
                        "intake_id": result.id,
                        "dish_name": result.dish.name,
                        "portion_size": float(result.portion_size),
                        "calories": float(result.dish.calories) if result.dish.calories else None,
                        "logged_at": result.intake_time.isoformat()
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "dish_name": dish_name
                    }
            else:
                return {
                    "success": False,
                    "error": "Database or user context not available",
                    "dish_name": dish_name
                }
        
        @tool
        def search_youtube_videos(query: str, max_results: int = 5) -> Dict[str, Any]:
            """Search for YouTube videos by query. Use this when the user asks for cooking tutorials, recipe videos, workout videos, or any educational content that would benefit from video demonstrations. Parameters: query (string), max_results (int, default 5)"""
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
                    return {
                        "success": False,
                        "error": f"YouTube API returned status code {response.status_code}",
                        "query": query,
                        "videos": []
                    }
                    
            except requests.exceptions.Timeout:
                return {
                    "success": False,
                    "error": "Request to YouTube API timed out",
                    "query": query,
                    "videos": []
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "query": query,
                    "videos": []
                }
        
        return [search_dishes, log_intake, search_youtube_videos]
    
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
        # Process image attachments to get descriptions
        image_context = self._process_image_attachments(attachments)
        
        # Create tools with proper context
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
        prompt = self.prompt_template.format(**input_data)
        response = self.llm.invoke(prompt)
        
        try:
            parsed = self.parser.invoke(response.content)
        except Exception as e:
            # Fallback if JSON parsing fails
            fallback_response = f"I'm here to help with your nutrition and health questions! You asked: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'"
            if image_context:
                fallback_response = f"I can see you've shared some images with me. {fallback_response}"
            return fallback_response, None
        
        # Check if tool use is requested
        if not parsed.get("use_tool", False):
            response_text = parsed.get("response", "I'm here to help with your nutrition and health questions!")
            if image_context and "I can see" not in response_text and "image" not in response_text.lower():
                response_text = f"I can see the images you've shared. {response_text}"
            return response_text, None
        
        # Execute tool
        tool_name = parsed.get("tool_name", "")
        tool_input = parsed.get("tool_input", {})
        
        if tool_name not in self.tool_dict:
            error_response = f"I wanted to help you with that, but I encountered an issue with the tool '{tool_name}'. How can I assist you with your nutrition questions?"
            if image_context:
                error_response = f"I can see the images you've shared. {error_response}"
            return error_response, None
        
        # Execute the tool
        tool = self.tool_dict[tool_name]
        try:
            # Handle both old dict format and new direct parameter format
            if isinstance(tool_input, dict):
                tool_output = tool.invoke(tool_input)
            else:
                tool_output = tool.invoke({"input": tool_input})
        except Exception as e:
            tool_output = {"success": False, "error": str(e)}
        
        # Prepare tool attachments
        tool_attachments = {
            "tool_calls": [{
                "tool_name": tool_name,
                "tool_response": tool_output
            }]
        }
        
        # Generate final response using the natural language template
        final_input = {
            "original_message": user_message,
            "image_context": image_context,
            "tool_result": json.dumps(tool_output, indent=2)
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
                elif tool_name == "log_intake":
                    final_content = f"Great! I've logged your {tool_output.get('dish_name', 'food intake')} successfully."
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
            input_tokens = len(user_message.split()) + 50  # Message + prompt overhead
            
            # Add tokens for image analysis if images are present
            if attachments and "images" in attachments and attachments["images"]:
                # Rough estimation: ~100-200 tokens per image for vision analysis
                image_count = len(attachments["images"])
                input_tokens += image_count * 150  # Conservative estimate for image processing
            
            output_tokens = len(response_content.split()) + 10  # Response + overhead
            
            # Merge tool attachments with image attachments
            final_attachments = tool_attachments or {}
            if attachments:
                if "images" in attachments:
                    final_attachments["images"] = attachments["images"]
                if "tool_results" in attachments:
                    final_attachments["tool_results"] = attachments.get("tool_results", {})
            
            return response_content, input_tokens, output_tokens, final_attachments
            
        except Exception as e:
            # Fallback response
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