from fastapi import APIRouter

# Import routers from different API modules
from app.api.endpoints import health, auth, chat, diary, dishes, community, fitness
# from app.api.endpoints import users, items, etc.

api_router = APIRouter()

# Include all API routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(diary.router, prefix="/diary", tags=["diary"])
api_router.include_router(dishes.router, prefix="/dishes", tags=["dishes"])
api_router.include_router(community.router, prefix="/community", tags=["community"])
api_router.include_router(fitness.router, prefix="/fitness", tags=["fitness"])
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(items.router, prefix="/items", tags=["items"])
# Add additional routers as needed 