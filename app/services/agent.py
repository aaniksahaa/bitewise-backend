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
                
                logger.info("LLM instances initialized successfully")
                
            except ImportError as e:
                logger.error(f"Failed to import required LLM libraries: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize LLM instances: {e}")
                raise
    
    @classmethod
    async def generate_response(
        cls,
        user_message: str,
        attachments: Optional[Dict[str, Any]] = None,
        conversation_context: Optional[List[Dict[str, str]]] = None,
        db: Optional[AsyncSession] = None
    ) -> Tuple[str, int, int, Optional[Dict[str, Any]]]:
        """
        Generate an AI response to a user message.
        
        Args:
            user_message: The user's message/question
            attachments: Optional attachments (images, etc.)
            conversation_context: Previous conversation messages for context
            db: Database session for real data queries
            
        Returns:
            Tuple of (response_text, input_tokens, output_tokens, response_attachments)
        """
        try:
            # Initialize LLM if needed
            cls._initialize_llm()
            
            # Handle empty or None messages
            if not user_message or not user_message.strip():
                return (
                    "I'd be happy to help! Please ask me a question about nutrition, food, or health.",
                    10, 20, None
                )
            
            # Analyze user intent first
            intent_analysis = cls.analyze_user_intent(user_message)
            
            # Handle food intake logging with widget generation
            if intent_analysis["primary_intent"] == "log_intake" and intent_analysis["confidence"] > 0.6:
                return await cls._handle_food_intake_intent(user_message, intent_analysis, db)
            
            # Process image attachments if present
            image_context = ""
            if attachments and "images" in attachments:
                image_context = cls._process_image_attachments(attachments["images"])
            
            # Build the prompt for general conversation
            system_prompt = cls._build_system_prompt()
            user_prompt = cls._build_user_prompt(user_message, image_context, conversation_context)
            
            # Generate response using LLM
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Call LLM
            response = cls.llm.invoke(messages)
            response_text = response.content
            
            # Parse response to check for tool usage
            try:
                # Try to parse as JSON to see if it contains tool instructions
                parsed_response = json.loads(response_text)
                if isinstance(parsed_response, dict) and "response" in parsed_response:
                    actual_response = parsed_response["response"]
                else:
                    actual_response = response_text
            except json.JSONDecodeError:
                # Not JSON, use as-is
                actual_response = response_text
            
            # Estimate token usage (simplified)
            input_tokens = cls._estimate_tokens(system_prompt + user_prompt)
            output_tokens = cls._estimate_tokens(actual_response)
            
            return actual_response, input_tokens, output_tokens, None
            
        except Exception as e:
            logger.error(f"Error generating agent response: {e}")
            error_response = "I apologize, but I'm having trouble processing your request right now. Please try again later."
            return error_response, 0, 0, None
    
    @classmethod
    async def _handle_food_intake_intent(cls, user_message: str, intent_analysis: Dict[str, Any], db: Optional[AsyncSession] = None) -> Tuple[str, int, int, Optional[Dict[str, Any]]]:
        """Handle food intake logging intent and generate dish selection widgets."""
        try:
            # Extract food/dish name from the message
            food_name = cls._extract_food_name(user_message)
            
            if not food_name:
                return (
                    "I understand you'd like to log some food intake! Could you please specify what you ate?",
                    20, 30, None
                )
            
            # Search for matching dishes (use real database if available)
            if db:
                matching_dishes = await cls._search_dishes_for_intake_db(food_name, db)
            else:
                matching_dishes = cls._search_dishes_for_intake_mock(food_name)
            
            if not matching_dishes:
                return (
                    f"I couldn't find any dishes matching '{food_name}' in our database. Could you try a different name or be more specific?",
                    25, 40, None
                )
            
            # Generate dish selection widget
            widget = cls._create_dish_selection_widget(food_name, matching_dishes)
            
            # Create response text
            response_text = cls._create_intake_response_text(food_name, matching_dishes)
            
            # Create tool attachments with widgets
            tool_attachments = {
                "widgets": [widget.dict()],
                "tool_calls": [{
                    "tool_name": "search_dishes_for_intake",
                    "tool_input": {"search_term": food_name},
                    "tool_response": {
                        "dishes_found": len(matching_dishes),
                        "widget_id": widget.widget_id
                    }
                }]
            }
            
            # Estimate token usage
            input_tokens = cls._estimate_tokens(user_message)
            output_tokens = cls._estimate_tokens(response_text)
            
            return response_text, input_tokens, output_tokens, tool_attachments
            
        except Exception as e:
            logger.error(f"Error handling food intake intent: {e}")
            return (
                "I had trouble processing your food logging request. Please try again.",
                10, 20, None
            )
    
    @classmethod
    async def _search_dishes_for_intake_db(cls, food_name: str, db: AsyncSession) -> List[Dict[str, Any]]:
        """Search for dishes matching the food name using real database queries."""
        try:
            from app.models.dish import Dish
            from sqlalchemy import or_, func
            
            # Search for dishes that match the food name
            food_name_lower = food_name.lower()
            
            # Build search query
            stmt = select(Dish).where(
                or_(
                    func.lower(Dish.name).contains(food_name_lower),
                    func.lower(Dish.description).contains(food_name_lower)
                )
            ).limit(5)  # Limit to 5 results for the widget
            
            result = await db.execute(stmt)
            dishes = result.scalars().all()
            
            # Convert to the format expected by the widget
            matching_dishes = []
            for dish in dishes:
                dish_dict = {
                    "id": dish.id,
                    "name": dish.name,
                    "description": dish.description,
                    "cuisine": dish.cuisine,
                    "image_url": dish.image_urls[0] if dish.image_urls else None,
                    "calories": int(float(dish.calories)) if dish.calories else 0,
                    "servings": dish.servings
                }
                matching_dishes.append(dish_dict)
            
            return matching_dishes
            
        except Exception as e:
            logger.error(f"Error searching dishes in database: {e}")
            # Fall back to mock data if database search fails
            return cls._search_dishes_for_intake_mock(food_name)
    
    @classmethod
    def _search_dishes_for_intake_mock(cls, food_name: str) -> List[Dict[str, Any]]:
        """Search for dishes matching the food name (mock implementation)."""
        # Mock dish data - fallback when database is not available
        mock_dishes = {
            "pizza": [
                {
                    "id": 999001,  # Use high IDs to avoid conflicts
                    "name": "Roasted Peppers, Spinach & Feta Pizza",
                    "description": "A delicious vegetarian option with roasted peppers, spinach, and feta cheese",
                    "cuisine": "Italian",
                    "image_url": "https://img.spoonacular.com/recipes/658615-312x231.jpg",
                    "calories": 390,
                    "servings": 4
                },
                {
                    "id": 999002,
                    "name": "Rustic Grilled Peaches Pizza",
                    "description": "A unique dish that can be prepared in about 45 minutes",
                    "cuisine": "Italian",
                    "image_url": "https://img.spoonacular.com/recipes/658920-312x231.jpg",
                    "calories": 226,
                    "servings": 2
                },
                {
                    "id": 999003,
                    "name": "Pizza Bites with Pumpkin",
                    "description": "These gluten-free pizza bites are great as an appetizer",
                    "cuisine": "Italian",
                    "image_url": "https://img.spoonacular.com/recipes/656329-312x231.jpg",
                    "calories": 310,
                    "servings": 6
                }
            ],
            "chicken": [
                {
                    "id": 999004,
                    "name": "Grilled Chicken Breast",
                    "description": "Lean protein, perfect for healthy eating",
                    "cuisine": "American",
                    "image_url": "https://via.placeholder.com/312x231",
                    "calories": 165,
                    "servings": 1
                },
                {
                    "id": 999005,
                    "name": "Chicken Caesar Salad",
                    "description": "Fresh romaine lettuce with grilled chicken and Caesar dressing",
                    "cuisine": "American",
                    "image_url": "https://via.placeholder.com/312x231",
                    "calories": 470,
                    "servings": 1
                }
            ],
            "salad": [
                {
                    "id": 999006,
                    "name": "Garden Salad",
                    "description": "Fresh mixed greens with vegetables",
                    "cuisine": "American",
                    "image_url": "https://via.placeholder.com/312x231",
                    "calories": 150,
                    "servings": 1
                },
                {
                    "id": 999007,
                    "name": "Greek Salad",
                    "description": "Mediterranean salad with feta cheese and olives",
                    "cuisine": "Greek",
                    "image_url": "https://via.placeholder.com/312x231",
                    "calories": 280,
                    "servings": 1
                }
            ]
        }
        
        # Find matching dishes
        food_name_lower = food_name.lower()
        
        # Direct keyword match
        for keyword, dishes in mock_dishes.items():
            if keyword in food_name_lower:
                return dishes
        
        # Partial match
        for keyword, dishes in mock_dishes.items():
            if any(word in keyword for word in food_name_lower.split()):
                return dishes
        
        return []
    
    @classmethod
    def _extract_food_name(cls, user_message: str) -> Optional[str]:
        """Extract food/dish name from user message."""
        # Simple extraction logic - this could be enhanced with NER
        user_message_lower = user_message.lower()
        
        # Common patterns for food intake
        patterns = [
            "i ate", "i had", "i consumed", "i just ate", "i just had",
            "ate", "had", "consumed", "eating", "having"
        ]
        
        for pattern in patterns:
            if pattern in user_message_lower:
                # Extract text after the pattern
                start_idx = user_message_lower.find(pattern) + len(pattern)
                remaining_text = user_message[start_idx:].strip()
                
                # Remove common stop words and extract the main food item
                remaining_text = remaining_text.replace("a ", "").replace("an ", "").replace("some ", "")
                
                # Take the first few words as the food name
                words = remaining_text.split()
                if words:
                    # Return up to 3 words as the food name
                    return " ".join(words[:3]).strip(".,!?")
        
        # If no pattern found, try to find common food words
        food_keywords = ["pizza", "chicken", "salad", "pasta", "burger", "sandwich", "rice", "bread"]
        for keyword in food_keywords:
            if keyword in user_message_lower:
                return keyword
        
        return None
    
    @classmethod
    def _create_dish_selection_widget(cls, search_term: str, dishes: List[Dict[str, Any]]) -> 'DishSelectionWidget':
        """Create a dish selection widget."""
        from app.schemas.chat import DishSelectionWidget, DishCard, WidgetType, WidgetStatus
        
        # Convert dishes to DishCard format
        dish_cards = []
        for dish in dishes:
            dish_card = DishCard(
                id=dish["id"],
                name=dish["name"],
                description=dish.get("description"),
                cuisine=dish.get("cuisine"),
                image_url=dish.get("image_url"),
                calories=dish.get("calories"),
                servings=dish.get("servings")
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
        
        return widget
    
    @classmethod
    def _create_intake_response_text(cls, food_name: str, dishes: List[Dict[str, Any]]) -> str:
        """Create the response text for food intake logging."""
        response_parts = [
            f"Hey there! Thanks for sharing that you had {food_name}. I found a few different types of {food_name} that match what you mentioned, and I need your help to pinpoint exactly which one you enjoyed. Here are the options:\n"
        ]
        
        for i, dish in enumerate(dishes, 1):
            response_parts.append(
                f"{i}. **{dish['name']}** - {dish.get('description', 'A delicious option')} with {dish.get('calories', 'unknown')} calories."
            )
            if dish.get('image_url'):
                response_parts.append(f"   ![{dish['name']}]({dish['image_url']})")
            response_parts.append("")
        
        response_parts.append("Could you please let me know which one you had? This way, I can help you keep track of your nutrition more accurately!")
        
        return "\n".join(response_parts)
    
    @classmethod
    def _build_system_prompt(cls) -> str:
        """Build the system prompt for the AI agent."""
        return """You are BiteWise, a helpful AI nutrition and health assistant. You help users with:

1. Nutrition questions and advice
2. Food and recipe recommendations
3. Meal planning and dietary guidance
4. Food intake logging and tracking
5. Health and wellness tips

Guidelines:
- Provide accurate, helpful information about nutrition and health
- Be encouraging and supportive
- If you're unsure about medical advice, recommend consulting healthcare professionals
- Keep responses conversational and friendly
- Focus on practical, actionable advice

When users ask about finding dishes or logging food intake, acknowledge their request and provide helpful guidance, but note that full database integration may require additional steps.

Respond in a natural, conversational way. Do not use JSON formatting unless specifically requested."""
    
    @classmethod
    def _build_user_prompt(
        cls, 
        user_message: str, 
        image_context: str = "", 
        conversation_context: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Build the user prompt with context."""
        prompt_parts = []
        
        # Add conversation context if available
        if conversation_context:
            prompt_parts.append("Previous conversation context:")
            for msg in conversation_context[-5:]:  # Last 5 messages for context
                role = msg.get("role", "user")
                content = msg.get("content", "")
                prompt_parts.append(f"{role.title()}: {content}")
            prompt_parts.append("")
        
        # Add image context if available
        if image_context:
            prompt_parts.append(f"Image analysis: {image_context}")
            prompt_parts.append("")
        
        # Add current user message
        prompt_parts.append(f"User question: {user_message}")
        
        return "\n".join(prompt_parts)
    
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
            logger.error(f"Error processing image attachments: {e}")
            return "I had trouble processing the image(s) you shared. Please describe what you'd like help with."
    
    @classmethod
    def _estimate_tokens(cls, text: str) -> int:
        """Estimate token count for text (rough approximation)."""
        # Rough estimation: ~4 characters per token for English text
        return max(1, len(text) // 4)
    
    @classmethod
    def analyze_user_intent(cls, user_message: str) -> Dict[str, Any]:
        """
        Analyze user intent to determine what action to take.
        
        Returns:
            Dict with intent analysis including suggested actions
        """
        user_message_lower = user_message.lower()
        
        intent_analysis = {
            "primary_intent": "general_question",
            "confidence": 0.5,
            "suggested_actions": [],
            "entities": []
        }
        
        # Simple keyword-based intent detection
        if any(word in user_message_lower for word in ["find", "search", "recommend", "suggest", "dish", "recipe"]):
            intent_analysis["primary_intent"] = "dish_search"
            intent_analysis["confidence"] = 0.8
            intent_analysis["suggested_actions"].append("search_dishes")
        
        elif any(word in user_message_lower for word in ["ate", "eating", "consumed", "had", "log", "track", "just ate", "just had"]):
            intent_analysis["primary_intent"] = "log_intake"
            intent_analysis["confidence"] = 0.7
            intent_analysis["suggested_actions"].append("log_food_intake")
        
        elif any(word in user_message_lower for word in ["nutrition", "calories", "protein", "carbs", "fat", "vitamins"]):
            intent_analysis["primary_intent"] = "nutrition_question"
            intent_analysis["confidence"] = 0.9
        
        return intent_analysis
    
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