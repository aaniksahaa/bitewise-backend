# BiteWise API Documentation

## Overview

BiteWise API provides programmatic access to the BiteWise platform, an AI-powered assistant for personalized nutrition, recipe recommendations, and food-related social features. This documentation describes the available endpoints, request parameters, and response formats.

## Base URL

```
https://api.bitewise.com/v1
```

## Authentication

All API requests require authentication using a Bearer token:

```
Authorization: Bearer YOUR_API_TOKEN
```

To obtain an API token, register at the [BiteWise Developer Portal](https://developers.bitewise.com).

## Rate Limiting

Requests are limited to 100 per minute per API token. Rate limit information is provided in the response headers:

- `X-RateLimit-Limit`: Maximum requests per minute
- `X-RateLimit-Remaining`: Remaining requests for the current minute
- `X-RateLimit-Reset`: Time (in seconds) until the rate limit resets

## API Endpoints

### User Management

#### Create User Profile

```http
POST /users
```

Creates a new user profile with health and dietary information.

**Request Body**:

```json
{
  "username": "string",
  "email": "string",
  "password": "string",
  "demographics": {
    "age": integer,
    "height": number,
    "weight": number,
    "sex": "string"
  },
  "health_profile": {
    "dietary_restrictions": ["string"],
    "allergies": ["string"],
    "health_conditions": ["string"],
    "fitness_goals": ["string"]
  },
  "preferences": {
    "taste_preferences": ["string"],
    "cuisine_interests": ["string"],
    "cooking_skill": "string"
  }
}
```

**Response** (201 Created):

```json
{
  "user_id": "string",
  "username": "string",
  "created_at": "string (ISO datetime)",
  "profile_complete": boolean
}
```

#### Get User Profile

```http
GET /users/{user_id}
```

Retrieves a user's profile information.

**Path Parameters**:

- `user_id` (string, required): Unique identifier for the user

**Response** (200 OK):

```json
{
  "user_id": "string",
  "username": "string",
  "email": "string",
  "demographics": {
    "age": integer,
    "height": number,
    "weight": number,
    "sex": "string"
  },
  "health_profile": {
    "dietary_restrictions": ["string"],
    "allergies": ["string"],
    "health_conditions": ["string"],
    "fitness_goals": ["string"]
  },
  "preferences": {
    "taste_preferences": ["string"],
    "cuisine_interests": ["string"],
    "cooking_skill": "string"
  },
  "created_at": "string (ISO datetime)",
  "updated_at": "string (ISO datetime)"
}
```

#### Update User Profile

```http
PATCH /users/{user_id}
```

Updates specific fields in a user's profile.

**Path Parameters**:

- `user_id` (string, required): Unique identifier for the user

**Request Body**:
Any fields from the user profile schema that need to be updated.

**Response** (200 OK):

```json
{
  "user_id": "string",
  "updated_at": "string (ISO datetime)",
  "updated_fields": ["string"]
}
```

### Conversational AI Chat

#### Initiate Chat Session

```http
POST /chat/sessions
```

Creates a new chat session with the AI assistant.

**Request Body**:

```json
{
  "user_id": "string"
}
```

**Response** (201 Created):

```json
{
  "session_id": "string",
  "created_at": "string (ISO datetime)"
}
```

#### Send Message

```http
POST /chat/sessions/{session_id}/messages
```

Sends a message to the AI assistant within a chat session.

**Path Parameters**:

- `session_id` (string, required): Unique identifier for the chat session

**Request Body**:

```json
{
  "message": "string",
  "attachments": [
    {
      "type": "image",
      "content": "base64_encoded_string",
      "filename": "string"
    }
  ]
}
```

**Response** (200 OK):

```json
{
  "message_id": "string",
  "response": "string",
  "detected_entities": {
    "ingredients": ["string"],
    "recipes": ["string"],
    "nutrition_info": {
      "calories": number,
      "protein": number,
      "carbs": number,
      "fat": number
    },
    "dietary_flags": ["string"]
  },
  "suggestions": ["string"],
  "timestamp": "string (ISO datetime)"
}
```

#### Get Chat History

```http
GET /chat/sessions/{session_id}/messages
```

Retrieves message history for a chat session.

**Path Parameters**:

- `session_id` (string, required): Unique identifier for the chat session

**Query Parameters**:

- `limit` (integer, optional): Maximum number of messages to return
- `before` (string, optional): Return messages before this timestamp

**Response** (200 OK):

```json
{
  "session_id": "string",
  "messages": [
    {
      "message_id": "string",
      "sender": "string",
      "content": "string",
      "attachments": [],
      "timestamp": "string (ISO datetime)"
    }
  ],
  "has_more": boolean
}
```

### Food & Nutrition

#### Analyze Food Image

```http
POST /food/analyze
```

Analyzes an image to identify ingredients and nutritional information.

**Request Body**:

```json
{
  "image": "base64_encoded_string",
  "user_id": "string"
}
```

**Response** (200 OK):

```json
{
  "analysis_id": "string",
  "identified_food": ["string"],
  "ingredients": ["string"],
  "nutrition": {
    "calories": number,
    "protein": number,
    "carbs": number,
    "fat": number,
    "vitamins": {},
    "minerals": {}
  },
  "health_warnings": ["string"],
  "portion_estimate": "string",
  "confidence_score": number
}
```

#### Analyze Recipe Text

```http
POST /food/recipes/analyze
```

Analyzes recipe text to extract ingredients and nutritional information.

**Request Body**:

```json
{
  "recipe_text": "string",
  "user_id": "string",
  "servings": integer
}
```

**Response** (200 OK):

```json
{
  "analysis_id": "string",
  "recipe_title": "string",
  "ingredients": [
    {
      "name": "string",
      "quantity": "string",
      "unit": "string"
    }
  ],
  "instructions": ["string"],
  "nutrition_per_serving": {
    "calories": number,
    "protein": number,
    "carbs": number,
    "fat": number
  },
  "health_warnings": ["string"],
  "health_benefits": ["string"],
  "user_compatibility": {
    "allergen_warnings": ["string"],
    "dietary_restriction_conflicts": ["string"],
    "health_condition_notes": ["string"]
  }
}
```

#### Log Food Entry

```http
POST /food/diary
```

Logs a food entry in the user's food diary.

**Request Body**:

```json
{
  "user_id": "string",
  "food_name": "string",
  "portion_size": "string",
  "meal_type": "string",
  "timestamp": "string (ISO datetime)",
  "nutrition": {
    "calories": number,
    "protein": number,
    "carbs": number,
    "fat": number
  },
  "notes": "string",
  "image_id": "string"
}
```

**Response** (201 Created):

```json
{
  "entry_id": "string",
  "created_at": "string (ISO datetime)"
}
```

#### Get Food Diary

```http
GET /food/diary
```

Retrieves food diary entries for a user.

**Query Parameters**:

- `user_id` (string, required): User identifier
- `start_date` (string, optional): Start date (ISO format)
- `end_date` (string, optional): End date (ISO format)
- `meal_type` (string, optional): Filter by meal type

**Response** (200 OK):

```json
{
  "entries": [
    {
      "entry_id": "string",
      "food_name": "string",
      "portion_size": "string",
      "meal_type": "string",
      "timestamp": "string (ISO datetime)",
      "nutrition": {
        "calories": number,
        "protein": number,
        "carbs": number,
        "fat": number
      },
      "notes": "string",
      "image_url": "string"
    }
  ],
  "daily_totals": [
    {
      "date": "string (ISO date)",
      "calories": number,
      "protein": number,
      "carbs": number,
      "fat": number
    }
  ],
  "insights": {
    "calorie_goal_progress": number,
    "macronutrient_distribution": {
      "protein_percentage": number,
      "carbs_percentage": number,
      "fat_percentage": number
    },
    "streak_days": integer
  }
}
```

### Recipe Recommendations

#### Get Recipe Suggestions

```http
GET /recipes/suggestions
```

Provides recipe suggestions based on user profile and preferences.

**Query Parameters**:

- `user_id` (string, required): User identifier
- `ingredients` (string, optional): Comma-separated list of available ingredients
- `meal_type` (string, optional): Type of meal (breakfast, lunch, dinner, snack)
- `max_prep_time` (integer, optional): Maximum preparation time in minutes
- `limit` (integer, optional): Maximum number of recipes to return

**Response** (200 OK):

```json
{
  "recipes": [
    {
      "recipe_id": "string",
      "title": "string",
      "image_url": "string",
      "prep_time": integer,
      "cook_time": integer,
      "servings": integer,
      "ingredients": [
        {
          "name": "string",
          "quantity": "string",
          "unit": "string",
          "substitutions": ["string"]
        }
      ],
      "instructions": ["string"],
      "nutrition_per_serving": {
        "calories": number,
        "protein": number,
        "carbs": number,
        "fat": number
      },
      "health_tags": ["string"],
      "relevance_score": number,
      "match_reason": "string"
    }
  ]
}
```

#### Get Recipe Details

```http
GET /recipes/{recipe_id}
```

Retrieves detailed information about a specific recipe.

**Path Parameters**:

- `recipe_id` (string, required): Unique identifier for the recipe

**Query Parameters**:

- `user_id` (string, optional): User identifier for personalized information

**Response** (200 OK):

```json
{
  "recipe_id": "string",
  "title": "string",
  "author": {
    "user_id": "string",
    "username": "string"
  },
  "created_at": "string (ISO datetime)",
  "updated_at": "string (ISO datetime)",
  "image_url": "string",
  "prep_time": integer,
  "cook_time": integer,
  "servings": integer,
  "ingredients": [
    {
      "name": "string",
      "quantity": "string",
      "unit": "string",
      "substitutions": ["string"]
    }
  ],
  "instructions": ["string"],
  "nutrition_per_serving": {
    "calories": number,
    "protein": number,
    "carbs": number,
    "fat": number,
    "vitamins": {},
    "minerals": {}
  },
  "health_tags": ["string"],
  "cuisine_type": "string",
  "difficulty_level": "string",
  "user_compatibility": {
    "allergen_warnings": ["string"],
    "dietary_restriction_conflicts": ["string"],
    "health_condition_notes": ["string"],
    "personalized_adjustments": ["string"]
  },
  "reviews": {
    "average_rating": number,
    "count": integer
  }
}
```

### Community Features

#### Create Recipe Post

```http
POST /community/posts
```

Creates a recipe post to share with the community.

**Request Body**:

```json
{
  "user_id": "string",
  "title": "string",
  "recipe_id": "string",
  "content": "string",
  "image": "base64_encoded_string",
  "tags": ["string"]
}
```

**Response** (201 Created):

```json
{
  "post_id": "string",
  "created_at": "string (ISO datetime)"
}
```

#### Get Community Feed

```http
GET /community/feed
```

Retrieves the community feed with recent posts.

**Query Parameters**:

- `user_id` (string, required): User identifier
- `limit` (integer, optional): Maximum number of posts to return
- `before` (string, optional): Return posts before this timestamp
- `tags` (string, optional): Filter by comma-separated tags

**Response** (200 OK):

```json
{
  "posts": [
    {
      "post_id": "string",
      "user": {
        "user_id": "string",
        "username": "string",
        "avatar_url": "string"
      },
      "title": "string",
      "content": "string",
      "image_url": "string",
      "recipe": {
        "recipe_id": "string",
        "title": "string",
        "preview": "string"
      },
      "likes_count": integer,
      "comments_count": integer,
      "tags": ["string"],
      "created_at": "string (ISO datetime)",
      "user_compatibility": {
        "allergen_warnings": ["string"],
        "dietary_match": boolean
      }
    }
  ],
  "has_more": boolean
}
```

## Error Handling

All endpoints follow a consistent error response format:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": {}
  }
}
```

### Common Error Codes

- `400` - Bad Request: Malformed request or invalid parameters
- `401` - Unauthorized: Authentication failure
- `403` - Forbidden: Insufficient permissions
- `404` - Not Found: Resource not found
- `422` - Unprocessable Entity: Valid request but unable to process
- `429` - Too Many Requests: Rate limit exceeded
- `500` - Internal Server Error: Server-side error

## Webhooks

BiteWise API supports webhooks for real-time notifications:

```http
POST /webhooks
```

**Request Body**:

```json
{
  "url": "string",
  "events": ["string"],
  "secret": "string"
}
```

**Response** (201 Created):

```json
{
  "webhook_id": "string",
  "created_at": "string (ISO datetime)"
}
```

### Supported Webhook Events

- `user.updated` - User profile was updated
- `meal.logged` - New meal entry was added to diary
- `recipe.shared` - New recipe was shared to community
- `goal.achieved` - User achieved a nutrition or health goal

## SDK Documentation

Official SDK libraries are available for:

- Python: [BiteWise Python SDK](https://github.com/bitewise/python-sdk)
- JavaScript: [BiteWise JavaScript SDK](https://github.com/bitewise/js-sdk)
- Swift: [BiteWise iOS SDK](https://github.com/bitewise/ios-sdk)
- Kotlin: [BiteWise Android SDK](https://github.com/bitewise/android-sdk)

Visit our [Developer Hub](https://developers.bitewise.com) for detailed guides and examples.
