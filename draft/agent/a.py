import os
import base64
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain.chains import LLMChain

from util import *

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# LLM setup
llm = ChatOpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY)

# Mock user context (replacing DB fetch)
def get_user_context(user_id: int) -> Dict[str, Any]:
    return {
        "name": "Test User",
        "dietary_restrictions": ["vegan"],
        "allergies": ["nuts"],
        "weight_kg": 70.0,
        "height_cm": 170.0,
        "goal": "weight_loss"
    }

# Mock conversation history (replacing DB fetch)
def get_conversation_history(conversation_id: int) -> List[Dict[str, Any]]:
    return [
        {"role": "user", "content": "I ate a salad yesterday.", "timestamp": "2025-05-09T10:00:00Z"},
        {"role": "assistant", "content": "Great, that salad was a healthy choice!", "timestamp": "2025-05-09T10:01:00Z"}
    ]

# Input Processor
class InputProcessor:
    def process(self, conversation_id: int, user_id: int, content: str = "", images_base64: List[str] = []) -> Dict[str, Any]:
        if not content and not images_base64:
            raise ValueError("Either content or images_base64 must be provided")

        # Fetch user context (mocked)
        user_context = get_user_context(user_id)

        # Process images (mocked: assume images identify a dish)
        image_items = []
        for img_b64 in images_base64:
            try:
                base64.b64decode(img_b64, validate=True)  # Validate base64
                image_items.append({"dish": "pizza"})  # Mock: replace with computer vision
            except Exception:
                raise ValueError("Invalid base64 image")

        # Mock saving user message (no DB)
        message_id = 123  # Dummy ID

        return {
            "content": content,
            "image_items": image_items,
            "user_context": user_context,
            "message_id": message_id,
            "conversation_id": conversation_id,
            "user_id": user_id
        }

# Tools
@tool
def log_intake(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Logs food intake and returns nutritional summary."""
    dish_name = input_data.get("dish", "unknown")
    portion_size = float(input_data.get("portion_size", 1.0))
    # Mock nutrition data (replace with USDA API)
    calories = 500.0 if dish_name == "pizza" else 200.0
    return {
        "intake_id": 456,  # Mock ID
        "dish": dish_name,
        "calories": calories * portion_size,
        "portion_size": portion_size
    }

@tool
def search_recipes(input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Searches for recipes based on ingredients."""
    ingredients = input_data.get("ingredients", [])
    user_context = input_data.get("user_context", {})
    allergies = user_context.get("allergies", [])
    # Mock recipe data
    recipes = [
        {
            "name": "Vegan Stir Fry",
            "ingredients": ["tofu", "broccoli", "soy sauce"],
            "calories": 300,
            "recipe": "Stir-fry ingredients with soy sauce."
        },
        {
            "name": "Chicken Salad",
            "ingredients": ["chicken", "lettuce", "tomato"],
            "calories": 400,
            "recipe": "Mix ingredients and serve."
        }
    ]
    # Filter out recipes with allergens
    return [r for r in recipes if not any(allergy in r["ingredients"] for allergy in allergies)]

@tool
def calculate_metric(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculates health metrics like BMI."""
    metric = input_data.get("metric", "bmi")
    user_context = input_data.get("user_context", {})
    weight_kg = user_context.get("weight_kg", 70.0)
    height_cm = user_context.get("height_cm", 170.0)
    if metric == "bmi":
        bmi = weight_kg / ((height_cm / 100) ** 2)
        return {
            "metric": "BMI",
            "value": round(bmi, 1),
            "widget_data": {"label": f"BMI: {bmi:.1f}"}
        }
    return {"error": "Unsupported metric"}

# Agent
class BiteWiseAgent:
    def __init__(self):
        self.llm = llm
        self.tools = [log_intake, search_recipes, calculate_metric]
        self.input_processor = InputProcessor()

        # Routing prompt for intent classification
        self.routing_prompt = PromptTemplate(
            input_variables=["content", "image_items", "user_context"],
            template="""
            Given the user message: "{content}" and detected image items: {image_items},
            classify the intent as one of: [food_intake, recipe_search, health_calculation, general].
            User context: {user_context}.
            Return a JSON object with:
            - intent: The classified intent
            - entities: Extracted entities (e.g., dish names, ingredients, metric)

            Example output:
            ```json
            {{
                "intent": "food_intake",
                "entities": {{"dish": "pizza", "portion_size": 1.0}}
            }}
            ```
            """
        )

        # self.routing_chain = LLMChain(llm=self.llm, prompt=self.routing_prompt)

        self.routing_chain = self.routing_prompt | self.llm


        # Response prompt
        self.response_prompt = PromptTemplate(
            input_variables=["user_context", "history", "content", "image_items", "tool_outputs"],
            template="""
            You are BiteWise, a friendly AI assistant for food and health.
            User context: {user_context}
            Conversation history: {history}
            Current message: {content}
            Image items: {image_items}
            Tool outputs: {tool_outputs}

            Generate a concise, personalized response addressing the user's request.
            - For food intake, include nutritional summary.
            - For recipes, list dish details.
            - For calculations, include results and explanations.
            - Respect dietary restrictions and allergies.
            - Keep the tone friendly and helpful.
            """
        )

        # self.response_chain = LLMChain(llm=self.llm, prompt=self.response_prompt)

        self.response_chain = self.response_prompt | self.llm

    def process_message(self, conversation_id: int, user_id: int, content: str = "", images_base64: List[str] = []) -> Dict[str, Any]:
        # Process input
        input_data = self.input_processor.process(conversation_id, user_id, content, images_base64)

        # Classify intent
        routing_input = {
            "content": input_data["content"],
            "image_items": input_data["image_items"],
            "user_context": input_data["user_context"]
        }

        # routing_result = self.routing_chain.run(**routing_input)

        routing_result = self.routing_chain.invoke(routing_input)

        print(routing_result)

        try:
            routing_result = parse_json_from_output(routing_result.content)
        except json.JSONDecodeError:
            routing_result = {"intent": "general", "entities": {}}

        print(routing_result)

        intent = routing_result["intent"]
        entities = routing_result["entities"]

        # Execute tools based on intent
        tool_outputs = {}
        tool_input = {
            "user_id": user_id,
            "user_context": input_data["user_context"],
            **entities
        }
        if intent == "food_intake":
            tool_outputs = log_intake.invoke(tool_input)
        elif intent == "recipe_search":
            tool_outputs = search_recipes(tool_input)
        elif intent == "health_calculation":
            tool_outputs = calculate_metric(tool_input)
        elif intent == "general":
            tool_outputs = {"message": "No specific action taken, responding directly."}

        # Fetch conversation history (mocked)
        history = get_conversation_history(conversation_id)

        # Generate response
        response_input = {
            "user_context": input_data["user_context"],
            "history": history,
            "content": input_data["content"],
            "image_items": input_data["image_items"],
            "tool_outputs": tool_outputs
        }
        response_text = self.response_chain.invoke(response_input)

        # Mock saving AI response (no DB)
        response = {
            "message_id": 124,  # Dummy ID
            "content": response_text,
            "tool_outputs": tool_outputs,
            "intent": intent
        }
        return response

# Example Usage
if __name__ == "__main__":
    agent = BiteWiseAgent()

    # Test case 1: Food intake with text and image
    result = agent.process_message(
        conversation_id=1,
        user_id=1,
        content="I ate a pizza",
        images_base64=[]
        # images_base64=["data:image/jpeg;base64,/9j/4AAQSkZJRg=="]  # Mock base64
    )
    print("Result:", json.dumps(result, indent=2))

    # # Test case 2: Recipe search
    # try:
    #     result = agent.process_message(
    #         conversation_id=1,
    #         user_id=1,
    #         content="What can I cook with tofu?"
    #     )
    #     print("Result:", json.dumps(result, indent=2))
    # except Exception as e:
    #     print("Error:", str(e))

    # # Test case 3: Health calculation
    # try:
    #     result = agent.process_message(
    #         conversation_id=1,
    #         user_id=1,
    #         content="What's my BMI?"
    #     )
    #     print("Result:", json.dumps(result, indent=2))
    # except Exception as e:
    #     print("Error:", str(e))