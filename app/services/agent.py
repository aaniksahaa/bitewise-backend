"""
Agent service for handling AI-powered chat responses.
"""

import json
import logging
import os
from typing import Dict, Any, Optional, Tuple, List
import base64
from io import BytesIO

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
    def generate_response(
        cls,
        user_message: str,
        attachments: Optional[Dict[str, Any]] = None,
        conversation_context: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[str, int, int, Optional[Dict[str, Any]]]:
        """
        Generate an AI response to a user message.
        
        Args:
            user_message: The user's message/question
            attachments: Optional attachments (images, etc.)
            conversation_context: Previous conversation messages for context
            
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
            
            # Process image attachments if present
            image_context = ""
            if attachments and "images" in attachments:
                image_context = cls._process_image_attachments(attachments["images"])
            
            # Build the prompt
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
        
        elif any(word in user_message_lower for word in ["ate", "eating", "consumed", "had", "log", "track"]):
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