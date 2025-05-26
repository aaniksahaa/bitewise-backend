from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.llm_model import LLMModel


class AgentService:
    """Simple agent service for handling AI interactions."""
    
    @staticmethod
    def generate_response(
        user_message: str,
        conversation_context: Optional[str] = None,
        attachments: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, int, int]:
        """
        Generate a simple dummy AI response.
        
        Returns:
            Tuple of (response_content, input_tokens, output_tokens)
        """
        # Simple dummy response
        response = f"Hello! You said: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'. How can I help you with your nutrition and health goals today?"
        
        # Dummy token counts
        input_tokens = len(user_message.split()) + 10  # Approximate input tokens
        output_tokens = len(response.split())  # Approximate output tokens
        
        return response, input_tokens, output_tokens
    
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