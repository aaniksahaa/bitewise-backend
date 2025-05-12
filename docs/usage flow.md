# Usage Flow

## Expected Usage Flow

- User signs up
    - While signing up, he enters name, gender, date of birth, location(maybe city, country or direct google location), height, current weight, we may also support signup with google, github etc
- User logs in
- In profile, user can update these infos anytime, especially changing height and weight should be very handy since they may change often
- The user will also have the options to add medical issues, dietary preferences/restrictions
- User will have a food diary,(like that in MyFitnessPal), much like Google Calender, which will log everything against time and day
- Since we will mainly work on food and nutrition, a coherent correct structure of such information storage is necessary. I am thinking of this, There will be ingredients, that are basically small unit ingredients, like Egg, Sugar, Salt, Rice, Atta, and they will be associated nutrition amounts or calories per unit(this unit may actually vary… like for Egg it will be like one egg, but for a fish say hilsha fish, or lentil, say we need per 100g), Okay, so ingredient is this low level thing, then a Dish will have some ingredients and their amounts, o like how many units, and a recipe, and one or more pictures may also be helpful, so yeah, Ingredient and Dish
- And as you see, multiple dishes constitute a Menu, a Menu may also have an occasion or context, like Birthday… Users may create and store menu,
- In Chat interface, user may give message, the message may contain text and image(s)
- A social community  feature like for sharing thoughts, recipes…
- User will have a Food Diary that will kinda be auto updated based on chat with the agent but also will have option for manual input of like, dish or water. So, we may have a Intake object, that will have a user, time, Dish, and multiple such intakes form a Food Diary of a User
- user edit or admin, search then if not
- Then we process message with an Agentic system, Like
    - If user says, I ate 1 pizza and 2 burgers today, of is he ups the picture of such a lunch, of if he shares a recipe of what he ate… the agent will log that in backend, and the food diary gets updated as such and the chat also gives a response containing the nutrition info, etc and feedbacks… while prompting we will always keep the agent aware of the user’s health condition and medical issues, dietary preferences/restrictions
    - Note that, in case of Food, we need to be biologically and chemically accurate like tracking the exact elements of food like carbs, fat, protein, vitamins, water etc
    - The user may also ask for typical health related calculations in the chat, which is very common, like say he asks, what is my BMI, what is my BMR, or what weight I need to achieve a healthy BMI, but see, the user may also want to know that for a family member of him/her, right? conventionally he would need to search for such web app, but i plan here we will embed a dynamically built *widget type inside the chat response, that will have like input for weight, height as needed, and will show the BMR/BMI etc as directed by user, this will be a tricky, especially how to fit it into a software class structure, that is extendable*
    - Also, the user may want to set a fitness goal, like I want to lose 6 kgs in the next 2 weeks, in that case, the agent will generate a FitnessPlan, maybe on a day to day basis,(like MyFitnessPal does), and it will be stored, and the user’s intakes will be tracked and compared against that fitness plan continously, and this progress will be shown somewhere in a visually appealing way, liek day by day etc
    - The Agent can also suggest recipes based on like what I have currently in grocery and what time is it etc.. So we will need to have a collection of recipes too maybe,
    - We may also keep a multimodal RAG on text and image, that will like store recipes/dishes, and will be able to retrieve relevant things, maybe this will be tool for the agent
    - Users may also upload like I cooked this, with a picture and a recipe, we may then, add it to our community recipes database… and users may explore what others are cooking as well as the pre saved recipes of dishes…, this will be shared as a Post and others may comment, just like a social media
    - User may also say I have a birthday party with 5 friends at home, plan me a Menu and then it will be saved.
- We also want to have a streak feature
- Note that the Agentic system will need a lot of curated prompts, we wish to write this prompt codebase in a organized efficient extandable way following LLM industry standards
- different LLMs may needed to be called for response and embedding generation, so there will be a LLMClient class
- Also, we need to track token usage and cost incurred for the LLM conversations for the users… so maybe LLMClient will return these in response, like when it is given a query, it gives the response text and also tokens, cost, model name, provider etc… which will be stored with that message maybe, well then the user’s cost may also be calculated by suming the costs in messages right?