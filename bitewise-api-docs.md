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

## Authentication Endpoints

### Traditional Authentication

#### User Registration

```http
POST /auth/register
```

Creates a new user account with email and password authentication.

**Request Body**:

```json
{
  "email": "string",
  "password": "string",
  "username": "string",
  "first_name": "string",
  "last_name": "string",
  "accept_terms": boolean
}
```

**Validation Requirements**:
- Email must be valid and unique
- Password must be at least 8 characters with uppercase, lowercase, number, and special character
- Username must be unique and 3-30 characters
- accept_terms must be true

**Response** (201 Created):

```json
{
  "user_id": "string",
  "email": "string",
  "username": "string",
  "access_token": "string",
  "refresh_token": "string",
  "expires_in": 3600,
  "token_type": "Bearer",
  "email_verification_required": boolean,
  "created_at": "string (ISO datetime)"
}
```

**Error Response** (422 Unprocessable Entity):

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": {
      "email": ["Email already exists"],
      "password": ["Password must contain at least one uppercase letter"]
    }
  }
}
```

#### User Login

```http
POST /auth/login
```

Authenticates a user with email and password credentials.

**Request Body**:

```json
{
  "email": "string",
  "password": "string",
  "remember_me": boolean
}
```

**Response** (200 OK):

```json
{
  "user_id": "string",
  "email": "string",
  "username": "string",
  "access_token": "string",
  "refresh_token": "string",
  "expires_in": 3600,
  "token_type": "Bearer",
  "last_login": "string (ISO datetime)",
  "profile_complete": boolean
}
```

**Error Response** (401 Unauthorized):

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password"
  }
}
```

#### Logout

```http
POST /auth/logout
```

Invalidates the current authentication token.

**Headers**:
- `Authorization: Bearer {access_token}`

**Response** (200 OK):

```json
{
  "message": "Successfully logged out"
}
```

#### Refresh Token

```http
POST /auth/refresh
```

Generates a new access token using a valid refresh token.

**Request Body**:

```json
{
  "refresh_token": "string"
}
```

**Response** (200 OK):

```json
{
  "access_token": "string",
  "refresh_token": "string",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

**Error Response** (401 Unauthorized):

```json
{
  "error": {
    "code": "INVALID_REFRESH_TOKEN",
    "message": "Refresh token is invalid or expired"
  }
}
```

#### Verify Email

```http
POST /auth/verify-email
```

Verifies a user's email address using a verification token.

**Request Body**:

```json
{
  "email": "string",
  "verification_token": "string"
}
```

**Response** (200 OK):

```json
{
  "message": "Email verified successfully",
  "email_verified": true,
  "verified_at": "string (ISO datetime)"
}
```

#### Resend Verification Email

```http
POST /auth/resend-verification
```

Sends a new email verification link to the user's email address.

**Request Body**:

```json
{
  "email": "string"
}
```

**Response** (200 OK):

```json
{
  "message": "Verification email sent successfully"
}
```

#### Request Password Reset

```http
POST /auth/forgot-password
```

Initiates password reset process by sending a reset link to the user's email.

**Request Body**:

```json
{
  "email": "string"
}
```

**Response** (200 OK):

```json
{
  "message": "Password reset email sent if account exists"
}
```

Note: This endpoint always returns success to prevent email enumeration attacks.

#### Reset Password

```http
POST /auth/reset-password
```

Resets user password using a valid reset token.

**Request Body**:

```json
{
  "email": "string",
  "reset_token": "string",
  "new_password": "string",
  "confirm_password": "string"
}
```

**Response** (200 OK):

```json
{
  "message": "Password reset successfully"
}
```

**Error Response** (400 Bad Request):

```json
{
  "error": {
    "code": "INVALID_RESET_TOKEN",
    "message": "Reset token is invalid or expired"
  }
}
```

#### Change Password

```http
POST /auth/change-password
```

Changes the password for an authenticated user.

**Headers**:
- `Authorization: Bearer {access_token}`

**Request Body**:

```json
{
  "current_password": "string",
  "new_password": "string",
  "confirm_password": "string"
}
```

**Response** (200 OK):

```json
{
  "message": "Password changed successfully"
}
```

### Google OAuth Authentication

#### Google OAuth Login URL

```http
GET /auth/google/login
```

Generates Google OAuth authorization URL for user authentication.

**Query Parameters**:
- `redirect_uri` (string, optional): Custom redirect URI after authentication
- `state` (string, optional): State parameter for security

**Response** (200 OK):

```json
{
  "authorization_url": "https://accounts.google.com/oauth/authorize?client_id=...",
  "state": "string"
}
```

#### Google OAuth Callback (GET)

```http
GET /auth/google/callback
```

Handles Google OAuth callback via direct redirect from Google. This is the traditional OAuth flow where Google redirects the user directly to this endpoint.

**Query Parameters**:
- `code` (string, required): Authorization code from Google
- `state` (string, optional): State parameter for security

**Response** (200 OK):

```json
{
  "user_id": "string",
  "access_token": "string",
  "refresh_token": "string",
  "expires_in": 3600,
  "token_type": "bearer",
  "is_new_user": boolean
}
```

#### Google OAuth Callback (POST)

```http
POST /auth/google/callback
```

Handles Google OAuth callback via POST request from frontend. This is for frontend applications that capture the callback and send it as an API call.

**Request Body**:

```json
{
  "code": "string",
  "state": "string"
}
```

**Response** (200 OK) - Existing User:

```json
{
  "user_id": "string",
  "access_token": "string",
  "refresh_token": "string",
  "expires_in": 3600,
  "token_type": "bearer",
  "is_new_user": false
}
```

**Response** (201 Created) - New User:

```json
{
  "user_id": "string", 
  "access_token": "string",
  "refresh_token": "string",
  "expires_in": 3600,
  "token_type": "bearer",
  "is_new_user": true
}
```

#### Link Google Account

```http
POST /auth/google/link
```

Links a Google account to an existing authenticated user account.

**Headers**:
- `Authorization: Bearer {access_token}`

**Request Body**:

```json
{
  "code": "string",
  "state": "string"
}
```

**Response** (200 OK):

```json
{
  "message": "Google account linked successfully",
  "google_email": "string",
  "linked_at": "string (ISO datetime)"
}
```

#### Unlink Google Account

```http
DELETE /auth/google/unlink
```

Removes Google account linkage from user profile.

**Headers**:
- `Authorization: Bearer {access_token}`

**Response** (200 OK):

```json
{
  "message": "Google account unlinked successfully"
}
```

### Account Management

#### Get Current User

```http
GET /auth/me
```

Retrieves the currently authenticated user's information.

**Headers**:
- `Authorization: Bearer {access_token}`

**Response** (200 OK):

```json
{
  "user_id": "string",
  "email": "string",
  "username": "string",
  "first_name": "string",
  "last_name": "string",
  "email_verified": boolean,
  "profile_complete": boolean,
  "provider": "email|google",
  "google_linked": boolean,
  "created_at": "string (ISO datetime)",
  "last_login": "string (ISO datetime)",
  "avatar_url": "string"
}
```

#### Update Account Info

```http
PATCH /auth/me
```

Updates the current user's account information.

**Headers**:
- `Authorization: Bearer {access_token}`

**Request Body**:

```json
{
  "first_name": "string",
  "last_name": "string",
  "username": "string",
  "avatar": "base64_encoded_string"
}
```

**Response** (200 OK):

```json
{
  "user_id": "string",
  "updated_fields": ["first_name", "username"],
  "updated_at": "string (ISO datetime)"
}
```

#### Delete Account

```http
DELETE /auth/me
```

Permanently deletes the user's account and all associated data.

**Headers**:
- `Authorization: Bearer {access_token}`

**Request Body**:

```json
{
  "password": "string",
  "confirmation": "DELETE_MY_ACCOUNT"
}
```

**Response** (200 OK):

```json
{
  "message": "Account deleted successfully",
  "deleted_at": "string (ISO datetime)"
}
```

### Session Management

#### Get Active Sessions

```http
GET /auth/sessions
```

Retrieves all active sessions for the authenticated user.

**Headers**:
- `Authorization: Bearer {access_token}`

**Response** (200 OK):

```json
{
  "sessions": [
    {
      "session_id": "string",
      "device_info": {
        "user_agent": "string",
        "ip_address": "string",
        "location": "string",
        "device_type": "mobile|desktop|tablet"
      },
      "created_at": "string (ISO datetime)",
      "last_activity": "string (ISO datetime)",
      "is_current": boolean
    }
  ]
}
```

#### Revoke Session

```http
DELETE /auth/sessions/{session_id}
```

Revokes a specific session, invalidating its tokens.

**Headers**:
- `Authorization: Bearer {access_token}`

**Path Parameters**:
- `session_id` (string, required): Session identifier to revoke

**Response** (200 OK):

```json
{
  "message": "Session revoked successfully"
}
```

#### Revoke All Sessions

```http
DELETE /auth/sessions
```

Revokes all sessions except the current one.

**Headers**:
- `Authorization: Bearer {access_token}`

**Response** (200 OK):

```json
{
  "message": "All other sessions revoked successfully",
  "revoked_count": integer
}
```

### Two-Factor Authentication (2FA)

#### Enable 2FA

```http
POST /auth/2fa/enable
```

Enables two-factor authentication for the user account.

**Headers**:
- `Authorization: Bearer {access_token}`

**Response** (200 OK):

```json
{
  "qr_code": "base64_encoded_qr_image",
  "secret": "string",
  "backup_codes": ["string"],
  "setup_url": "string"
}
```

#### Confirm 2FA Setup

```http
POST /auth/2fa/confirm
```

Confirms 2FA setup with a verification code.

**Headers**:
- `Authorization: Bearer {access_token}`

**Request Body**:

```json
{
  "totp_code": "string"
}
```

**Response** (200 OK):

```json
{
  "message": "2FA enabled successfully",
  "enabled_at": "string (ISO datetime)"
}
```

#### Disable 2FA

```http
POST /auth/2fa/disable
```

Disables two-factor authentication.

**Headers**:
- `Authorization: Bearer {access_token}`

**Request Body**:

```json
{
  "password": "string",
  "totp_code": "string"
}
```

**Response** (200 OK):

```json
{
  "message": "2FA disabled successfully"
}
```

#### Verify 2FA Code

```http
POST /auth/2fa/verify
```

Verifies a 2FA code during login process.

**Request Body**:

```json
{
  "email": "string",
  "totp_code": "string",
  "temporary_token": "string"
}
```

**Response** (200 OK):

```json
{
  "access_token": "string",
  "refresh_token": "string",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

### Authentication Usage Examples

#### Frontend Integration

```javascript
// User registration
const registerUser = async (userData) => {
  const response = await fetch('/api/v1/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(userData)
  });
  
  if (response.ok) {
    const data = await response.json();
    // Store tokens securely
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    return data;
  }
  throw new Error('Registration failed');
};

// User login
const loginUser = async (email, password) => {
  const response = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ email, password })
  });
  
  if (response.ok) {
    const data = await response.json();
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    return data;
  }
  throw new Error('Login failed');
};

// Google OAuth flow
const initiateGoogleAuth = async () => {
  const response = await fetch('/api/v1/auth/google/login');
  const data = await response.json();
  
  // Redirect to Google OAuth using the returned authorization URL
  window.location.href = data.authorization_url;
};

// Handle OAuth callback (called from your frontend route that receives the code)
const handleGoogleCallback = async (code, state) => {
  const response = await fetch('/api/v1/auth/google/callback', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ code, state })
  });
  
  if (response.ok) {
    const data = await response.json();
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    
    if (data.is_new_user) {
      // Redirect to profile setup for new users
      window.location.href = '/setup-profile';
    } else {
      // Redirect to dashboard for existing users
      window.location.href = '/dashboard';
    }
  } else {
    console.error('Google authentication failed');
    window.location.href = '/login?error=oauth_failed';
  }
};

// Token refresh
const refreshToken = async () => {
  const refreshToken = localStorage.getItem('refresh_token');
  
  const response = await fetch('/api/v1/auth/refresh', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ refresh_token: refreshToken })
  });
  
  if (response.ok) {
    const data = await response.json();
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    return data.access_token;
  }
  
  // Refresh failed, redirect to login
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  window.location.href = '/login';
};

// Authenticated API request with auto-refresh
const makeAuthenticatedRequest = async (url, options = {}) => {
  let token = localStorage.getItem('access_token');
  
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (response.status === 401) {
    // Token expired, try to refresh
    token = await refreshToken();
    
    // Retry original request
    return fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${token}`
      }
    });
  }
  
  return response;
};
```

#### Security Best Practices

1. **Token Storage**: Store tokens securely (httpOnly cookies preferred over localStorage)
2. **HTTPS Only**: All authentication endpoints require HTTPS in production
3. **Token Expiration**: Access tokens expire in 1 hour, refresh tokens in 7 days
4. **Rate Limiting**: Login attempts are rate-limited to prevent brute force attacks
5. **Password Requirements**: Strong password policies enforced
6. **2FA Recommended**: Enable two-factor authentication for enhanced security

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

## Statistics API

The statistics endpoints provide comprehensive nutrition analytics, health progress tracking, and consumption pattern analysis for users. All statistics endpoints require authentication and return data specific to the authenticated user.

### Time Range Parameters

Most statistics endpoints now use simplified time range parameters for better usability:

- `unit` (string, required): Time unit - `hour`, `day`, `week`, `month`, `year`
- `num` (integer, required): Number of time units (1-365)

**Examples**:
- Last 7 days: `unit=day&num=7`
- Last 24 hours: `unit=hour&num=24`
- Last 3 months: `unit=month&num=3`
- Last 2 weeks: `unit=week&num=2`

The data granularity automatically matches the time unit:
- `hour` unit returns hourly data points
- `day` unit returns daily data points  
- `week` unit returns weekly data points
- `month` unit returns monthly data points
- `year` unit returns yearly data points

### Quick Dashboard Stats

#### Get Quick Stats

```http
GET /stats/quick
```

Retrieves essential metrics for dashboard display including today's calories, weekly averages, and key health indicators.

**Response** (200 OK):

```json
{
  "today_calories": 1850.5,
  "today_goal_percentage": 92.75,
  "weekly_avg_calories": 1923.2,
  "top_cuisine_this_week": "Mediterranean",
  "total_dishes_tried": 127,
  "current_streak_days": 15,
  "weight_change_this_month": -1.2
}
```

### Comprehensive Analytics

#### Get Comprehensive Stats

```http
GET /stats/comprehensive
```

Retrieves complete statistical analysis including nutrition, consumption patterns, and health progress.

**Query Parameters**:

- `unit` (string, required): Time unit - `hour`, `day`, `week`, `month`, `year`
- `num` (integer, required): Number of time units (1-365)

**Example**: `GET /stats/comprehensive?unit=day&num=30` (last 30 days)

**Response** (200 OK):

```json
{
  "time_range": {
    "start_date": "2024-05-25",
    "end_date": "2024-06-24",
    "period": "daily"
  },
  "nutrition_overview": {
    "calorie_stats": {
      "data_points": [
        {
          "timestamp": "2024-05-25T00:00:00",
          "calories": 2100.5,
          "goal_calories": 2000.0,
          "deficit_surplus": 100.5
        }
      ],
      "avg_daily_calories": 1980.3,
      "total_calories": 59409.0,
      "peak_consumption_hour": 13,
      "days_above_goal": 8,
      "days_below_goal": 22
    },
    "macronutrient_stats": {
      "current_breakdown": {
        "carbs_percentage": 45.2,
        "protein_percentage": 25.8,
        "fats_percentage": 29.0,
        "carbs_grams": 224.5,
        "protein_grams": 128.1,
        "fats_grams": 64.2,
        "fiber_grams": 28.5,
        "sugar_grams": 65.3,
        "saturated_fats_grams": 18.7,
        "unsaturated_fats_grams": 45.5
      },
      "data_points": [
        {
          "date": "2024-05-25",
          "carbs_g": 220.3,
          "protein_g": 125.8,
          "fats_g": 62.1,
          "fiber_g": 27.2,
          "sugar_g": 62.8
        }
      ],
      "avg_breakdown": {
        "carbs_percentage": 46.1,
        "protein_percentage": 24.9,
        "fats_percentage": 29.0,
        "carbs_grams": 218.7,
        "protein_grams": 124.3,
        "fats_grams": 63.1,
        "fiber_grams": 26.8,
        "sugar_grams": 63.5,
        "saturated_fats_grams": 19.2,
        "unsaturated_fats_grams": 43.9
      }
    },
    "micronutrient_stats": {
      "vitamins": {
        "VITAMIN A": {
          "amount": 750.5,
          "unit": "mcg",
          "daily_value_percentage": 83.4
        },
        "VITAMIN C": {
          "amount": 85.2,
          "unit": "mg",
          "daily_value_percentage": 94.7
        }
      },
      "minerals": {
        "Calcium": {
          "amount": 890.3,
          "unit": "mg",
          "daily_value_percentage": 89.0
        },
        "Iron": {
          "amount": 14.2,
          "unit": "mg",
          "daily_value_percentage": 78.9
        }
      },
      "deficiency_alerts": [
        "Low Vitamin D intake: 45.2% of daily value",
        "Low Potassium intake: 62.1% of daily value"
      ]
    }
  },
  "consumption_patterns": {
    "top_dishes": [
      {
        "dish_id": 123,
        "dish_name": "Greek Salad",
        "cuisine": "Mediterranean",
        "consumption_count": 8,
        "last_consumed": "2024-06-20T12:30:00",
        "avg_portion_size": 1.2
      }
    ],
    "cuisine_distribution": [
      {
        "cuisine": "Mediterranean",
        "consumption_count": 25,
        "percentage": 32.1,
        "calories_consumed": 12850.5
      }
    ],
    "eating_patterns": [
      {
        "hour": 7,
        "intake_count": 28,
        "avg_calories": 420.5
      }
    ],
    "dishes_tried_count": 65,
    "unique_cuisines_count": 12,
    "avg_meals_per_day": 3.2,
    "weekend_vs_weekday_ratio": 1.15
  },
  "progress_stats": {
    "health_metrics": [
      {
        "date": "2024-05-25",
        "weight_kg": 72.5,
        "bmi": 23.1,
        "calories_consumed": 2100.5,
        "goal_adherence_percentage": 95.0
      }
    ],
    "weight_trend": "decreasing",
    "avg_goal_adherence": 88.5,
    "dietary_restriction_compliance": 92.3,
    "best_nutrition_day": "2024-06-15",
    "improvement_trend": "improving"
  },
  "advanced_analytics": {
    "correlations": [
      {
        "factor1": "Peak eating hour",
        "factor2": "Total daily calories",
        "correlation_strength": 0.65,
        "description": "Peak consumption occurs at 13:00, suggesting a correlation with daily calorie intake patterns."
      }
    ],
    "predictions": [
      {
        "metric": "Goal adherence",
        "predicted_value": 98.5,
        "confidence_level": 75.0,
        "time_horizon_days": 30,
        "recommendation": "Continue current eating patterns to maintain improvement trend."
      }
    ],
    "optimization_suggestions": [
      "Consider increasing protein intake to 20-30% of total calories for better satiety and muscle maintenance.",
      "Try eating your largest meal earlier in the day to improve metabolism and sleep quality."
    ]
  },
  "generated_at": "2024-06-24T10:30:00Z"
}
```

### Nutrition Analytics

#### Get Calorie Statistics

```http
GET /stats/calories
```

Detailed calorie intake analysis with timeline data and goal tracking.

**Query Parameters**:

- `unit` (string, required): Time unit - `hour`, `day`, `week`, `month`, `year`
- `num` (integer, required): Number of time units (1-365)

**Example**: `GET /stats/calories?unit=day&num=7` (last 7 days)

**Response** (200 OK):

```json
{
  "data_points": [
    {
      "timestamp": "2024-06-18T00:00:00",
      "calories": 2100.5,
      "goal_calories": 2000.0,
      "deficit_surplus": 100.5
    }
  ],
  "avg_daily_calories": 1980.3,
  "total_calories": 13862.1,
  "peak_consumption_hour": 13,
  "days_above_goal": 2,
  "days_below_goal": 5
}
```

#### Get Macronutrient Statistics

```http
GET /stats/macronutrients
```

Macronutrient distribution analysis and trends over time.

**Query Parameters**:

- `unit` (string, required): Time unit - `hour`, `day`, `week`, `month`, `year`
- `num` (integer, required): Number of time units (1-365)

**Example**: `GET /stats/macronutrients?unit=week&num=2` (last 2 weeks)

**Response** (200 OK): *[Similar structure to macronutrient_stats in comprehensive response]*

#### Get Micronutrient Statistics

```http
GET /stats/micronutrients
```

Micronutrient intake analysis with deficiency alerts.

**Query Parameters**:

- `unit` (string, required): Time unit - `hour`, `day`, `week`, `month`, `year`
- `num` (integer, required): Number of time units (1-365)

**Example**: `GET /stats/micronutrients?unit=month&num=1` (last month)

**Response** (200 OK): *[Similar structure to micronutrient_stats in comprehensive response]*

#### Get Nutrition Overview

```http
GET /stats/nutrition-overview
```

Combined nutrition overview including calories, macronutrients, and micronutrients.

**Query Parameters**:

- `unit` (string, required): Time unit - `hour`, `day`, `week`, `month`, `year`
- `num` (integer, required): Number of time units (1-365)

**Example**: `GET /stats/nutrition-overview?unit=day&num=30` (last 30 days)

**Response** (200 OK): *[Includes calorie_stats, macronutrient_stats, and micronutrient_stats]*

### Consumption Patterns

#### Get Consumption Pattern Statistics

```http
GET /stats/consumption-patterns
```

Analysis of food consumption patterns, favorite dishes, and eating habits.

**Query Parameters**:

- `unit` (string, required): Time unit - `hour`, `day`, `week`, `month`, `year`
- `num` (integer, required): Number of time units (1-365)

**Example**: `GET /stats/consumption-patterns?unit=month&num=3` (last 3 months)

**Response** (200 OK): *[Similar structure to consumption_patterns in comprehensive response]*

### Health Progress

#### Get Progress Statistics

```http
GET /stats/progress
```

Health and fitness progress tracking with trend analysis.

**Query Parameters**:

- `unit` (string, required): Time unit - `hour`, `day`, `week`, `month`, `year`
- `num` (integer, required): Number of time units (1-365)

**Example**: `GET /stats/progress?unit=week&num=4` (last 4 weeks)

**Response** (200 OK): *[Similar structure to progress_stats in comprehensive response]*

### Time-Based Summaries

#### Get Weekly Summary

```http
GET /stats/weekly-summary
```

Comprehensive statistics for a specific week.

**Query Parameters**:

- `week_offset` (integer, optional): Weeks ago (0 = current week, 1 = last week, etc.) (default: 0)

**Response** (200 OK): *[Same structure as comprehensive stats]*

#### Get Monthly Summary

```http
GET /stats/monthly-summary
```

Comprehensive statistics for a specific month.

**Query Parameters**:

- `year` (integer, required): Year for the monthly summary
- `month` (integer, required): Month for the summary (1-12)

**Response** (200 OK): *[Same structure as comprehensive stats]*

### Comparative Analytics

#### Get Period Comparison

```http
GET /stats/comparison
```

Compare statistics between two time periods with change analysis.

**Query Parameters**:

- `current_unit` (string, required): Time unit for current period - `hour`, `day`, `week`, `month`, `year`
- `current_num` (integer, required): Number of time units for current period (1-365)
- `previous_unit` (string, required): Time unit for previous period - `hour`, `day`, `week`, `month`, `year`
- `previous_num` (integer, required): Number of time units for previous period (1-365)

**Example**: `GET /stats/comparison?current_unit=week&current_num=1&previous_unit=week&previous_num=1` (this week vs last week)

**Response** (200 OK):

```json
{
  "current_period": {
    "avg_daily_calories": 1980.5,
    "dishes_tried": 15,
    "goal_adherence": 88.5
  },
  "previous_period": {
    "avg_daily_calories": 2150.3,
    "dishes_tried": 12,
    "goal_adherence": 82.1
  },
  "changes": {
    "avg_daily_calories": -7.9,
    "dish_variety": 25.0,
    "goal_adherence": 7.8
  },
  "insights": [
    "Calorie intake decreased by 7.9% compared to previous period",
    "Dish variety increased by 25.0%",
    "Goal adherence improved by 7.8%"
  ]
}
```

#### Get Trend Analysis

```http
GET /stats/trends
```

Trend analysis for various metrics over time with insights.

**Query Parameters**:

- `unit` (string, optional): Time unit for trend analysis - `hour`, `day`, `week`, `month`, `year` (default: `day`)
- `num` (integer, optional): Number of time units to analyze (7-365) (default: 30)

**Example**: `GET /stats/trends?unit=day&num=30` (30-day trend analysis)

**Response** (200 OK):

```json
{
  "period": "30 days",
  "calorie_trend": [
    {
      "date": "2024-05-25",
      "calories": 2100.5
    }
  ],
  "macronutrient_trend": [
    {
      "date": "2024-05-25",
      "carbs": 220.3,
      "protein": 125.8,
      "fats": 62.1
    }
  ],
  "insights": [
    "Consider increasing protein intake to 20-30% of total calories for better satiety and muscle maintenance.",
    "Try eating your largest meal earlier in the day to improve metabolism and sleep quality."
  ]
}
```

### Legacy Endpoints

For backward compatibility, the original date-based endpoints are still available under the `/legacy/` prefix:

#### Get Comprehensive Stats (Legacy)

```http
GET /stats/legacy/comprehensive
```

**Query Parameters**:

- `start_date` (string, required): Start date in YYYY-MM-DD format
- `end_date` (string, required): End date in YYYY-MM-DD format
- `period` (string, optional): Data granularity - `hourly`, `daily`, `weekly`, `monthly`, `yearly` (default: `daily`)

**Response** (200 OK): *[Same structure as new comprehensive stats endpoint]*

## Error Handling

All endpoints use standard HTTP status codes:

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required or invalid token
- `403 Forbidden`: Access denied
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation errors
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

Error responses include details:

```json
{
  "error": {
    "code": "INVALID_DATE_RANGE",
    "message": "Start date must be before or equal to end date",
    "details": {
      "start_date": "2024-06-01",
      "end_date": "2024-05-01"
    }
  }
}
```

## Usage Examples

### Frontend Chart Integration

```javascript
// Get calorie data for chart visualization (last 30 days)
const response = await fetch('/api/v1/stats/calories?unit=day&num=30', {
  headers: {
    'Authorization': 'Bearer ' + token
  }
});

const calorieData = await response.json();

// Use with Chart.js, D3, or other visualization libraries
const chartData = {
  labels: calorieData.data_points.map(point => point.timestamp),
  datasets: [{
    label: 'Daily Calories',
    data: calorieData.data_points.map(point => point.calories),
    borderColor: 'rgb(75, 192, 192)'
  }]
};

// Example for weekly data
const weeklyResponse = await fetch('/api/v1/stats/macronutrients?unit=week&num=8', {
  headers: { 'Authorization': 'Bearer ' + token }
});

const macroData = await weeklyResponse.json();
console.log('8-week macronutrient breakdown:', macroData.current_breakdown);
```

### Dashboard Metrics

```javascript
// Get quick stats for dashboard
const quickStats = await fetch('/api/v1/stats/quick', {
  headers: { 'Authorization': 'Bearer ' + token }
}).then(res => res.json());

// Display key metrics
document.getElementById('todayCalories').textContent = quickStats.today_calories;
document.getElementById('goalProgress').textContent = quickStats.today_goal_percentage + '%';
document.getElementById('weeklyAvg').textContent = quickStats.weekly_avg_calories;
document.getElementById('streakDays').textContent = quickStats.current_streak_days;

// Get comprehensive stats for last 7 days
const weeklyStats = await fetch('/api/v1/stats/comprehensive?unit=day&num=7', {
  headers: { 'Authorization': 'Bearer ' + token }
}).then(res => res.json());

console.log('Weekly nutrition overview:', weeklyStats.nutrition_overview);
```

### Health Progress Tracking

```javascript
// Get progress data for last 3 months
const progressData = await fetch('/api/v1/stats/progress?unit=month&num=3', {
  headers: { 'Authorization': 'Bearer ' + token }
}).then(res => res.json());

// Show weight trend and goal adherence
console.log('Weight trend:', progressData.weight_trend);
console.log('Average goal adherence:', progressData.avg_goal_adherence);
console.log('Best nutrition day:', progressData.best_nutrition_day);

// Get yearly overview for annual report
const yearlyData = await fetch('/api/v1/stats/comprehensive?unit=year&num=1', {
  headers: { 'Authorization': 'Bearer ' + token }
}).then(res => res.json());

console.log('Annual nutrition summary:', yearlyData);
```

### Trend Analysis and Insights

```javascript
// Get 30-day trend analysis
const trendData = await fetch('/api/v1/stats/trends?unit=day&num=30', {
  headers: { 'Authorization': 'Bearer ' + token }
}).then(res => res.json());

// Display trend insights
trendData.insights.forEach(insight => {
  console.log('💡 Insight:', insight);
});

// Compare this week vs last week
const comparison = await fetch('/api/v1/stats/comparison?current_unit=week&current_num=1&previous_unit=week&previous_num=1', {
  headers: { 'Authorization': 'Bearer ' + token }
}).then(res => res.json());

console.log('Week-over-week changes:', comparison.changes);
comparison.insights.forEach(insight => {
  console.log('📊 Change insight:', insight);
});
```

### Consumption Pattern Analysis

```javascript
// Analyze consumption patterns for last 2 months
const patterns = await fetch('/api/v1/stats/consumption-patterns?unit=month&num=2', {
  headers: { 'Authorization': 'Bearer ' + token }
}).then(res => res.json());

// Display favorite dishes and cuisines
console.log('Top 10 dishes:', patterns.top_dishes);
console.log('Cuisine distribution:', patterns.cuisine_distribution);
console.log('Peak eating hours:', patterns.eating_patterns);

// Get hourly eating patterns for today
const hourlyPatterns = await fetch('/api/v1/stats/consumption-patterns?unit=hour&num=24', {
  headers: { 'Authorization': 'Bearer ' + token }
}).then(res => res.json());

console.log('Today\'s eating pattern:', hourlyPatterns.eating_patterns);
```

### Micronutrient Tracking

```javascript
// Check micronutrient status for last month
const microData = await fetch('/api/v1/stats/micronutrients?unit=month&num=1', {
  headers: { 'Authorization': 'Bearer ' + token }
}).then(res => res.json());

// Alert for deficiencies
if (microData.deficiency_alerts.length > 0) {
  console.log('⚠️ Nutritional deficiencies detected:');
  microData.deficiency_alerts.forEach(alert => {
    console.log('-', alert);
  });
}

// Display vitamin and mineral status
console.log('Vitamin levels:', microData.vitamins);
console.log('Mineral levels:', microData.minerals);
```

### Using Legacy Endpoints (Backward Compatibility)

```javascript
// For applications still using date ranges
const legacyData = await fetch('/api/v1/stats/legacy/comprehensive?start_date=2024-05-01&end_date=2024-05-31&period=daily', {
  headers: { 'Authorization': 'Bearer ' + token }
}).then(res => res.json());

console.log('Legacy comprehensive stats:', legacyData);
```

This comprehensive statistics API enables rich analytics and insights for nutrition tracking applications, supporting various frontend visualizations and user engagement features. The simplified time range parameters make it much easier to request common time periods like "last 7 days" or "last 3 months" without having to calculate specific dates.

### Complete Frontend Implementation Example

Here's a complete example of how to implement Google OAuth in your frontend:

#### 1. Frontend Google Login Button Handler

```javascript
// auth.js - API functions
export const authApi = {
  googleLogin: async (redirectUri, state) => {
    const params = new URLSearchParams();
    if (redirectUri) params.append('redirect_uri', redirectUri);
    if (state) params.append('state', state);
    
    const url = `/api/v1/auth/google/login${params.toString() ? '?' + params.toString() : ''}`;
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error('Failed to get Google authorization URL');
    }
    
    return response.json();
  },

  googleCallback: async (code, state) => {
    const response = await fetch('/api/v1/auth/google/callback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ code, state })
    });

    if (!response.ok) {
      throw new Error('Google authentication failed');
    }

    return response.json();
  }
};

// Login component
const GoogleLoginButton = () => {
  const handleGoogleLogin = async () => {
    try {
      const state = Date.now().toString(); // Simple state for CSRF protection
      const redirectUri = `${window.location.origin}/auth/google/callback`;
      
      const { authorization_url } = await authApi.googleLogin(redirectUri, state);
      
      // Store state for verification in callback
      localStorage.setItem('oauth_state', state);
      
      // Redirect to Google OAuth
      window.location.href = authorization_url;
    } catch (error) {
      console.error('Google login failed:', error);
      alert('Google login failed. Please try again.');
    }
  };

  return (
    <button onClick={handleGoogleLogin}>
      Continue with Google
    </button>
  );
};
```

#### 2. Frontend Callback Route Handler

Create a route at `/auth/google/callback` in your frontend:

```javascript
// GoogleCallbackPage.js or similar
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const GoogleCallbackPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Extract code and state from URL
        const urlParams = new URLSearchParams(window.location.search);
        const code = urlParams.get('code');
        const state = urlParams.get('state');
        const storedState = localStorage.getItem('oauth_state');

        // Verify state parameter for CSRF protection
        if (!state || state !== storedState) {
          throw new Error('Invalid state parameter');
        }

        // Clean up stored state
        localStorage.removeItem('oauth_state');

        if (!code) {
          throw new Error('Authorization code not found');
        }

        // Exchange code for tokens via your backend
        const authResult = await authApi.googleCallback(code, state);

        // Store tokens
        localStorage.setItem('access_token', authResult.access_token);
        localStorage.setItem('refresh_token', authResult.refresh_token);
        localStorage.setItem('user_id', authResult.user_id);

        // Redirect based on user status
        if (authResult.is_new_user) {
          navigate('/setup-profile');
        } else {
          navigate('/dashboard');
        }

      } catch (error) {
        console.error('OAuth callback failed:', error);
        setError(error.message);
        setLoading(false);
      }
    };

    handleCallback();
  }, [navigate]);

  if (loading) {
    return <div>Completing Google authentication...</div>;
  }

  if (error) {
    return (
      <div>
        <h2>Authentication Failed</h2>
        <p>{error}</p>
        <button onClick={() => navigate('/login')}>
          Back to Login
        </button>
      </div>
    );
  }

  return null;
};

export default GoogleCallbackPage;
```

#### 3. Router Configuration

Make sure to add the callback route to your router:

```javascript
// App.js or router configuration
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/auth/google/callback" element={<GoogleCallbackPage />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/setup-profile" element={<ProfileSetup />} />
        {/* other routes */}
      </Routes>
    </Router>
  );
}
```

#### 4. Environment Configuration

Make sure your `.env` file has the correct values:

```bash
# Backend .env
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_CALLBACK_URL=http://localhost:8080/auth/google/callback

# Frontend .env (if needed)
VITE_API_BASE_URL=http://localhost:8000
```

#### 5. Google Cloud Console Configuration

In your Google Cloud Console OAuth2 credentials:

**Authorized JavaScript origins:**
- `http://localhost:8080` (development)
- `https://yourdomain.com` (production)

**Authorized redirect URIs:**
- `http://localhost:8080/auth/google/callback` (development)
- `https://yourdomain.com/auth/google/callback` (production)
