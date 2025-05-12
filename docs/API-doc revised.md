# API-doc revised

# BiteWise AI Assistant API Documentation

## Overview

This documentation outlines all endpoints, grouped by module, with detailed request/response schemas, example responses (positive and negative), and implementation notes to guide backend development. Endpoints are designed to align with the database schema and support the project’s features, ensuring scalability, security, and extensibility.

## Base Information

- **Base URL**: `/api/v1`
- **Authentication**: JWT-based Bearer tokens (generated via `/auth/login`).
- **Content Type**: `application/json` (unless specified for file uploads).
- **Error Handling**: Standard HTTP status codes with JSON error responses.
- **Pagination**: Supported for list endpoints (e.g., posts, intakes) with `limit` and `offset` query parameters.
- **Database Schema**: PostgreSQL tables (`users`, `health_profiles`, `ingredients`, `dishes`, etc.) as defined in the provided schema.
- **AI Integration**: LangChain for LLM orchestration, with token/cost tracking in `llm_models` and `messages`.

## Modules and Endpoints

The API is organized into six modules, mirroring the project’s modular structure:

1. **User Management**: Authentication, profile, and health profile management.
2. **Conversational AI**: AI chat, multimodal input processing, and health calculations.
3. **Food Diary**: Food intake logging and nutritional analysis.
4. **Recipe Management**: Ingredient detection, recipe suggestions, and dish/menu management.
5. **Community**: Posts, comments, and streaks.
6. **Fitness Planning**: Fitness goals, meal plans, and progress tracking.

Each endpoint includes:

- **HTTP Method and Path**
- **Description**
- **Request Parameters** (path, query, body, headers)
- **Response Schemas** (success and error)
- **Example Responses** (positive and negative)
- **Implementation Notes** (database interactions, AI integration, etc.)

---

## 1. User Management Module

Handles user authentication, profile updates, and health profile management.

### 1.1. User Signup

- **Method**: `POST`
- **Path**: `/auth/signup`
- **Description**: Creates a new user account with basic profile and health information.
- **Request**:
    - **Body** (JSON):
        
        ```json
        {
          "email": "string",
          "password": "string",
        	"username": "string"
        }
        ```
        
    
- **Response**:
    - **Success** (201 Created):
        
        ```json
        {
          "user_id": "integer",
          "email": "string",
          "username": "string",
          "created_at": "string (ISO 8601)"
        }
        
        ```
        
    - **Error** (400 Bad Request, 409 Conflict):
        
        ```json
        {
          "detail": "string"
        }
        
        ```
        
- **Example Responses**:
    - **Positive**:
        
        ```json
        {
          "user_id": 1,
          "email": "user@example.com",
          "first_name": "John",
          "created_at": "2025-05-10T12:00:00Z"
        }
        
        ```
        
    - **Negative** (409 Conflict):
        
        ```json
        {
          "detail": "Email already exists"
        }
        
        ```
        
- **Implementation Notes**:
    - Hash password using bcrypt before storing in `users.password_hash`.
    - Insert user data into `users` table and health data into `health_profiles`.
    - Validate email uniqueness and password strength (min 8 characters).
    - Use transactions to ensure atomicity between `users` and `health_profiles` inserts.

### 1.2. User Login

- **Method**: `POST`
- **Path**: `/auth/login`
- **Description**: Authenticates a user and returns a JWT token.
- **Request**:
    - **Body** (JSON):
        
        ```json
        {
          "email": "string",
          "password": "string"
        }
        
        ```
        
- **Response**:
    - **Success** (200 OK):
        
        ```json
        {
          "access_token": "string",
          "token_type": "bearer",
          "user_id": "integer",
          "email": "string"
        }
        
        ```
        
    - **Error** (401 Unauthorized):
        
        ```json
        {
          "detail": "Invalid credentials"
        }
        
        ```
        
- **Example Responses**:
    - **Positive**:
        
        ```json
        {
          "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
          "token_type": "bearer",
          "user_id": 1,
          "email": "user@example.com"
        }
        
        ```
        
    - **Negative**:
        
        ```json
        {
          "detail": "Invalid credentials"
        }
        
        ```
        
- **Implementation Notes**:
    - Verify password against `users.password_hash` using bcrypt.
    - Generate JWT with user_id and email, set expiration (e.g., 1 hour).
    - Update `users.last_login_at` on successful login.

### 1.3. Get User Profile

- **Method**: `GET`
- **Path**: `/users/profile`
- **Description**: Retrieves the authenticated user’s profile and health data.
- **Request**:
    - **Headers**:
        - `Authorization: Bearer <token>`
- **Response**:
    - **Success** (200 OK):
        
        ```json
        {
          "user_id": "integer",
          "email": "string",
          "first_name": "string",
          "last_name": "string | null",
          "gender": "string | null",
          "date_of_birth": "string | null",
          "location_city": "string | null",
          "location_country": "string | null",
          "latitude": "number | null",
          "longitude": "number | null",
          "height_cm": "number | null",
          "weight_kg": "number | null",
          "dietary_restrictions": "string[] | null",
          "allergies": "string[] | null",
          "medical_conditions": "string[] | null",
          "fitness_goals": "string[] | null",
          "taste_preferences": "string[] | null",
          "cuisine_interests": "string[] | null",
          "cooking_skill_level": "string | null",
          "created_at": "string (ISO 8601)"
        }
        
        ```
        
    - **Error** (401 Unauthorized):
        
        ```json
        {
          "detail": "Invalid or expired token"
        }
        
        ```
        
- **Example Responses**:
    - **Positive**:
        
        ```json
        {
          "user_id": 1,
          "email": "user@example.com",
          "first_name": "John",
          "last_name": "Doe",
          "gender": "male",
          "date_of_birth": "1990-01-01",
          "location_city": "New York",
          "location_country": "USA",
          "latitude": 40.7128,
          "longitude": -74.0060,
          "height_cm": 175.5,
          "weight_kg": 70.0,
          "dietary_restrictions": ["vegan"],
          "allergies": ["nuts"],
          "medical_conditions": ["hypertension"],
          "fitness_goals": ["weight_loss"],
          "taste_preferences": ["spicy"],
          "cuisine_interests": ["Indian"],
          "cooking_skill_level": "intermediate",
          "created_at": "2025-05-10T12:00:00Z"
        }
        
        ```
        
    - **Negative**:
        
        ```json
        {
          "detail": "Invalid or expired token"
        }
        
        ```
        
- **Implementation Notes**:
    - Join `users` and `health_profiles` tables on `user_id`.
    - Use JWT to extract `user_id` and validate authorization.
    - Cache profile data (e.g., Redis) for frequent access.

### 1.4. Update User Profile

- **Method**: `PUT`
- **Path**: `/users/profile`
- **Description**: Updates the authenticated user’s profile and health data.
- **Request**:
    - **Headers**:
        - `Authorization: Bearer <token>`
    - **Body** (JSON, partial update):
        
        ```json
        {
          "first_name": "string | null",
          "last_name": "string | null",
          "gender": "male | female | non_binary | other | prefer_not_to_say | null",
          "date_of_birth": "string (YYYY-MM-DD) | null",
          "location_city": "string | null",
          "location_country": "string | null",
          "latitude": "number | null",
          "longitude": "number | null",
          "height_cm": "number | null",
          "weight_kg": "number | null",
          "dietary_restrictions": "string[] | null",
          "allergies": "string[] | null",
          "medical_conditions": "string[] | null",
          "fitness_goals": "string[] | null",
          "taste_preferences": "string[] | null",
          "cuisine_interests": "string[] | null",
          "cooking_skill_level": "beginner | intermediate | advanced | expert | null"
        }
        
        ```
        
- **Response**:
    - **Success** (200 OK):
        
        ```json
        {
          "user_id": "integer",
          "email": "string",
          "first_name": "string",
          "updated_at": "string (ISO 8601)"
        }
        
        ```
        
    - **Error** (401 Unauthorized, 400 Bad Request):
        
        ```json
        {
          "detail": "string"
        }
        
        ```
        
- **Example Responses**:
    - **Positive**:
        
        ```json
        {
          "user_id": 1,
          "email": "user@example.com",
          "first_name": "John",
          "updated_at": "2025-05-10T12:30:00Z"
        }
        
        ```
        
    - **Negative** (400 Bad Request):
        
        ```json
        {
          "detail": "Invalid height_cm value"
        }
        
        ```
        
- **Implementation Notes**:
    - Update `users` and `health_profiles` tables, triggering `health_profile_history` insert if `height_cm` or `weight_kg` changes.
    - Use transactions to ensure atomicity.
    - Validate inputs (e.g., `height_cm > 0`, `cooking_skill_level` in enum).

### 1.5. Create User Profile

- **Method**: `POST`
- **Path**: `/users/profile`
- **Description**: Creates the authenticated user’s profile and health data.
- **Request**:
    - **Headers**:
        - `Authorization: Bearer <token>`
    - **Body** (JSON):
    
       
    
    ```json
    {
    	"email": "string",
      "first_name": "string",
      "last_name": "string | null",
      "gender": "male | female | non_binary | other | prefer_not_to_say | null",
      "date_of_birth": "string (YYYY-MM-DD) | null",
      "location_city": "string | null",
      "location_country": "string | null",
      "latitude": "number | null",
      "longitude": "number | null",
      "height_cm": "number | null",
      "weight_kg": "number | null",
      "dietary_restrictions": "string[] | null",
      "allergies": "string[] | null",
      "medical_conditions": "string[] | null",
      "fitness_goals": "string[] | null",
      "taste_preferences": "string[] | null",
      "cuisine_interests": "string[] | null",
      "cooking_skill_level": "beginner | intermediate | advanced | expert | null"
    }
    ```
    
- **Response**:
    - **Success** (201 Created):
    
    ```json
    {
      "user_id": 2,
      "email": "newuser@example.com",
      "first_name": "Jane",
      "last_name": "Smith",
      "created_at": "2025-05-11T10:00:00Z"
    }
    
    ```
    
    - **Error** (400 Bad Request – validation error):
    
    ```json
    {
      "detail": "Email is already registered"
    }
    
    ```
    
    - **Error** (422 Unprocessable Entity – invalid data format):
    
    ```json
    {
      "detail": [
        {
          "loc": ["body", "email"],
          "msg": "value is not a valid email address",
          "type": "value_error.email"
        }
      ]
    }
    ```
    
- **Example Requests**:
    - **Positive**:
    
    ```json
    {
      "email": "newuser@example.com",
      "first_name": "Jane",
      "last_name": "Smith",
      "gender": "female",
      "date_of_birth": "1985-06-15",
      "location_city": "Los Angeles",
      "location_country": "USA",
      "latitude": 34.0522,
      "longitude": -118.2437,
      "height_cm": 165.0,
      "weight_kg": 58.0,
      "dietary_restrictions": ["vegetarian"],
      "allergies": ["shellfish"],
      "medical_conditions": ["diabetes"],
      "fitness_goals": ["muscle_gain"],
      "taste_preferences": ["sweet"],
      "cuisine_interests": ["Mexican"],
      "cooking_skill_level": "beginner"
    }
    ```
    
    - **Negative**:
    
    ```json
    {
      "email": "invalid-email",
      "password": "short",
      "first_name": ""
    }
    ```
    
- **Implementation Notes**:
    - Hash the password before storing it using a secure algorithm (e.g., bcrypt).
    - Validate all fields against expected formats and constraints.
    - Insert into both `users` and `health_profiles` tables, ensuring transactional integrity.
    - Return minimal user details upon successful creation to avoid leaking sensitive data.
    - Consider rate-limiting this endpoint to prevent abuse or brute-force attacks.

---

## 2. Conversational AI Module

### 2.1. Create New Conversation

- **Method**: `POST`
- **Path**: `/chat/conversations`
- **Description**: Creates a new conversation for the authenticated user.
- **Request**:
    - **Headers**:
        - `Authorization perceived`: `Bearer <token>`
- **Response**:
    - **Success** (201 Created):
        
        ```json
        {
          "conversation_id": "integer",
          "user_id": "integer",
          "started_at": "string (ISO 8601)"
        }
        
        ```
        
    - **Error** (401 Unauthorized):
        
        ```json
        {
          "detail": "Invalid or expired token"
        }
        
        ```
        
- **Example Responses**:
    - **Positive**:
        
        ```json
        {
          "conversation_id": 1,
          "user_id": 1,
          "started_at": "2025-05-10T12:00:00Z"
        }
        
        ```
        
    - **Negative**:
        
        ```json
        {
          "detail": "Invalid or expired token"
        }
        
        ```
        
- **Implementation Notes**:
    - Insert a new record into the `conversations` table with `user_id` from the JWT and `started_at` as the current timestamp.
    - Ensure the user is authenticated via JWT.
    - Return the newly created `conversation_id` for subsequent chat interactions.

### 2.2. Get Conversations

- **Method**: `GET`
- **Path**: `/chat/conversations`
- **Description**: Retrieves a list of the authenticated user’s conversations, ordered by `started_at` (descending).
- **Request**:
    - **Headers**:
        - `Authorization: Bearer <token>`
    - **Query Parameters**:
        - `limit`: `integer` (default: 20)
        - `offset`: `integer` (default: 0)
- **Response**:
    - **Success** (200 OK):
        
        ```json
        {
          "conversations": [
            {
              "conversation_id": "integer",
              "started_at": "string (ISO 8601)",
              "last_message": {
                "message_id": "integer | null",
                "content": "string | null",
                "created_at": "string (ISO 8601) | null",
                "is_user_message": "boolean | null"
              }
            }
          ],
          "total_count": "integer"
        }
        
        ```
        
    - **Error** (401 Unauthorized):
        
        ```json
        {
          "detail": "Invalid or expired token"
        }
        
        ```
        
- **Example Responses**:
    - **Positive**:
        
        ```json
        {
          "conversations": [
            {
              "conversation_id": 1,
              "started_at": "2025-05-10T12:00:00Z",
              "last_message": {
                "message_id": 2,
                "content": "You ate 1 pizza (800 kcal).",
                "created_at": "2025-05-10T12:15:00Z",
                "is_user_message": false
              }
            }
          ],
          "total_count": 1
        }
        
        ```
        
    - **Negative**:
        
        ```json
        {
          "detail": "Invalid or expired token"
        }
        
        ```
        
- **Implementation Notes**:
    - Query the `conversations` table for records matching the authenticated `user_id`.
    - Left join with `messages` to get the most recent message per conversation (using a subquery or window function).
    - Use indexes on `conversations.user_id` and `conversations.started_at` for performance.
    - Apply pagination with `limit` and `offset`.

### 2.3. Get Conversation History

- **Method**: `GET`
- **Path**: `/chat/conversations/{conversation_id}/messages`
- **Description**: Retrieves the message history for a specific conversation, ordered by `created_at` (ascending).
- **Request**:
    - **Headers**:
        - `Authorization: Bearer <token>`
    - **Path Parameters**:
        - `conversation_id`: `integer`
    - **Query Parameters**:
        - `limit`: `integer` (default: 50)
        - `offset`: `integer` (default: 0)
- **Response**:
    - **Success** (200 OK):
        
        ```json
        {
          "messages": [
            {
              "message_id": "integer",
              "conversation_id": "integer",
              "user_id": "integer",
              "content": "string",
              "is_user_message": "boolean",
              "llm_model_id": "integer | null",
              "input_tokens": "integer | null",
              "output_tokens": "integer | null",
              "created_at": "string (ISO 8601)"
            }
          ],
          "total_count": "integer"
        }
        
        ```
        
    - **Error** (401 Unauthorized, 404 Not Found):
        
        ```json
        {
          "detail": "string"
        }
        
        ```
        
- **Example Responses**:
    - **Positive**:
        
        ```json
        {
          "messages": [
            {
              "message_id": 1,
              "conversation_id": 1,
              "user_id": 1,
              "content": "I ate 1 pizza today.",
              "is_user_message": true,
              "llm_model_id": null,
              "input_tokens": null,
              "output_tokens": null,
              "created_at": "2025-05-10T12:10:00Z"
            },
            {
              "message_id": 2,
              "conversation_id": 1,
              "user_id": 1,
              "content": "You ate 1 pizza (approx. 800 kcal, 30g protein). This exceeds your daily calorie goal by 200 kcal.",
              "is_user_message": false,
              "llm_model_id": 1,
              "input_tokens": 50,
              "output_tokens": 70,
              "created_at": "2025-05-10T12:15:00Z"
            }
          ],
          "total_count": 2
        }
        
        ```
        
    - **Negative** (404 Not Found):
        
        ```json
        {
          "detail": "Conversation not found or access denied"
        }
        
        ```
        
- **Implementation Notes**:
    - Query the `messages` table for records matching `conversation_id` and `user_id` (to prevent unauthorized access).
    - Use index on `messages.conversation_id` and `messages.created_at` for efficient sorting.
    - Apply pagination with `limit` and `offset`.
    - Ensure `llm_model_id`, `input_tokens`, and `output_tokens` are null for user messages.

### 2.4. Send Chat Message

- **Method**: `POST`
- **Path**: `/chat/conversations/{conversation_id}/messages`
- **Description**: Sends a message (text or multiple base64-encoded images) in a specific conversation, processes it with the AI, and returns the response. Logs food intake to the diary if applicable.
- **Request**:
    - **Headers**:
        - `Authorization: Bearer <token>`
    - **Path Parameters**:
        - `conversation_id`: `integer`
    - **Body** (JSON):
        
        ```json
        {
          "content": "string | null",
          "images_base64": "string[] | null" // Array of base64-encoded images (e.g., JPEG, PNG)
        }
        
        ```
        
- **Response**:
    - **Success** (200 OK):
        
        ```json
        {
          "message_id": "integer",
          "conversation_id": "integer",
          "user_id": "integer",
          "content": "string",
          "is_user_message": false,
          "llm_model_id": "integer",
          "input_tokens": "integer",
          "output_tokens": "integer",
          "created_at": "string (ISO 8601)",
          "intake_id": "integer | null" // If food intake was logged
        }
        
        ```
        
    - **Error** (401 Unauthorized, 400 Bad Request, 404 Not Found):
        
        ```json
        {
          "detail": "string"
        }
        
        ```
        
- **Example Responses**:
    - **Positive** (Text and multiple images, food logged):
        
        ```json
        {
          "message_id": 2,
          "conversation_id": 1,
          "user_id": 1,
          "content": "You provided images of 1 pizza and a salad (total: 900 kcal, 35g protein). The pizza exceeds your daily calorie goal by 200 kcal, but the salad helps balance it.",
          "is_user_message": false,
          "llm_model_id": 1,
          "input_tokens": 100,
          "output_tokens": 80,
          "created_at": "2025-05-10T12:15:00Z",
          "intake_id": 1
        }
        
        ```
        
    - **Negative** (Invalid input):
        
        ```json
        {
          "detail": "Either content or images_base64 must be provided"
        }
        
        ```
        
- **Implementation Notes**:
    - Validate that at least one of `content` or `images_base64` is provided.
    - Verify `conversation_id` exists in `conversations` and belongs to the authenticated `user_id`.
    - Fetch user’s health profile (`users`, `health_profiles`) to prepend to LLM prompt for personalization.
    - For text input, use NLP (via LangChain, Gemini-2.0-flash) to process the message.
    - For `images_base64`, iterate through the array, decode each base64 string, validate image formats (e.g., JPEG, PNG) and size (e.g., max 5MB per image), and use computer vision (YOLO/ResNet) to detect ingredients in each image.
    - If food is detected (e.g., “I ate 1 pizza” or pizza/salad in images), log to `intakes` table, linking to `dishes`/`ingredients`.
    - Insert user message and AI response into `messages` table, setting `is_user_message` appropriately.
    - Use `LLMClient` to call the LLM, track `input_tokens`, `output_tokens`, and `llm_model_id` (referencing `llm_models` table).
    - Calculate and store LLM costs based on `llm_models.cost_per_million_input_tokens` and `cost_per_million_output_tokens`.
    - Use transactions to ensure atomicity for message and intake inserts.
    - Optionally store image URLs (e.g., in AWS S3) in `messages.content` for auditing, if images are persisted.
    - Cache health profile data (e.g., in Redis) for frequent access.

### 2.5. Calculate Health Metric

- **Method**: `POST`
- **Path**: `/chat/conversations/{conversation_id}/calculate`
- **Description**: Performs health calculations (e.g., BMI, BMR) within a conversation, returning a dynamic widget response for the user or another person.
- **Request**:
    - **Headers**:
        - `Authorization: Bearer <token>`
    - **Path Parameters**:
        - `conversation_id`: `integer`
    - **Body** (JSON):
        
        ```json
        {
          "metric_type": "bmi | bmr",
          "height_cm": "number | null",
          "weight_kg": "number | null",
          "age": "integer | null",
          "gender": "male | female | non_binary | other | null"
        }
        
        ```
        
- **Response**:
    - **Success** (200 OK):
        
        ```json
        {
          "message_id": "integer",
          "conversation_id": "integer",
          "metric_type": "string",
          "result": "number",
          "widget_data": {
            "description": "string",
            "input_fields": [
              { "name": "string", "value": "string | number" }
            ],
            "result_label": "string"
          },
          "is_user_message": false,
          "llm_model_id": "integer",
          "input_tokens": "integer",
          "output_tokens": "integer",
          "created_at": "string (ISO 8601)"
        }
        
        ```
        
    - **Error** (401 Unauthorized, 400 Bad Request, 404 Not Found):
        
        ```json
        {
          "detail": "string"
        }
        
        ```
        
- **Example Responses**:
    - **Positive** (BMI calculation):
        
        ```json
        {
          "message_id": 3,
          "conversation_id": 1,
          "metric_type": "bmi",
          "result": 22.5,
          "widget_data": {
            "description": "Your BMI is in the healthy range (18.5-24.9).",
            "input_fields": [
              { "name": "height_cm", "value": 175.5 },
              { "name": "weight_kg", "value": 70.0 }
            ],
            "result_label": "BMI: 22.5"
          },
          "is_user_message": false,
          "llm_model_id": 1,
          "input_tokens": 30,
          "output_tokens": 50,
          "created_at": "2025-05-10T12:20:00Z"
        }
        
        ```
        
    - **Negative**:
        
        ```json
        {
          "detail": "Missing required field: height_cm"
        }
        
        ```
        
- **Implementation Notes**:
    - Verify `conversation_id` exists and belongs to the authenticated `user_id`.
    - If `height_cm` or `weight_kg` are null, use user’s `health_profiles` data for calculations.
    - Calculate BMI (`weight_kg / (height_cm/100)^2`) or BMR (Harris-Benedict formula).
    - Generate `widget_data` for frontend rendering (e.g., input fields for re-calculation).
    - Insert the calculation request and response into `messages` table, setting `is_user_message` to false.
    - Use `LLMClient` to format the response via Gemini-2.0-flash, tracking tokens and costs.
    - Store `llm_model_id`, `input_tokens`, and `output_tokens` in `messages`.

---

---

## 3. Food Diary Module

Manages food intake logging and nutritional analysis.

### 3.1. Log Food Intake

- **Method**: `POST`
- **Path**: `/diary/intakes`
- **Description**: Manually logs a food intake for the user’s diary.
- **Request**:
    - **Headers**:
        - `Authorization: Bearer <token>`
    - **Body** (JSON):
        
        ```json
        {
          "dish_id": "integer",
          "intake_time": "string (ISO 8601)",
          "portion_size": "number",
          "water_ml": "integer | null"
        }
        
        ```
        
- **Response**:
    - **Success** (201 Created):
        
        ```json
        {
          "intake_id": "integer",
          "dish_id": "integer",
          "intake_time": "string (ISO 8601)",
          "portion_size": "number",
          "water_ml": "integer | null",
          "created_at": "string (ISO 8601)"
        }
        
        ```
        
    - **Error** (400 Bad Request, 404 Not Found):
        
        ```json
        {
          "detail": "string"
        }
        
        ```
        
- **Example Responses**:
    - **Positive**:
        
        ```json
        {
          "intake_id": 1,
          "dish_id": 1,
          "intake_time": "2025-05-10T12:00:00Z",
          "portion_size": 1.0,
          "water_ml": 500,
          "created_at": "2025-05-10T12:00:00Z"
        }
        
        ```
        
    - **Negative**:
        
        ```json
        {
          "detail": "Dish not found"
        }
        
        ```
        
- **Implementation Notes**:
    - Insert into `intakes` table, linking to `dishes`.
    - Validate `dish_id` exists and `portion_size > 0`.
    - Check dish ingredients against user’s `allergies` and `dietary_restrictions` before logging.
    - Update `streaks` if applicable (e.g., allergy-free meal).

### 3.2. Get Food Diary

- **Method**: `GET`
- **Path**: `/diary/intakes`
- **Description**: Retrieves the user’s food diary with nutritional summaries.
- **Request**:
    - **Headers**:
        - `Authorization: Bearer <token>`
    - **Query Parameters**:
        - `start_date`: `string (YYYY-MM-DD)` (optional)
        - `end_date`: `string (YYYY-MM-DD)` (optional)
        - `limit`: `integer` (default: 50)
        - `offset`: `integer` (default: 0)
- **Response**:
    - **Success** (200 OK):
        
        ```json
        {
          "intakes": [
            {
              "intake_id": "integer",
              "dish_id": "integer",
              "dish_name": "string",
              "intake_time": "string (ISO 8601)",
              "portion_size": "number",
              "water_ml": "integer | null",
              "nutrition": {
                "calories": "number",
                "protein_g": "number",
                "carbs_g": "number",
                "fats_g": "number"
              }
            }
          ],
          "total_count": "integer",
          "summary": {
            "total_calories": "number",
            "total_protein_g": "number",
            "total_carbs_g": "number",
            "total_fats_g": "number"
          }
        }
        
        ```
        
    - **Error** (401 Unauthorized):
        
        ```json
        {
          "detail": "Invalid or expired token"
        }
        
        ```
        
- **Example Responses**:
    - **Positive**:
        
        ```json
        {
          "intakes": [
            {
              "intake_id": 1,
              "dish_id": 1,
              "dish_name": "Chicken Curry",
              "intake_time": "2025-05-10T12:00:00Z",
              "portion_size": 1.0,
              "water_ml": 500,
              "nutrition": {
                "calories": 600,
                "protein_g": 30,
                "carbs_g": 50,
                "fats_g": 20
              }
            }
          ],
          "total_count": 1,
          "summary": {
            "total_calories": 600,
            "total_protein_g": 30,
            "total_carbs_g": 50,
            "total_fats_g": 20
          }
        }
        
        ```
        
    - **Negative**:
        
        ```json
        {
          "detail": "Invalid or expired token"
        }
        
        ```
        
- **Implementation Notes**:
    - Join `intakes`, `dishes`, and `dish_ingredients` to compute nutritional data.
    - Aggregate `calories`, `protein_g`, etc., from `ingredients` table, scaled by `portion_size`.
    - Use indexes on `intakes.intake_time` and `intakes.user_id` for performance.
    - Filter by `start_date` and `end_date` if provided.

---

## 4. Dishes Module

Handles the management of dishes and their associated ingredients, including creation, retrieval, and searching of dishes. This module focuses on core CRUD operations for dishes and avoids business-layer functionalities like ingredient detection or recipe suggestion, which are handled by the AI or other modules. The module aligns with the `dishes`, `dish_ingredients`, and `ingredients` tables in the PostgreSQL schema, supporting search capabilities to facilitate RAG-based filtering.

### 4.1. Create Dish

- **Method**: `POST`
- **Path**: `/dishes`
- **Description**: Creates a new dish with its ingredients and recipe details.
- **Request**:
    - **Headers**:
        - `Authorization: Bearer <token>`
    - **Body** (JSON):
        
        ```json
        {
          "name": "string",
          "description": "string | null",
          "recipe_text": "string | null",
          "prep_time_minutes": "integer | null",
          "cook_time_minutes": "integer | null",
          "ingredients": [
            {
              "ingredient_id": "integer",
              "quantity": "number"
            }
          ]
        }
        
        ```
        
- **Response**:
    - **Success** (201 Created):
        
        ```json
        {
          "dish_id": "integer",
          "name": "string",
          "created_at": "string (ISO 8601)"
        }
        
        ```
        
    - **Error** (400 Bad Request, 404 Not Found):
        
        ```json
        {
          "detail": "string"
        }
        
        ```
        
- **Example Responses**:
    - **Positive**:
        
        ```json
        {
          "dish_id": 1,
          "name": "Chicken Curry",
          "created_at": "2025-05-10T12:00:00Z"
        }
        
        ```
        
    - **Negative**:
        
        ```json
        {
          "detail": "Invalid ingredient_id"
        }
        
        ```
        
- **Implementation Notes**:
    - Insert into `dishes` table, setting `created_by_user_id` to the authenticated user’s `user_id`.
    - Insert associated ingredients into `dish_ingredients` table.
    - Validate `ingredient_id` exists in `ingredients` table and `quantity > 0`.
    - Use transactions to ensure atomicity between `dishes` and `dish_ingredients` inserts.
    - Validate inputs (e.g., `name` is non-empty, `prep_time_minutes` is positive).

### 4.2. Get Dish

- **Method**: `GET`
- **Path**: `/dishes/{dish_id}`
- **Description**: Retrieves details of a specific dish, including its ingredients and nutritional data.
- **Request**:
    - **Headers**:
        - `Authorization: Bearer <token>`
    - **Path Parameters**:
        - `dish_id`: `integer`
- **Response**:
    - **Success** (200 OK):
        
        ```json
        {
          "dish_id": "integer",
          "name": "string",
          "description": "string | null",
          "recipe_text": "string | null",
          "prep_time_minutes": "integer | null",
          "cook_time_minutes": "integer | null",
          "created_by_user_id": "integer | null",
          "created_at": "string (ISO 8601)",
          "ingredients": [
            {
              "ingredient_id": "integer",
              "name": "string",
              "quantity": "number",
              "unit_type": "string",
              "nutrition": {
                "calories": "number",
                "protein_g": "number",
                "carbs_g": "number",
                "fats_g": "number"
              }
            }
          ],
          "total_nutrition": {
            "calories": "number",
            "protein_g": "number",
            "carbs_g": "number",
            "fats_g": "number"
          }
        }
        
        ```
        
    - **Error** (404 Not Found, 401 Unauthorized):
        
        ```json
        {
          "detail": "string"
        }
        
        ```
        
- **Example Responses**:
    - **Positive**:
        
        ```json
        {
          "dish_id": 1,
          "name": "Scrambled Eggs",
          "description": "Fluffy scrambled eggs with a hint of salt.",
          "recipe_text": "Beat 2 eggs, cook on low heat, add salt.",
          "prep_time_minutes": 5,
          "cook_time_minutes": 10,
          "created_by_user_id": 1,
          "created_at": "2025-05-10T12:00:00Z",
          "ingredients": [
            {
              "ingredient_id": 1,
              "name": "Egg",
              "quantity": 2,
              "unit_type": "piece",
              "nutrition": {
                "calories": 80,
                "protein_g": 6,
                "carbs_g": 1,
                "fats_g": 5
              }
            },
            {
              "ingredient_id": 3,
              "name": "Salt",
              "quantity": 1,
              "unit_type": "pinch",
              "nutrition": {
                "calories": 0,
                "protein_g": 0,
                "carbs_g": 0,
                "fats_g": 0
              }
            }
          ],
          "total_nutrition": {
            "calories": 160,
            "protein_g": 12,
            "carbs_g": 2,
            "fats_g": 10
          }
        }
        
        ```
        
    - **Negative**:
        
        ```json
        {
          "detail": "Dish not found"
        }
        
        ```
        
- **Implementation Notes**:
    - Query `dishes` table for the specified `dish_id`.
    - Join `dish_ingredients` and `ingredients` tables to retrieve ingredient details and nutritional data.
    - Calculate `total_nutrition` by summing ingredient nutritional values, scaled by `quantity`.
    - Ensure the user is authenticated, but allow access to all dishes (no ownership restriction).
    - Use index on `dishes.dish_id` for efficient retrieval.

### 4.3. Search Dishes

- **Method**: `GET`
- **Path**: `/dishes`
- **Description**: Retrieves a paginated list of dishes, filtered by a search query to support RAG-based filtering. The search query matches dish names, descriptions, or ingredient names.
- **Request**:
    - **Headers**:
        - `Authorization: Bearer <token>`
    - **Query Parameters**:
        - `search_query`: `string` (optional, e.g., “curry” or “vegan”)
        - `limit`: `integer` (default: 20)
        - `offset`: `integer` (default: 0)
- **Response**:
    - **Success** (200 OK):
        
        ```json
        {
          "dishes": [
            {
              "dish_id": "integer",
              "name": "string",
              "description": "string | null",
              "prep_time_minutes": "integer | null",
              "cook_time_minutes": "integer | null",
              "created_by_user_id": "integer | null",
              "created_at": "string (ISO 8601)",
              "ingredient_names": "string[]",
              "total_nutrition": {
                "calories": "number",
                "protein_g": "number",
                "carbs_g": "number",
                "fats_g": "number"
              }
            }
          ],
          "total_count": "integer"
        }
        
        ```
        
    - **Error** (401 Unauthorized):
        
        ```json
        {
          "detail": "string"
        }
        
        ```
        
- **Example Responses**:
    - **Positive** (Search for “curry”):
        
        ```json
        {
          "dishes": [
            {
              "dish_id": 1,
              "name": "Chicken Curry",
              "description": "Spicy chicken curry with rice.",
              "prep_time_minutes": 15,
              "cook_time_minutes": 30,
              "created_by_user_id": 1,
              "created_at": "2025-05-10T12:00:00Z",
              "ingredient_names": ["Chicken", "Rice", "Curry Powder"],
              "total_nutrition": {
                "calories": 600,
                "protein_g": 30,
                "carbs_g": 50,
                "fats_g": 20
              }
            }
          ],
          "total_count": 1
        }
        
        ```
        
    - **Negative**:
        
        ```json
        {
          "detail": "Invalid or expired token"
        }
        
        ```
        
- **Implementation Notes**:
    - Query `dishes` table, joining with `dish_ingredients` and `ingredients` to include ingredient names.
    - If `search_query` is provided, use PostgreSQL full-text search (e.g., `to_tsvector` on `dishes.name`, `dishes.description`, and `ingredients.name`) to filter results.
    - Alternatively, integrate with Qdrant vector search for RAG-based filtering if embeddings are precomputed for dishes and ingredients.
    - Calculate `total_nutrition` by summing ingredient nutritional values.
    - Use indexes on `dishes.created_at` and `ingredients.name` for performance.
    - Apply pagination with `limit` and `offset`.
    - Aggregate `ingredient_names` as an array for display purposes.
    - Ensure the user is authenticated, but allow access to all dishes.

---

## 5. Community Module

Handles social features for posts, comments, and streaks.

### 5.1. Create Post

- **Method**: `POST`
- **Path**: `/community/posts`
- **Description**: Creates a new community post with optional dish link.
- **Request**:
    - **Headers**:
        - `Authorization: Bearer <token>`
    - **Body** (JSON):
        
        ```json
        {
          "title": "string",
          "content": "string",
          "dish_id": "integer | null",
          "tags": "string[] | null"
        }
        
        ```
        
- **Response**:
    - **Success** (201 Created):
        
        ```json
        {
          "post_id": "integer",
          "title": "string",
          "created_at": "string (ISO 8601)"
        }
        
        ```
        
    - **Error** (400 Bad Request, 404 Not Found):
        
        ```json
        {
          "detail": "string"
        }
        
        ```
        
- **Example Responses**:
    - **Positive**:
        
        ```json
        {
          "post_id": 1,
          "title": "My Vegan Curry Recipe",
          "created_at": "2025-05-10T12:00:00Z"
        }
        
        ```
        
    - **Negative**:
        
        ```json
        {
          "detail": "Invalid dish_id"
        }
        
        ```
        
- **Implementation Notes**:
    - Insert into `posts` table, linking to `dishes` if `dish_id` provided.
    - Validate `dish_id` exists if specified.
    - Optionally use AI moderation (via Conversational AI Module) to flag inappropriate content.

### 5.2. Get Community Feed

- **Method**: `GET`
- **Path**: `/community/posts`
- **Description**: Retrieves a paginated feed of community posts.
- **Request**:
    - **Headers**:
        - `Authorization: Bearer <token>`
    - **Query Parameters**:
        - `limit`: `integer` (default: 20)
        - `offset`: `integer` (default: 0)
        - `tags`: `string[]` (optional, filter by tags)
- **Response**:
    - **Success** (200 OK):
        
        ```json
        {
          "posts": [
            {
              "post_id": "integer",
              "user_id": "integer",
              "username": "string",
              "title": "string",
              "content": "string",
              "dish_id": "integer | null",
              "dish_name": "string | null",
              "tags": "string[] | null",
              "created_at": "string (ISO 8601)"
            }
          ],
          "total_count": "integer"
        }
        
        ```
        
    - **Error** (401 Unauthorized):
        
        ```json
        {
          "detail": "Invalid or expired token"
        }
        
        ```
        
- **Example Responses**:
    - **Positive**:
        
        ```json
        {
          "posts": [
            {
              "post_id": 1,
              "user_id": 1,
              "username": "John Doe",
              "title": "My Vegan Curry Recipe",
              "content": "Check out this delicious curry I made!",
              "dish_id": 1,
              "dish_name": "Vegan Curry",
              "tags": ["vegan", "spicy"],
              "created_at": "2025-05-10T12:00:00Z"
            }
          ],
          "total_count": 1
        }
        
        ```
        
    - **Negative**:
        
        ```json
        {
          "detail": "Invalid or expired token"
        }
        
        ```
        
- **Implementation Notes**:
    - Join `posts`, `users`, and `dishes` tables for feed data.
    - Filter by `tags` using PostgreSQL array operations.
    - Use index on `posts.created_at` for efficient sorting/pagination.

### 5.3. Update Streak

- **Method**: `POST`
- **Path**: `/community/streaks`
- **Description**: Updates a user’s streak (e.g., allergy-free meals).
- **Request**:
    - **Headers**:
        - `Authorization: Bearer <token>`
    - **Body** (JSON):
        
        ```json
        {
          "streak_type": "string",
          "increment": "boolean" // True to increment, False to reset
        }
        
        ```
        
- **Response**:
    - **Success** (200 OK):
        
        ```json
        {
          "streak_id": "integer",
          "streak_type": "string",
          "current_count": "integer",
          "last_updated": "string (ISO 8601)"
        }
        
        ```
        
    - **Error** (400 Bad Request):
        
        ```json
        {
          "detail": "string"
        }
        
        ```
        
- **Example Responses**:
    - **Positive**:
        
        ```json
        {
          "streak_id": 1,
          "streak_type": "allergy_free_meals",
          "current_count": 5,
          "last_updated": "2025-05-10T00:00:00Z"
        }
        
        ```
        
    - **Negative**:
        
        ```json
        {
          "detail": "Invalid streak_type"
        }
        
        ```
        
- **Implementation Notes**:
    - Update or insert into `streaks` table.
    - Validate `streak_type` (e.g., predefined list).
    - Check `last_updated` to prevent multiple updates in a day.

---

## 6. Fitness Planning Module

Manages fitness goals, meal plans, and progress tracking.

### 6.1. Create Fitness Plan

- **Method**: `POST`
- **Path**: `/fitness/plans`
- **Description**: Creates a fitness plan with AI-generated meal suggestions.
- **Request**:
    - **Headers**:
        - `Authorization: Bearer <token>`
    - **Body** (JSON):
        
        ```json
        {
          "goal_type": "string",
          "target_weight_kg": "number | null",
          "target_calories_per_day": "integer | null",
          "start_date": "string (YYYY-MM-DD)",
          "end_date": "string (YYYY-MM-DD)"
        }
        
        ```
        
- **Response**:
    - **Success** (201 Created):
        
        ```json
        {
          "fitness_plan_id": "integer",
          "goal_type": "string",
          "start_date": "string (ISO 8601)",
          "end_date": "string (ISO 8601)",
          "suggestions": "object" // JSONB field
        }
        
        ```
        
    - **Error** (400 Bad Request):
        
        ```json
        {
          "detail": "string"
        }
        
        ```
        
- **Example Responses**:
    - **Positive**:
        
        ```json
        {
          "fitness_plan_id": 1,
          "goal_type": "weight_loss",
          "start_date": "2025-05-10T00:00:00Z",
          "end_date": "2025-05-24T00:00:00Z",
          "suggestions": {
            "daily_meals": [
              {
                "meal_type": "breakfast",
                "dish_id": 1,
                "dish_name": "Oatmeal",
                "calories": 200
              }
            ]
          }
        }
        
        ```
        
    - **Negative**:
        
        ```json
        {
          "detail": "End date must be after start date"
        }
        
        ```
        
- **Implementation Notes**:
    - Insert into `fitness_plans` table.
    - Use Conversational AI Module to generate `suggestions` (JSONB) based on user’s health profile and `goal_type`.
    - Validate dates and `goal_type` (e.g., “weight_loss”, “muscle_gain”).

### 6.2. Get Fitness Progress

- **Method**: `GET`
- **Path**: `/fitness/plans/{plan_id}/progress`
- **Description**: Retrieves progress against a fitness plan, comparing intakes to targets.
- **Request**:
    - **Headers**:
        - `Authorization: Bearer <token>`
    - **Path Parameters**:
        - `plan_id`: `integer`
- **Response**:
    - **Success** (200 OK):
        
        ```json
        {
          "fitness_plan_id": "integer",
          "goal_type": "string",
          "progress": {
            "days_completed": "integer",
            "total_calories_consumed": "number",
            "target_calories": "number",
            "calorie_deficit": "number"
          }
        }
        
        ```
        
    - **Error** (404 Not Found):
        
        ```json
        {
          "detail": "Fitness plan not found"
        }
        
        ```
        
- **Example Responses**:
    - **Positive**:
        
        ```json
        {
          "fitness_plan_id": 1,
          "goal_type": "weight_loss",
          "progress": {
            "days_completed": 5,
            "total_calories_consumed": 8000,
            "target_calories": 10000,
            "calorie_deficit": 2000
          }
        }
        
        ```
        
    - **Negative**:
        
        ```json
        {
          "detail": "Fitness plan not found"
        }
        
        ```
        
- **Implementation Notes**:
    - Join `fitness_plans` and `intakes` to calculate consumed calories.
    - Compute `calorie_deficit` as `target_calories - total_calories_consumed`.
    - Restrict access to user’s own plans (`fitness_plans.user_id`).

---

## Implementation Guidelines

- **FastAPI Setup**:
    - Use routers for each module (e.g., `auth_router`, `chat_router`).
    - Implement dependency injection for JWT authentication (`Depends(oauth2_scheme)`).
    - Enable CORS for frontend integration.
- **Database Access**:
    - Use SQLAlchemy or asyncpg for PostgreSQL queries.
    - Create repository classes (e.g., `UserRepository`, `IntakeRepository`) for each module.
    - Leverage indexes (e.g., `intakes.intake_time`, `posts.created_at`) for performance.
- **AI Integration**:
    - Implement `LLMClient` class to handle Gemini API calls, token tracking, and cost calculation.
    - Store LLM metadata in `messages` (e.g., `input_tokens`, `output_tokens`, `llm_model_id`).
    - Use curated prompts with user context (health profile, dietary restrictions).
- **Security**:
    - Validate all inputs (e.g., enum values, positive numbers).
    - Sanitize user inputs to prevent SQL injection or XSS (handled by FastAPI).
    - Restrict endpoints to authenticated users via JWT.
- **Scalability**:
    - Cache frequent queries (e.g., user profiles, ingredient data) in Redis.
    - Use connection pooling for PostgreSQL.
    - Deploy on AWS/Google Cloud with load balancing for API and LLM calls.
- **Error Handling**:
    - Return consistent error responses (`{"detail": "message"}`).
    - Log errors for debugging (e.g., using `logging` module).
- **Testing**:
    - Write unit tests for each endpoint (e.g., using `pytest`, `TestClient`).
    - Test AI responses with varied inputs (text, images, health profiles).
    - Perform integration tests for cross-module workflows (e.g., chat-to-diary logging).

---