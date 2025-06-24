"""AI agent service for handling intelligent interactions using LangChain."""

import json
from typing import Any, Dict, List, Optional, Tuple

import requests
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI
from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.intake import Intake
from app.models.llm_model import LLMModel
from app.schemas.intake import IntakeCreateByName, IntakeUpdate
from app.services.dish import DishService
from app.services.intake import IntakeService


class AgentService:
    """AI agent service for handling intelligent interactions using LangChain."""

    def __init__(self):
        """Initialize the AI agent service with LLM models and configurations."""
        self.llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY)
        self.vision_llm = ChatOpenAI(
            model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY
        )
        self.tools = []  # Will be populated during run_agent
        self.tool_dict = {}
        self.parser = JsonOutputParser()

        # Updated prompt template to include image context
        self.prompt_template = ChatPromptTemplate.from_template(
            """
You are BiteWise, a helpful AI assistant for nutrition and health tracking.
You can help users with general questions and have access to tools for searching dishes, logging food intake, viewing recent intake records, updating existing intake records, removing intake records, and finding YouTube videos.

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
- If users want to see their recent food intake records, use the get_recent_intakes tool. IMPORTANT: When displaying intake records, always show the intake ID prominently (e.g., "ID: 123 - Dish Name") so users can easily reference them for updates or deletions.
- If users want to modify their previously logged food intake (change portion size, dish, or add water), use the update_intake tool. You may need to use get_recent_intakes first to help them identify which intake to update.
- If users want to delete/remove a previously logged food intake, use the remove_intake tool. You may need to use get_recent_intakes first to help them identify which intake to remove.
- If users ask for cooking tutorials, recipe videos, workout instructions, or any educational content that would benefit from video demonstrations, use the search_youtube_videos tool.
- Use YouTube search for beginners asking how to cook specific dishes, exercise routines, or educational nutrition content.
"""
        )

        # Template for final response generation
        self.final_response_template = ChatPromptTemplate.from_template(
            """
You are BiteWise, a helpful AI assistant for nutrition and health tracking.
A user asked: {original_message}
{image_context}

You used a tool and got this result: {tool_result}

Please provide a friendly, conversational response to the user based on the tool result.
Be helpful and explain what happened. Do not use JSON format - just respond naturally.
Reference the images if they were relevant to the tool usage.

IMPORTANT: If the tool result contains intake records (like from get_recent_intakes), make sure to prominently display the intake ID for each record so users can easily reference them for updates or deletions. Format it like "ID: 123 - Dish Name" or similar.
"""
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
                    {"type": "image_url", "image_url": {"url": data_url}},
                ]
            )

            response = self.vision_llm.invoke([message])
            description = response.content.strip()

            # Ensure the description is under 30 words
            words = description.split()
            if len(words) > 30:
                description = " ".join(words[:30]) + "..."

            return description

        except Exception:
            # Fallback description
            return "Image uploaded (analysis unavailable)"

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

                                base64_encoded = base64.b64encode(
                                    response.content
                                ).decode("utf-8")
                                description = self._analyze_image(
                                    base64_encoded, content_type
                                )
                                image_descriptions.append(f"Image {i}: {description}")
                            else:
                                image_descriptions.append(
                                    f"Image {i}: Image file (could not fetch)"
                                )
                        except Exception:
                            image_descriptions.append(
                                f"Image {i}: Image file (fetch failed)"
                            )
                    else:
                        image_descriptions.append(
                            f"Image {i}: Image file (no data available)"
                        )
            except Exception:
                image_descriptions.append(f"Image {i}: Image file (analysis failed)")

        if image_descriptions:
            return "\nAttached images:\n" + "\n".join(image_descriptions) + "\n"

        return ""

    def _create_tools_with_context(
        self, db: Optional[Session], current_user_id: Optional[int]
    ) -> List[BaseTool]:
        """Create tools with database and user context."""

        @tool
        def search_dishes(search_term: str) -> Dict[str, Any]:
            """
            Search for dishes by name or ingredient.

            Use this tool to find dishes in the database that match the search term.
            Useful when users ask about specific foods or want nutritional information.
            """
            try:
                if not db:
                    return {"success": False, "error": "Database not available"}

                dish_service = DishService(db)
                dishes = dish_service.search_dishes(search_term, limit=10)

                result_dishes = []
                for dish in dishes:
                    dish_data = {
                        "id": dish.id,
                        "name": dish.name,
                        "calories_per_100g": float(dish.calories_per_100g),
                        "protein_per_100g": float(dish.protein_per_100g),
                        "carbs_per_100g": float(dish.carbs_per_100g),
                        "fat_per_100g": float(dish.fat_per_100g),
                        "fiber_per_100g": float(dish.fiber_per_100g or 0),
                        "image_url": dish.image_url,
                        "description": dish.description,
                    }
                    result_dishes.append(dish_data)

                return {
                    "success": True,
                    "dishes": result_dishes,
                    "count": len(result_dishes),
                    "search_term": search_term,
                }

            except Exception:
                return {
                    "success": False,
                    "error": "Failed to search dishes",
                    "search_term": search_term,
                }

        @tool
        def log_intake(dish_name: str, portion_size: float = 1.0) -> Dict[str, Any]:
            """
            Log food intake for the current user.

            Use this tool when users mention eating something or want to track their food.
            portion_size is a multiplier (1.0 = standard portion, 0.5 = half portion, etc.)
            """
            try:
                if not db or not current_user_id:
                    return {"success": False, "error": "User authentication required"}

                intake_service = IntakeService(db)
                intake_data = IntakeCreateByName(
                    dish_name=dish_name, portion_size=portion_size
                )

                new_intake = intake_service.create_intake_by_name(
                    current_user_id, intake_data
                )

                return {
                    "success": True,
                    "intake_id": new_intake.id,
                    "dish_name": dish_name,
                    "portion_size": portion_size,
                    "calories": float(new_intake.calories),
                    "protein": float(new_intake.protein),
                    "carbs": float(new_intake.carbs),
                    "fat": float(new_intake.fat),
                    "timestamp": new_intake.timestamp.isoformat(),
                }

            except Exception:
                return {
                    "success": False,
                    "error": f"Failed to log intake for {dish_name}",
                    "dish_name": dish_name,
                }

        @tool
        def search_youtube_videos(query: str, max_results: int = 5) -> Dict[str, Any]:
            """
            Search for YouTube videos related to cooking, nutrition, or fitness.

            Use this tool when users ask for:
            - Cooking tutorials or recipes
            - Workout or exercise demonstrations
            - Nutrition education content
            - How-to guides for food preparation
            """
            try:
                # Using YouTube Data API v3
                api_key = getattr(settings, "YOUTUBE_API_KEY", None)
                if not api_key:
                    return {
                        "success": False,
                        "error": "YouTube API key not configured",
                        "query": query,
                    }

                url = "https://www.googleapis.com/youtube/v3/search"
                params = {
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "maxResults": min(max_results, 10),
                    "key": api_key,
                    "order": "relevance",
                    "safeSearch": "moderate",
                    "regionCode": "US",
                }

                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                videos = []
                for item in data.get("items", []):
                    video = {
                        "title": item["snippet"]["title"],
                        "description": item["snippet"]["description"][:200] + "...",
                        "video_id": item["id"]["videoId"],
                        "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                        "channel": item["snippet"]["channelTitle"],
                        "published_at": item["snippet"]["publishedAt"],
                    }
                    videos.append(video)

                return {
                    "success": True,
                    "videos": videos,
                    "count": len(videos),
                    "query": query,
                }

            except requests.exceptions.RequestException:
                return {
                    "success": False,
                    "error": "Failed to connect to YouTube API",
                    "query": query,
                }
            except Exception:
                return {
                    "success": False,
                    "error": "Failed to search YouTube videos",
                    "query": query,
                }

        @tool
        def update_intake(
            intake_id: int,
            portion_size: Optional[float] = None,
            dish_name: Optional[str] = None,
            water_ml: Optional[int] = None,
        ) -> Dict[str, Any]:
            """
            Update an existing food intake record.

            Use this tool when users want to modify their previously logged food:
            - Change portion size
            - Change the dish/food item
            - Add or update water intake
            Users should specify the intake_id from their recent intake records.
            """
            try:
                if not db or not current_user_id:
                    return {"success": False, "error": "User authentication required"}

                intake_service = IntakeService(db)

                # Get the existing intake to verify ownership
                existing_intake = (
                    db.query(Intake)
                    .filter(
                        and_(Intake.id == intake_id, Intake.user_id == current_user_id)
                    )
                    .first()
                )

                if not existing_intake:
                    return {
                        "success": False,
                        "error": f"Intake record {intake_id} not found or not accessible",
                        "intake_id": intake_id,
                    }

                # Prepare update data
                update_data = IntakeUpdate()
                if portion_size is not None:
                    update_data.portion_size = portion_size
                if dish_name is not None:
                    update_data.dish_name = dish_name
                if water_ml is not None:
                    update_data.water_ml = water_ml

                # Update the intake
                updated_intake = intake_service.update_intake(intake_id, update_data)

                return {
                    "success": True,
                    "intake_id": updated_intake.id,
                    "dish_name": updated_intake.dish.name,
                    "portion_size": float(updated_intake.portion_size),
                    "calories": float(updated_intake.calories),
                    "protein": float(updated_intake.protein),
                    "carbs": float(updated_intake.carbs),
                    "fat": float(updated_intake.fat),
                    "water_ml": updated_intake.water_ml,
                    "timestamp": updated_intake.timestamp.isoformat(),
                }

            except Exception:
                return {
                    "success": False,
                    "error": f"Failed to update intake record {intake_id}",
                    "intake_id": intake_id,
                }

        @tool
        def get_recent_intakes(limit: int = 5) -> Dict[str, Any]:
            """
            Get the user's recent food intake records.

            Use this tool when users want to see their recent food logs or need to identify intake IDs for updates/deletions.
            Always display intake IDs prominently in the response.
            """
            try:
                if not db or not current_user_id:
                    return {"success": False, "error": "User authentication required"}

                intake_service = IntakeService(db)
                intakes = intake_service.get_user_intakes(
                    current_user_id, limit=min(limit, 20)
                )

                result_intakes = []
                for intake in intakes:
                    intake_data = {
                        "id": intake.id,
                        "dish_name": intake.dish.name,
                        "portion_size": float(intake.portion_size),
                        "calories": float(intake.calories),
                        "protein": float(intake.protein),
                        "carbs": float(intake.carbs),
                        "fat": float(intake.fat),
                        "water_ml": intake.water_ml,
                        "timestamp": intake.timestamp.isoformat(),
                    }
                    result_intakes.append(intake_data)

                return {
                    "success": True,
                    "intakes": result_intakes,
                    "count": len(result_intakes),
                }

            except Exception:
                return {
                    "success": False,
                    "error": "Failed to retrieve recent intakes",
                }

        @tool
        def remove_intake(intake_id: int) -> Dict[str, Any]:
            """
            Remove/delete a food intake record.

            Use this tool when users want to delete a previously logged food intake.
            Users should specify the intake_id from their recent intake records.
            """
            try:
                if not db or not current_user_id:
                    return {"success": False, "error": "User authentication required"}

                # Get the existing intake to verify ownership and get dish name
                existing_intake = (
                    db.query(Intake)
                    .options(joinedload(Intake.dish))
                    .filter(
                        and_(Intake.id == intake_id, Intake.user_id == current_user_id)
                    )
                    .first()
                )

                if not existing_intake:
                    return {
                        "success": False,
                        "error": f"Intake record {intake_id} not found or not accessible",
                        "intake_id": intake_id,
                    }

                dish_name = existing_intake.dish.name

                # Delete the intake
                intake_service = IntakeService(db)
                intake_service.delete_intake(intake_id)

                return {
                    "success": True,
                    "intake_id": intake_id,
                    "dish_name": dish_name,
                    "message": f"Successfully removed intake record for {dish_name}",
                }

            except Exception:
                return {
                    "success": False,
                    "error": f"Failed to remove intake record {intake_id}",
                    "intake_id": intake_id,
                }

        return [
            search_dishes,
            log_intake,
            search_youtube_videos,
            update_intake,
            get_recent_intakes,
            remove_intake,
        ]

    def _get_tool_descriptions(self) -> str:
        """Get formatted descriptions of available tools."""
        return "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])

    def run_agent(
        self,
        user_message: str,
        attachments: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None,
        current_user_id: Optional[int] = None,
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Run the AI agent to process user message with optional image attachments.

        Args:
            user_message: The user's text message
            attachments: Optional dictionary containing image attachments
            db: Database session for tool operations
            current_user_id: Current user ID for personalized responses

        Returns:
            Tuple of (response_content, tool_attachments)
        """
        # Process image attachments for context
        image_context = self._process_image_attachments(attachments)

        # Create tools with current context
        self.tools = self._create_tools_with_context(db, current_user_id)
        self.tool_dict = {tool.name: tool for tool in self.tools}

        # Prepare input for the prompt
        prompt_input = {
            "message": user_message,
            "image_context": image_context,
            "tool_descriptions": self._get_tool_descriptions(),
        }

        # Generate the prompt and get AI response
        prompt = self.prompt_template.format(**prompt_input)

        try:
            response = self.llm.invoke(prompt)
            response_content = response.content.strip()

            # Parse the JSON response
            try:
                parsed = json.loads(response_content)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                fallback_response = "I'm here to help with your nutrition and health questions! Could you please rephrase your request?"
                if image_context:
                    fallback_response = f"I can see you've shared some images with me. {fallback_response}"
                return fallback_response, None

        except Exception:
            # Fallback response if LLM call fails
            fallback_response = "I'm experiencing some technical difficulties, but I'm here to help with your nutrition and health questions!"
            if image_context:
                fallback_response = (
                    f"I can see you've shared some images with me. {fallback_response}"
                )
            return fallback_response, None

        # Check if tool use is requested
        if not parsed.get("use_tool", False):
            response_text = parsed.get(
                "response", "I'm here to help with your nutrition and health questions!"
            )
            if (
                image_context
                and "I can see" not in response_text
                and "image" not in response_text.lower()
            ):
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
        except Exception:
            tool_output = {"success": False, "error": "Tool execution failed"}

        # Prepare tool attachments
        tool_attachments = {
            "tool_calls": [{"tool_name": tool_name, "tool_response": tool_output}]
        }

        # Generate final response using the natural language template
        final_input = {
            "original_message": user_message,
            "image_context": image_context,
            "tool_result": json.dumps(tool_output, indent=2),
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
                elif tool_name == "update_intake":
                    final_content = f"Perfect! I've updated your intake record for {tool_output.get('dish_name', 'food')} successfully."
                elif tool_name == "get_recent_intakes":
                    intakes_count = len(tool_output.get("intakes", []))
                    intakes = tool_output.get("intakes", [])

                    if intakes:
                        # Create a formatted list of intakes with IDs prominently displayed
                        intake_list = []
                        for intake in intakes:
                            intake_id = intake.get("id", "Unknown")
                            dish_name = intake.get("dish_name", "Unknown dish")
                            portion_size = intake.get("portion_size", 1.0)
                            calories = intake.get("calories")
                            water_ml = intake.get("water_ml")

                            intake_info = f"ID: {intake_id} - {dish_name} ({portion_size} portions)"
                            if calories:
                                intake_info += f" - {calories} calories"
                            if water_ml:
                                intake_info += f" - {water_ml}ml water"

                            intake_list.append(intake_info)

                        final_content = (
                            f"Here are your {intakes_count} most recent food intake records:\n\n"
                            + "\n".join(intake_list)
                            + "\n\nYou can use the intake ID to update or remove any of these records."
                        )
                    else:
                        final_content = (
                            "You don't have any recent food intake records yet."
                        )
                elif tool_name == "remove_intake":
                    final_content = f"Done! I've removed your intake record for {tool_output.get('dish_name', 'food')} successfully."
                elif tool_name == "search_youtube_videos":
                    videos_count = len(tool_output.get("videos", []))
                    final_content = f"I found {videos_count} YouTube videos for '{tool_output.get('query', 'your search')}'! These videos should be helpful for your request."
                else:
                    final_content = "I've completed your request!"

                # Add image acknowledgment if present
                if image_context:
                    final_content = (
                        f"Based on the images you shared, {final_content.lower()}"
                    )
            else:
                final_content = f"I tried to help you with that, but encountered an issue: {tool_output.get('error', 'Unknown error')}. How else can I assist you?"
                if image_context:
                    final_content = (
                        f"I can see the images you've shared. {final_content}"
                    )

        return final_content, tool_attachments

    @staticmethod
    def generate_response(
        user_message: str,
        conversation_context: Optional[str] = None,
        attachments: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None,
        current_user_id: Optional[int] = None,
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
                current_user_id=current_user_id,
            )

            # Estimate token usage (rough approximation)
            input_tokens = len(user_message.split()) + 50  # Message + prompt overhead

            # Add tokens for image analysis if images are present
            if attachments and "images" in attachments and attachments["images"]:
                # Rough estimation: ~100-200 tokens per image for vision analysis
                image_count = len(attachments["images"])
                input_tokens += (
                    image_count * 150
                )  # Conservative estimate for image processing

            output_tokens = len(response_content.split()) + 10  # Response + overhead

            # Merge tool attachments with image attachments
            final_attachments = tool_attachments or {}
            if attachments:
                if "images" in attachments:
                    final_attachments["images"] = attachments["images"]
                if "tool_results" in attachments:
                    final_attachments["tool_results"] = attachments.get(
                        "tool_results", {}
                    )

            return response_content, input_tokens, output_tokens, final_attachments

        except Exception:
            # Fallback response
            error_response = f"I'm experiencing some technical difficulties, but I'm here to help with your nutrition and health questions. You asked: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'"

            # Still acknowledge images if they were uploaded
            if attachments and "images" in attachments and attachments["images"]:
                error_response = "📷 I can see you've uploaded images! " + error_response

            return error_response, 0, 0, attachments

    @staticmethod
    def get_default_model(db: Session) -> Optional[LLMModel]:
        """Get the default LLM model."""
        return db.query(LLMModel).filter(LLMModel.is_available is True).first()

    @staticmethod
    def calculate_cost(input_tokens: int, output_tokens: int, model: LLMModel) -> float:
        """Calculate the cost of the interaction."""
        if not model:
            return 0.0

        input_cost = (input_tokens / 1_000_000) * float(
            model.cost_per_million_input_tokens
        )
        output_cost = (output_tokens / 1_000_000) * float(
            model.cost_per_million_output_tokens
        )
        return input_cost + output_cost
