# Modules

### Summary of Modules

| **Module** | **Key Features** | **Dependencies** | **Timeline** |
| --- | --- | --- | --- |
| User Management | Signup, login, profile, health profile | None | Phase 1 (0-3 mo) |
| Conversational AI | AI chat, LLM integration, token/cost tracking, dynamic widgets | User Management | Phase 1-2 (0-6 mo) |
| Food Diary | Intake logging, timeline, nutritional trends | User Management, Conversational AI | Phase 2 (4-6 mo) |
| Recipe Management | Ingredient detection, recipe suggestions, dish/menu management | User Management, Conversational AI | Phase 2-3 (4-9 mo) |
| Community | Posts, comments, streaks, social feed | User Management, Recipe Management | Phase 3 (7-9 mo) |
| Fitness Planning | Fitness goals, meal planning, progress tracking, AI suggestions | User Management, Recipe Management, Conv. AI | Phase 3 (7-9 mo) |

To facilitate development of the BiteWise AI Assistant project, dividing the project into independent modules allows for parallel development, easier testing, and better maintainability. Each module should encapsulate a distinct set of features or functionalities, align with the project’s objectives, and minimize dependencies to enable teams to work concurrently. Below, I’ll propose a modular structure based on the project context and schema, ensuring each module is cohesive, covers specific functionalities, and supports the technical stack (React, FastAPI, PostgreSQL, LangChain, etc.). I’ll also outline the scope, key features, dependencies, and development considerations for each module.

The goal is to create modules that are independent enough for separate development but integrate seamlessly to deliver the full BiteWise experience. I’ll consider the schema, user flows, and technical requirements to ensure the division is practical for implementation.

---

### Modular Structure for BiteWise AI Assistant

The project can be divided into **six independent modules**, each focusing on a core aspect of the system. These modules are designed to align with the key features (e.g., conversational AI, food diary, recipe suggestions, community features) and the technical architecture (frontend, backend, AI/ML components). Each module includes its scope, key components, dependencies, and development considerations.

### 1. User Management Module

**Scope**: Handles user authentication, profile management, and health profile configuration.

- **Key Features**:
    - User signup/login (email, Google, GitHub).
    - Profile updates (name, gender, date of birth, location, height, weight).
    - Health profile management (dietary restrictions, allergies, medical conditions, fitness goals, taste preferences, cuisine interests, cooking skill level).
    - Database tables: `users`, `health_profiles`.
- **Frontend Components**:
    - Signup/login forms (React, Tailwind CSS, Shadcn UI).
    - Profile dashboard for editing demographics and health data.
    - Responsive UI for mobile and web.
- **Backend Components**:
    - FastAPI endpoints for user CRUD operations (`/auth/signup`, `/auth/login`, `/users/profile`).
    - Password hashing and JWT-based authentication.
    - PostgreSQL queries for `users` and `health_profiles`.
- **AI/ML Components**: None.
- **Dependencies**:
    - External: Authentication APIs (Google, GitHub OAuth).
    - Internal: None (foundational module).
- **Development Considerations**:
    - Prioritize security (e.g., secure password storage, OAuth integration).
    - Ensure health profile data is easily accessible for other modules (e.g., via API).
    - Use Swagger for API documentation.
    - Estimated timeline: Phase 1 (0-3 months, core feature).

### 2. Conversational AI Module

**Scope**: Implements the AI chat interface for personalized food and nutrition advice, including LLM integration and cost tracking.

- **Key Features**:
    - Conversational AI chat for dietary advice, recipe queries, and health calculations (e.g., BMI, BMR).
    - Prepends user context (health profile, preferences) to LLM prompts.
    - Processes text and image inputs (e.g., meal photos, recipes).
    - Tracks LLM usage (model, tokens, costs) via `llm_models` and `messages`.
    - Dynamic widget rendering for calculations (e.g., BMI calculator in chat).
    - Database tables: `conversations`, `messages`, `llm_models`.
- **Frontend Components**:
    - Chat interface (React, Headless UI, real-time updates).
    - Image upload for meal/recipe inputs.
    - Dynamic widgets for health calculations (e.g., input fields for BMI).
- **Backend Components**:
    - FastAPI endpoints for chat interactions (`/chat/message`, `/chat/upload-image`).
    - LangChain for LLM orchestration (Gemini-2.0-flash, 4.1-mini).
    - Integration with nutrition databases (e.g., USDA FoodData Central).
    - PostgreSQL queries for storing conversations and messages.
- **AI/ML Components**:
    - LLMClient class for calling LLMs, tracking tokens, and selecting models.
    - Multimodal processing (NLP for text, computer vision for images).
    - Prompt engineering to include user context (health profile, dietary restrictions).
- **Dependencies**:
    - External: LLM APIs (Google Gemini), nutrition databases.
    - Internal: User Management Module (for user context/health profile).
- **Development Considerations**:
    - Curate organized, extensible prompt codebase following LLM industry standards.
    - Implement token tracking and cost calculation logic (using `llm_models` rates).
    - Test multimodal inputs (text + images) for accuracy.
    - Estimated timeline: Phase 2 (4-6 months, core feature).

### 3. Food Diary Module

**Scope**: Manages food intake tracking, diary visualization, and nutritional analysis.

- **Key Features**:
    - Logs food intakes (manual or AI-populated) with time, dish, portion size, and water.
    - Visualizes food diary as a timeline (like Google Calendar).
    - Displays nutritional trends (calories, protein, carbs, fats) and flags dietary conflicts (e.g., allergens).
    - Database tables: `food_diaries`, `intakes`, `dishes`, `dish_ingredients`, `ingredients`.
- **Frontend Components**:
    - Food diary timeline UI (React, Tailwind CSS, Shadcn UI).
    - Manual intake form (select dish, portion, time).
    - Nutritional summary charts (e.g., calorie trends).
- **Backend Components**:
    - FastAPI endpoints for intake CRUD (`/diary/intakes`, `/diary/summary`).
    - PostgreSQL queries for intake logging and trend analysis.
    - Logic to validate intakes against health profile (e.g., allergen checks).
- **AI/ML Components**:
    - Integration with Conversational AI Module to auto-populate intakes from chat inputs.
    - NLP for extracting intake details from user messages.
- **Dependencies**:
    - External: Nutrition databases for ingredient data.
    - Internal: User Management Module (health profile), Conversational AI Module (auto-logging).
- **Development Considerations**:
    - Optimize timeline queries for performance (use indexes on `intakes.diary_id`, `intake_time`).
    - Ensure accurate nutritional calculations (sum `dish_ingredients` nutrients).
    - Design visually appealing charts for user engagement.
    - Estimated timeline: Phase 2 (4-6 months, core feature).

### 4. Recipe Management Module

**Scope**: Handles ingredient detection, recipe suggestions, and dish/menu management.

- **Key Features**:
    - Detects ingredients from images (e.g., grocery hauls) or text (e.g., recipes).
    - Suggests recipes based on available ingredients, health profile, and preferences.
    - Manages dishes (ingredients, recipes, nutritional data) and menus (collections of dishes).
    - Supports substitutions for allergens or missing ingredients.
    - Database tables: `ingredients`, `dishes`, `dish_ingredients`, `menus`, `menu_dishes`.
- **Frontend Components**:
    - Recipe suggestion UI (React, Tailwind CSS).
    - Ingredient upload interface (image or text input).
    - Dish/menu creation forms.
- **Backend Components**:
    - FastAPI endpoints for recipe suggestions (`/recipes/suggest`, `/ingredients/detect`).
    - PostgreSQL queries for dish/menu management and ingredient matching.
    - Integration with nutrition databases for nutritional data.
- **AI/ML Components**:
    - Computer vision (YOLO/ResNet) for ingredient detection in images.
    - NLP (BERT-based) for parsing text-based recipes.
    - Multimodal RAG (text + image) for recipe retrieval (handled externally, per your instruction).
- **Dependencies**:
    - External: Nutrition databases, computer vision models.
    - Internal: User Management Module (health profile), Conversational AI Module (chat-based recipe queries).
- **Development Considerations**:
    - Ensure recipe suggestions respect dietary restrictions/allergies.
    - Cache frequent ingredient lookups for performance.
    - Test image-based ingredient detection for accuracy.
    - Estimated timeline: Phase 3 (7-9 months, core feature).

### 5. Community Module

**Scope**: Implements social features for sharing recipes, blogs, and engaging in food-focused challenges.

- **Key Features**:
    - Share posts (recipes, meal photos, blogs) with tags and comments.
    - Follow users, view feeds, and participate in challenges (e.g., allergy-free streaks).
    - Database tables: `posts`, `comments`, `streaks`.
- **Frontend Components**:
    - Social feed UI (React, Shadcn UI).
    - Post creation form (text, images, dish links).
    - Commenting system and streak trackers.
- **Backend Components**:
    - FastAPI endpoints for posts/comments (`/community/posts`, `/community/comments`).
    - PostgreSQL queries for feed generation and streak updates.
- **AI/ML Components**:
    - Optional sentiment analysis for post content (via Conversational AI Module).
    - AI moderation for community posts (e.g., flag inappropriate content).
- **Dependencies**:
    - External: Cloud storage for images (e.g., AWS S3).
    - Internal: User Management Module (user profiles), Recipe Management Module (dish links in posts).
- **Development Considerations**:
    - Implement pagination for feeds to handle large post volumes.
    - Ensure streaks are updated reliably (e.g., daily checks).
    - Design for scalability (e.g., index `posts.created_at`).
    - Estimated timeline: Phase 3 (7-9 months, secondary feature).

### 6. Fitness Planning Module

**Scope**: Manages fitness goals, meal planning, and progress tracking.

- **Key Features**:
    - Create fitness plans (e.g., lose 6kg in 2 weeks) with daily calorie targets.
    - Generate personalized meal plans based on health profile and ingredients.
    - Track progress against goals (e.g., calorie intake vs. target).
    - Store AI-generated suggestions in `suggestions` JSONB field.
    - Database tables: `fitness_plans`, `fitness_plan_meals`.
- **Frontend Components**:
    - Fitness goal setup UI (React, Tailwind CSS).
    - Meal plan visualization (daily/weekly view).
    - Progress charts (e.g., weight loss trends).
- **Backend Components**:
    - FastAPI endpoints for fitness plans (`/fitness/plans`, `/fitness/meals`).
    - PostgreSQL queries for plan creation and progress tracking.
- **AI/ML Components**:
    - LLM-generated meal plans and suggestions (via Conversational AI Module).
    - Integration with Recipe Management Module for meal recommendations.
- **Dependencies**:
    - External: Nutrition databases for meal planning.
    - Internal: User Management Module (health profile), Recipe Management Module (dishes/menus), Conversational AI Module (suggestions).
- **Development Considerations**:
    - Parse `suggestions` JSONB for dynamic frontend rendering.
    - Ensure meal plans align with dietary restrictions.
    - Optimize progress queries (e.g., join `intakes` with `fitness_plans`).
    - Estimated timeline: Phase 3 (7-9 months, secondary feature).

---

### Module Dependencies and Integration

The modules are designed to be as independent as possible, but some dependencies are necessary due to shared data (e.g., health profiles, dishes). Below is a summary of dependencies and integration points:

- **User Management Module**:
    - Foundational module, required by all others for user authentication and health profile data.
    - Provides API endpoints (e.g., `/users/profile`) for other modules to fetch user context.
- **Conversational AI Module**:
    - Depends on User Management for health profile data to prepend to prompts.
    - Integrates with Food Diary (auto-logging intakes) and Recipe Management (recipe queries).
    - Provides AI capabilities (e.g., NLP, suggestions) to Fitness Planning and Community modules.
- **Food Diary Module**:
    - Depends on User Management (health profile) and Conversational AI (auto-logging).
    - Shares `dishes` and `ingredients` with Recipe Management for nutritional data.
- **Recipe Management Module**:
    - Depends on User Management (health profile) and Conversational AI (chat-based queries).
    - Provides dishes/menus to Food Diary (intakes) and Fitness Planning (meal plans).
- **Community Module**:
    - Depends on User Management (user profiles) and Recipe Management (dish links in posts).
    - Optional integration with Conversational AI for sentiment analysis or moderation.
- **Fitness Planning Module**:
    - Depends on User Management (health profile), Recipe Management (dishes/menus), and Conversational AI (suggestions).
    - Integrates with Food Diary to compare intakes against goals.

**Integration Strategy**:

- Use FastAPI for a unified API layer, with endpoints grouped by module (e.g., `/auth/*`, `/chat/*`, `/diary/*`).
- Share database access via PostgreSQL, with clear table ownership (e.g., `messages` owned by Conversational AI).
- Implement API contracts early to allow parallel frontend/backend development.
- Use React’s component-based architecture to map UI components to modules (e.g., `ChatComponent`, `DiaryTimeline`).

---

### Development Roadmap

To align with the project timeline (12 months), here’s how the modules can be prioritized and developed:

- **Phase 1 (0-3 months)**:
    - **User Management Module**: Build authentication and profile management (core foundation).
    - **Conversational AI Module**: Prototype chat interface and LLM integration (key differentiator).
    - Focus: UI/UX design, API scaffolding, LLM prompt engineering.
- **Phase 2 (4-6 months)**:
    - **Food Diary Module**: Develop intake logging and timeline visualization.
    - **Recipe Management Module**: Implement ingredient detection and basic recipe suggestions.
    - Focus: Nutritional calculations, computer vision, backend performance.
- **Phase 3 (7-9 months)**:
    - **Community Module**: Add social features and streaks.
    - **Fitness Planning Module**: Build goal setting and meal planning.
    - Focus: Social engagement, AI-driven suggestions, progress tracking.
- **Phase 4 (10-12 months)**:
    - Integration testing across modules.
    - Beta testing with users, iterative improvements.
    - Marketing and full launch.

**Team Allocation**:

- **Frontend Team**: Split between User Management (auth/profile UI), Conversational AI (chat UI), and Food Diary (timeline UI) initially.
- **Backend Team**: Focus on FastAPI endpoints for User Management and Conversational AI, then Food Diary and Recipe Management.
- **AI/ML Team**: Work on Conversational AI (LLM integration, prompts) and Recipe Management (computer vision, NLP).
- **Cross-functional Team**: Handle Community and Fitness Planning in Phase 3, integrating outputs from other teams.

---

### Development Considerations

- **Modularity**:
    - Use clear module boundaries (e.g., separate FastAPI routers, React component folders).
    - Encapsulate database access per module to avoid tight coupling (e.g., `FoodDiaryService` for `intakes`).
- **Testing**:
    - Write unit tests for each module (e.g., FastAPI endpoints, React components).
    - Test AI components (e.g., LLM prompts, ingredient detection) with diverse inputs.
    - Perform integration tests for cross-module interactions (e.g., chat-to-diary logging).
- **Scalability**:
    - Optimize database queries with indexes (already defined in schema).
    - Use caching (e.g., Redis) for frequent lookups (e.g., ingredient nutritional data).
    - Deploy on AWS/Google Cloud with load balancing for API and LLM calls.
- **User Experience**:
    - Prioritize responsive design for mobile/web (React, Tailwind CSS).
    - Ensure AI responses are friendly and accurate (test with health profile variations).
    - Design intuitive flows for diary logging, recipe discovery, and community engagement.
- **Extensibility**:
    - Keep JSONB fields (e.g., `fitness_plans.suggestions`) flexible for future LLM features.
    - Design `llm_models` to accommodate new models/providers.
    - Allow schema evolution (e.g., adding fields to `ingredients` for new nutrients).

---

### Summary of Modules

| **Module** | **Key Features** | **Dependencies** | **Timeline** |
| --- | --- | --- | --- |
| User Management | Signup, login, profile, health profile | None | Phase 1 (0-3 mo) |
| Conversational AI | AI chat, LLM integration, token/cost tracking, dynamic widgets | User Management | Phase 1-2 (0-6 mo) |
| Food Diary | Intake logging, timeline, nutritional trends | User Management, Conversational AI | Phase 2 (4-6 mo) |
| Recipe Management | Ingredient detection, recipe suggestions, dish/menu management | User Management, Conversational AI | Phase 2-3 (4-9 mo) |
| Community | Posts, comments, streaks, social feed | User Management, Recipe Management | Phase 3 (7-9 mo) |
| Fitness Planning | Fitness goals, meal planning, progress tracking, AI suggestions | User Management, Recipe Management, Conv. AI | Phase 3 (7-9 mo) |

This modular structure enables parallel development, aligns with the project’s 12-month timeline, and supports the technical stack and schema. Each module is independent enough to be developed by separate teams but integrates via well-defined APIs and shared database tables.

If you need further details, such as specific API endpoints, sample code for a module, or a more granular task breakdown for a specific module, please let me know!