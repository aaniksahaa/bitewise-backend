# DB Schema - PGSQL

enums

```jsx
CREATE TYPE gender_type AS ENUM ('male', 'female', 'non_binary', 'other', 'prefer_not_to_say');

CREATE TYPE cooking_skill_level_type AS ENUM ('beginner', 'intermediate', 'advanced', 'expert');

CREATE TYPE ingredient_measurement_unit_type AS ENUM ('gram', 'kilogram', 'milliliter', 'liter', 'teaspoon', 'tablespoon', 'cup', 'ounce', 'pound', 'piece', 'slice', 'pinch', 'serving');
```

```jsx
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- Hashed password for security
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    gender gender_type,
    date_of_birth DATE,
    location_city VARCHAR(100),
    location_country VARCHAR(100),
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    profile_image_url VARCHAR(255),
    bio TEXT,
    
    dietary_restrictions TEXT[], -- e.g., ['vegan', 'gluten-free']
    allergies TEXT[], -- e.g., ['nuts', 'dairy']
    medical_conditions TEXT[], -- e.g., ['diabetes', 'hypertension']
    fitness_goals TEXT[], -- e.g., ['weight_loss', 'muscle_gain']
    taste_preferences TEXT[], -- e.g., ['spicy', 'savory']
    cuisine_interests TEXT[], -- e.g., ['Italian', 'Indian']
    cooking_skill_level cooking_skill_level_type DEFAULT 'beginner',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMPTZ,
    is_admin BOOLEAN DEFAULT FALSE,
    email_notifications_enabled BOOLEAN DEFAULT TRUE,
    push_notifications_enabled BOOLEAN DEFAULT TRUE
);
```

health_profiles table is the current profile and the history is like a versioning

```jsx
-- Main table
CREATE TABLE health_profiles (
    health_profile_id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id BIGINT UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    height_cm DECIMAL(5,2),
    weight_kg DECIMAL(5,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- History table
CREATE TABLE health_profile_history (
    history_id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    health_profile_id BIGINT NOT NULL REFERENCES health_profiles(health_profile_id) ON DELETE CASCADE,
    height_cm DECIMAL(5,2),
    weight_kg DECIMAL(5,2),
    change_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_health_profile FOREIGN KEY (health_profile_id) REFERENCES health_profiles(health_profile_id)
);

-- Trigger function
CREATE OR REPLACE FUNCTION log_health_profile_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.height_cm IS DISTINCT FROM NEW.height_cm OR OLD.weight_kg IS DISTINCT FROM NEW.weight_kg THEN
        INSERT INTO health_profile_history (health_profile_id, height_cm, weight_kg, change_timestamp)
        VALUES (OLD.health_profile_id, OLD.height_cm, OLD.weight_kg, CURRENT_TIMESTAMP);
    END IF;
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger
CREATE TRIGGER health_profile_update_trigger
BEFORE UPDATE ON health_profiles
FOR EACH ROW
EXECUTE FUNCTION log_health_profile_changes();
```

```jsx
CREATE TABLE ingredients (
    ingredient_id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name VARCHAR(100) UNIQUE NOT NULL, -- e.g., 'Egg', 'Sugar', 'Hilsa Fish'
    unit_type ingredient_measurement_unit_type NOT NULL,
    default_serving_size DECIMAL(10,2) NOT NULL, -- e.g., 1 for egg, 100 for fish (grams)
    calories_per_serving DECIMAL(10,2), -- Calories per default serving
    protein_g_per_serving DECIMAL(10,2), -- Protein in grams
    carbs_g_per_serving DECIMAL(10,2), -- Carbohydrates in grams
    fats_g_per_serving DECIMAL(10,2), -- Fats in grams
    vitamins_json JSONB, -- e.g., {'vitamin_a': '100IU', 'vitamin_c': '5mg'}
    image_url VARCHAR(255), -- URL for ingredient image
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

```jsx
CREATE TABLE dishes (
    dish_id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name VARCHAR(100) NOT NULL, -- e.g., 'Chicken Curry'
    description TEXT, -- Short description of the dish
    cuisine VARCHAR(50), -- e.g., 'Indian', 'Italian', 'Mexican'
    created_by_user_id BIGINT REFERENCES users(user_id) ON DELETE SET NULL, -- Optional, for user-created dishes
    recipe_text TEXT, -- Detailed cooking instructions
    prep_time_minutes INTEGER CHECK (prep_time_minutes >= 0), -- Preparation time, non-negative
    cook_time_minutes INTEGER CHECK (cook_time_minutes >= 0), -- Cooking time, non-negative
    image_urls VARCHAR(255)[], -- Array of URLs or file paths to dish images
    servings INTEGER CHECK (servings > 0), -- Number of servings, positive
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

```jsx
CREATE TABLE dish_ingredients (
    dish_ingredient_id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    dish_id BIGINT NOT NULL REFERENCES dishes(dish_id) ON DELETE CASCADE,
    ingredient_id BIGINT NOT NULL REFERENCES ingredients(ingredient_id) ON DELETE RESTRICT,
    quantity DECIMAL(10,2) NOT NULL, -- Amount in ingredient's unit (e.g., 2 eggs, 100g rice)
    UNIQUE(dish_id, ingredient_id)
);
```

```jsx
CREATE TABLE menus (
    menu_id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL, -- e.g., 'Birthday Party Menu'
    occasion VARCHAR(100), -- e.g., 'Birthday', 'Dinner Party'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

```jsx
CREATE TABLE menu_dishes (
    menu_dish_id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    menu_id BIGINT NOT NULL REFERENCES menus(menu_id) ON DELETE CASCADE,
    dish_id BIGINT NOT NULL REFERENCES dishes(dish_id) ON DELETE RESTRICT,
    UNIQUE(menu_id, dish_id)
);
```

```jsx
CREATE TABLE intakes (
    intake_id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    dish_id BIGINT NOT NULL REFERENCES dishes(dish_id) ON DELETE RESTRICT,
    intake_time TIMESTAMP WITH TIME ZONE NOT NULL, -- When the dish was consumed
    portion_size DECIMAL(5,2) DEFAULT 1.0, -- Portion relative to dish serving size
    water_ml INTEGER, -- Optional water intake in milliliters
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

Food diary table not needed, it is basically just all the recent intakes, SQL

```jsx
CREATE TABLE fitness_plans (
    fitness_plan_id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    goal_type VARCHAR(50) NOT NULL, -- e.g., 'weight_loss', 'muscle_gain'
    target_weight_kg DECIMAL(5,2), -- Optional target weight
    target_calories_per_day INTEGER, -- Daily calorie target
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    suggestions JSONB, -- Free-form JSON for LLM-generated suggestions
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

```jsx
CREATE TABLE posts (
    post_id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL, -- Blog content or description
    dish_id BIGINT REFERENCES dishes(dish_id) ON DELETE SET NULL, -- Optional link to a dish
    tags TEXT[], -- e.g., ['vegan', 'low-carb']
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

```jsx
CREATE TABLE comments (
    comment_id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    post_id BIGINT NOT NULL REFERENCES posts(post_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

```jsx
CREATE TABLE streaks (
    streak_id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    streak_type VARCHAR(50) NOT NULL, -- e.g., 'allergy_free_meals', 'balanced_nutrition'
    current_count INTEGER DEFAULT 0, -- Current streak length
    last_updated DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

```jsx
CREATE TABLE conversations (
    conversation_id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

```jsx
CREATE TABLE messages (
    message_id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    conversation_id BIGINT NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    content TEXT NOT NULL, -- User input or AI response
    is_user_message BOOLEAN NOT NULL, -- True for user, False for AI
    llm_model_id BIGINT REFERENCES llm_models(llm_model_id) ON DELETE SET NULL, -- Nullable for user messages
    input_tokens INTEGER, -- Tokens used for input (NULL for user messages)
    output_tokens INTEGER, -- Tokens used for output (NULL for user messages)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

```jsx
CREATE TABLE llm_models (
    llm_model_id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    model_name VARCHAR(100) NOT NULL, -- e.g., 'Gemini-2.0-flash'
    provider_name VARCHAR(100) NOT NULL, -- e.g., 'Google'
    model_nickname VARCHAR(100), -- e.g., 'Gemini Flash'
    cost_per_million_input_tokens DECIMAL(10,4) NOT NULL, -- USD per million input tokens
    cost_per_million_output_tokens DECIMAL(10,4) NOT NULL, -- USD per million output tokens
    is_available BOOLEAN DEFAULT TRUE, -- Indicates if the model is currently usable
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(model_name, provider_name) -- Ensure no duplicate models
);
```