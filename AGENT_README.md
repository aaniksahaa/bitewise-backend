# BiteWise AI Agent

## Overview

The BiteWise AI Agent is a simple but powerful conversational AI that can help users with nutrition and health questions while providing access to specific tools for dish searching and intake logging.

## Features

### 🤖 General AI Assistant
- Answer general nutrition and health questions
- Provide dietary advice and recommendations
- Engage in conversational interactions

### 🔍 Dish Search Tool
- Search for dishes by name or keywords
- Returns dish details including nutrition information
- Integrated with the existing dish database

### 📝 Intake Logging Tool
- Log food intake by dish name
- Automatically finds matching dishes in the database
- Tracks portion sizes and nutritional data

## Architecture

The agent follows a simple but effective architecture:

1. **Single-pass execution**: Makes at most one tool call per request
2. **Tool-aware LLM**: Uses OpenAI GPT-4o-mini with function calling
3. **Direct service integration**: Calls backend services directly (no API calls)
4. **Structured responses**: Returns tool results in standardized attachments format

## API Integration

### Chat Endpoint
```
POST /chat
```

The agent integrates seamlessly with the existing chat system. When a user sends a message, the agent:

1. Analyzes the message to determine intent
2. Decides whether to use tools or provide a general response
3. If tools are needed, executes the appropriate function
4. Returns a natural language response with tool results in attachments

### Response Format

```json
{
  "conversation_id": 123,
  "user_message": { ... },
  "ai_message": {
    "content": "I found 5 chicken dishes for you!",
    "attachments": {
      "tool_calls": [
        {
          "tool_name": "search_dishes",
          "tool_response": {
            "success": true,
            "dishes": [...],
            "total_found": 5
          }
        }
      ]
    }
  },
  "total_tokens_used": 150,
  "cost_estimate": 0.002
}
```

## Available Tools

### 1. Search Dishes (`search_dishes`)
**When to use**: User asks about finding dishes, recipes, or specific foods.

**Parameters**:
- `search_term` (string, required): Search term for dishes

**Example queries**:
- "Find me some chicken dishes"
- "What pasta recipes do you have?"
- "Show me healthy salads"

### 2. Log Intake (`log_intake`)
**When to use**: User mentions eating something or wants to track food consumption.

**Parameters**:
- `dish_name` (string, required): Name of the dish consumed
- `portion_size` (number, optional): Portion multiplier (default: 1.0)

**Example queries**:
- "I just ate a grilled chicken breast"
- "Log my breakfast: scrambled eggs"
- "I had 2 slices of pizza"

## Configuration

### Environment Variables
```bash
OPENAI_API_KEY=your-openai-api-key-here
```

### Dependencies
The agent requires:
- `openai>=1.68.2`
- Existing FastAPI dependencies

## Testing

Run the test script to verify functionality:

```bash
python test_agent.py
```

This will test:
- General question answering
- Tool decision making
- Error handling

## Usage Examples

### 1. General Nutrition Question
```
User: "What are the benefits of eating protein?"
Agent: "Protein is essential for building and repairing tissues..."
```

### 2. Dish Search
```
User: "Can you help me find some chicken dishes?"
Agent: "I found several chicken dishes for you! Here are the options..."
Attachments: {tool_calls: [{tool_name: "search_dishes", tool_response: {...}}]}
```

### 3. Intake Logging
```
User: "I just ate a grilled chicken breast"
Agent: "Great! I've logged your grilled chicken breast intake..."
Attachments: {tool_calls: [{tool_name: "log_intake", tool_response: {...}}]}
```

## Error Handling

The agent gracefully handles:
- Missing OpenAI API key (fallback response)
- Database connection issues
- Tool execution errors
- Invalid parameters

## Best Practices

1. **Keep it simple**: The agent makes one tool call maximum per request
2. **Clear intent**: Tool descriptions help the LLM make the right choice
3. **Structured data**: Tool responses are returned in a consistent format
4. **Fallback handling**: Always provides a response even if tools fail

## Future Enhancements

Potential improvements:
- Multi-turn tool conversations
- Image analysis capabilities
- Recipe recommendations
- Nutritional goal tracking
- Integration with fitness data 