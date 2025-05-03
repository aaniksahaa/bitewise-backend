from fastapi import APIRouter

# Import routers from different API modules
from app.api.endpoints import health
# from app.api.endpoints import users, items, etc.

api_router = APIRouter()

# Include all API routers
api_router.include_router(health.router, tags=["health"])
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(items.router, prefix="/items", tags=["items"])
# Add additional routers as needed 