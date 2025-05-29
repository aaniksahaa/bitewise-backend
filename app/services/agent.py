import os
import json
from typing import Optional, Dict, Any, Tuple, List
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.tools import tool, BaseTool

from app.models.llm_model import LLMModel
from app.services.dish import DishService
from app.services.intake import IntakeService
from app.schemas.intake import IntakeCreateByName
from app.core.config import settings


class AgentService:
    """AI agent service for handling intelligent interactions using LangChain."""
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY)
        self.tools = []  # Will be populated during run_agent
        self.tool_dict = {}
        self.parser = JsonOutputParser()
        self.prompt_template = ChatPromptTemplate.from_template("""
You are BiteWise, a helpful AI assistant for nutrition and health tracking. 
You can help users with general questions and have access to tools for searching dishes and logging food intake.

User message: {message}

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
Use tools when appropriate based on the user's message.
""")

        # Template for final response generation
        self.final_response_template = ChatPromptTemplate.from_template("""
You are BiteWise, a helpful AI assistant for nutrition and health tracking.
A user asked: {original_message}

You used a tool and got this result: {tool_result}

Please provide a friendly, conversational response to the user based on the tool result.
Be helpful and explain what happened. Do not use JSON format - just respond naturally.
""")
    
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
        
        return [search_dishes, log_intake]
    
    def _get_tool_descriptions(self) -> str:
        """Get formatted tool descriptions."""
        return "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])
    
    def run_agent(
        self, 
        user_message: str, 
        db: Optional[Session] = None, 
        current_user_id: Optional[int] = None
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Run the agent with a single-pass execution.
        
        Returns:
            Tuple of (response_content, tool_attachments)
        """
        # Create tools with proper context
        self.tools = self._create_tools_with_context(db, current_user_id)
        self.tool_dict = {t.name: t for t in self.tools}
        tool_descriptions = self._get_tool_descriptions()
        
        # Prepare input data
        input_data = {
            "message": user_message,
            "tool_descriptions": tool_descriptions
        }
        
        # Generate prompt and get LLM response
        prompt = self.prompt_template.format(**input_data)
        response = self.llm.invoke(prompt)
        
        try:
            parsed = self.parser.invoke(response.content)
        except Exception as e:
            # Fallback if JSON parsing fails
            return f"I'm here to help with your nutrition and health questions! You asked: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'", None
        
        # Check if tool use is requested
        if not parsed.get("use_tool", False):
            return parsed.get("response", "I'm here to help with your nutrition and health questions!"), None
        
        # Execute tool
        tool_name = parsed.get("tool_name", "")
        tool_input = parsed.get("tool_input", {})
        
        if tool_name not in self.tool_dict:
            return f"I wanted to help you with that, but I encountered an issue with the tool '{tool_name}'. How can I assist you with your nutrition questions?", None
        
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
                else:
                    final_content = "I've completed your request!"
            else:
                final_content = f"I tried to help you with that, but encountered an issue: {tool_output.get('error', 'Unknown error')}. How else can I assist you?"
        
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
            # Check if there are image attachments and prepend metadata
            image_metadata_text = ""
            if attachments and "images" in attachments and attachments["images"]:
                images = attachments["images"]
                image_count = len(images)
                
                # Create image metadata summary
                if image_count == 1:
                    img = images[0]
                    width = img.get("metadata", {}).get("width", "unknown")
                    height = img.get("metadata", {}).get("height", "unknown")
                    size_kb = round(img.get("size", 0) / 1024, 1)
                    image_metadata_text = f"📷 Thanks for uploading an image! I can see you've shared a {width}x{height} image ({size_kb}KB). "
                else:
                    total_size = sum(img.get("size", 0) for img in images)
                    total_size_kb = round(total_size / 1024, 1)
                    image_metadata_text = f"📷 Thanks for uploading {image_count} images! Total size: {total_size_kb}KB. "
                
                # Add a note about future image processing capabilities
                image_metadata_text += "While I can see that you've shared images, I'm currently learning to analyze them better. For now, I can help you with any questions about the images or assist with your nutrition goals! "
            
            agent = AgentService()
            response_content, tool_attachments = agent.run_agent(
                user_message=user_message,
                db=db,
                current_user_id=current_user_id
            )
            
            # Prepend image metadata to the response
            if image_metadata_text:
                response_content = image_metadata_text + response_content
            
            # Estimate token usage (rough approximation)
            input_tokens = len(user_message.split()) + 50  # Message + prompt overhead
            if image_metadata_text:
                input_tokens += len(image_metadata_text.split())  # Add image context tokens
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
                error_response = "📷 I can see you've uploaded an image! " + error_response
            
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