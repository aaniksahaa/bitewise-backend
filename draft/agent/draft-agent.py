import os
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.tools import tool, BaseTool

from util import parse_json_from_output

# Load env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY)

# Mocked DB functions
def get_user_context(user_id: int) -> Dict[str, Any]:
    return {
        "name": "Test User",
        "dietary_restrictions": ["vegan"],
        "allergies": ["nuts"],
        "weight_kg": 70.0,
        "height_cm": 170.0,
        "goal": "weight_loss"
    }

def get_conversation_history(conversation_id: int) -> List[Dict[str, Any]]:
    return [
        {"role": "user", "content": "I ate a salad yesterday.", "timestamp": "2025-05-09T10:00:00Z"},
        {"role": "assistant", "content": "Great, that salad was a healthy choice!", "timestamp": "2025-05-09T10:01:00Z"}
    ]

@tool
def log_intake(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Logs food intake and returns nutritional summary."""
    dish_name = input_data.get("dish", "unknown")
    portion_size = float(input_data.get("portion_size", 1.0))
    calories = 500.0 if dish_name == "pizza" else 200.0
    return {
        "intake_id": 456,
        "dish": dish_name,
        "calories": calories * portion_size,
        "portion_size": portion_size
    }

@tool
def search_recipes(input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Search for recipes based on ingredients and dietary restrictions."""
    ingredients = input_data.get("ingredients", [])
    allergies = input_data.get("user_context", {}).get("allergies", [])
    recipes = [
        {"name": "Vegan Stir Fry", "ingredients": ["tofu", "broccoli"], "calories": 300},
        {"name": "Chicken Salad", "ingredients": ["chicken", "lettuce"], "calories": 400}
    ]
    return [r for r in recipes if not any(a in r["ingredients"] for a in allergies)]

@tool
def calculate_metric(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate BMI based on user weight and height."""
    weight = input_data.get("user_context", {}).get("weight_kg", 70.0)
    height = input_data.get("user_context", {}).get("height_cm", 170.0)
    bmi = weight / ((height / 100) ** 2)
    return {
        "metric": "BMI",
        "value": round(bmi, 1),
        "widget_data": {"label": f"BMI: {bmi:.1f}"}
    }


def get_tool_descriptions(tools: List[BaseTool]) -> str:
    return "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])


# Core Agent
class DynamicBiteWiseAgent:
    def __init__(self):
        self.llm = llm
        self.tools: List[BaseTool] = [log_intake, search_recipes, calculate_metric]
        self.tool_dict = {t.name: t for t in self.tools}
        self.parser = JsonOutputParser()
        self.tool_descriptions = get_tool_descriptions(self.tools)
        self.prompt_template = ChatPromptTemplate.from_template("""
You are BiteWise, an AI assistant for food and health. You have access to tools.

User context:
{user_context}

Conversation history:
{history}

New user message:
{message}

Image items:
{image_items}
                                                                
Available tools:
{tool_descriptions}

You may call a tool by responding in JSON:
{{
  "use_tool": true,
  "tool_name": "tool_name_here",
  "tool_input": {{...tool input as JSON...}}
}}

If no tool is needed:
{{
  "use_tool": false,
  "response": "Final natural language response"
}}
""")

    def run(self, conversation_id: int, user_id: int, content: str, images_base64: List[str] = []) -> Dict[str, Any]:
        user_context = get_user_context(user_id)
        history = get_conversation_history(conversation_id)
        image_items = [{"dish": "pizza"} for _ in images_base64]  # Mocked

        input_data = {
            "user_context": user_context,
            "history": history,
            "message": content,
            "image_items": image_items,
            "tool_descriptions": self.tool_descriptions
        }

        for _ in range(5):  # max steps
            prompt = self.prompt_template.format(**input_data)

            print(prompt)

            response = self.llm.invoke(prompt)

            try:
                parsed = self.parser.invoke(response.content)
            except Exception as e:
                return {"error": f"Failed to parse model response: {e}", "raw_response": response.content}

            if not parsed.get("use_tool"):
                return {
                    "message_id": 124,
                    "content": parsed["response"],
                    "tool_outputs": {},
                    "intent": "general"
                }

            tool_name = parsed["tool_name"]
            tool_input = parsed["tool_input"]

            print(f"\n\nllm called\n tool: {tool_name}, tool input: {tool_input}\n\n")

            if tool_name not in self.tool_dict:
                return {"error": f"Unknown tool '{tool_name}'", "raw_response": response.content}

            tool = self.tool_dict[tool_name]
            tool_output = tool.invoke(tool_input)

            input_data["message"] += f"\n\nTool result: {tool_output}"
            input_data["tool_outputs"] = tool_output

        return {
            "message_id": 125,
            "content": "Too many steps without final response.",
            "tool_outputs": {},
            "intent": "uncertain"
        }

# Example
if __name__ == "__main__":
    agent = DynamicBiteWiseAgent()
    result = agent.run(
        conversation_id=1,
        user_id=1,
        content="I ate two slices of pizza today. please log this intake",
        images_base64=[]
    )
    print(json.dumps(result, indent=2))
