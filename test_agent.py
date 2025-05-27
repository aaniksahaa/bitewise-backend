#!/usr/bin/env python3
"""
Simple test script for the BiteWise Agent.
This demonstrates the agent's capabilities without needing the full FastAPI server.
"""

import os
from typing import Dict, Any
from app.services.agent import AgentService

def test_general_question():
    """Test the agent with a general nutrition question."""
    print("=== Testing General Question ===")
    
    user_message = "What are the benefits of eating protein?"
    response, input_tokens, output_tokens, attachments = AgentService.generate_response(
        user_message=user_message
    )
    
    print(f"User: {user_message}")
    print(f"Agent: {response}")
    print(f"Tokens: {input_tokens} in, {output_tokens} out")
    print(f"Attachments: {attachments}")
    print()

def test_search_query():
    """Test the agent with a dish search query (without DB)."""
    print("=== Testing Search Query (No DB) ===")
    
    user_message = "Can you help me find some chicken dishes?"
    response, input_tokens, output_tokens, attachments = AgentService.generate_response(
        user_message=user_message
    )
    
    print(f"User: {user_message}")
    print(f"Agent: {response}")
    print(f"Tokens: {input_tokens} in, {output_tokens} out")
    print(f"Attachments: {attachments}")
    print()

def test_log_intake_query():
    """Test the agent with an intake logging query (without DB)."""
    print("=== Testing Log Intake Query (No DB) ===")
    
    user_message = "I just ate a grilled chicken breast"
    response, input_tokens, output_tokens, attachments = AgentService.generate_response(
        user_message=user_message
    )
    
    print(f"User: {user_message}")
    print(f"Agent: {response}")
    print(f"Tokens: {input_tokens} in, {output_tokens} out")
    print(f"Attachments: {attachments}")
    print()

def main():
    """Run all tests."""
    print("BiteWise Agent Test")
    print("==================")
    print()
    
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable not set!")
        print("Please set your OpenAI API key to test the agent.")
        return
    
    print("✅ OpenAI API key found")
    print()
    
    try:
        # Test general questions
        test_general_question()
        
        # Test search functionality (will show what the agent would try to do)
        test_search_query()
        
        # Test intake logging (will show what the agent would try to do)
        test_log_intake_query()
        
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")

if __name__ == "__main__":
    main() 