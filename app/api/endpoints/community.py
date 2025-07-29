from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.async_session import get_async_db
from app.services.async_auth import AsyncAuthService, get_current_active_user_async
from app.services.async_community import AsyncCommunityService
from app.models.user import User

router = APIRouter()

# Models
class PostCreate(BaseModel):
    title: str
    content: str
    dish_id: Optional[int] = None
    tags: Optional[List[str]] = None

class PostResponse(BaseModel):
    post_id: int
    title: str
    created_at: datetime

class PostDetailResponse(BaseModel):
    post_id: int
    user_id: int
    username: str
    title: str
    content: str
    dish_id: Optional[int] = None
    dish_name: Optional[str] = None
    tags: Optional[List[str]] = None
    created_at: datetime

class PostListResponse(BaseModel):
    posts: List[PostDetailResponse]
    total_count: int

class StreakUpdate(BaseModel):
    streak_type: str
    increment: bool

class StreakResponse(BaseModel):
    streak_id: int
    streak_type: str
    current_count: int
    last_updated: datetime

@router.post("/posts", response_model=PostResponse)
async def create_post(
    post: PostCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """Create a new community post."""
    created_post = await AsyncCommunityService.create_post(
        db=db,
        user_id=current_user.id,
        title=post.title,
        content=post.content,
        dish_id=post.dish_id,
        tags=post.tags
    )
    
    return PostResponse(
        post_id=created_post.id,
        title=created_post.title,
        created_at=created_post.created_at
    )

@router.get("/posts", response_model=PostListResponse)
async def get_community_feed(
    limit: int = 20,
    offset: int = 0,
    tags: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_async_db)
):
    """Get community feed."""
    posts, total_count = await AsyncCommunityService.get_community_feed(
        db=db,
        limit=limit,
        offset=offset,
        tags=tags
    )
    
    post_responses = []
    for post in posts:
        post_responses.append(PostDetailResponse(
            post_id=post.id,
            user_id=post.user_id,
            username=post.user.username if post.user else "Unknown",
            title=post.title,
            content=post.content,
            dish_id=post.dish_id,
            dish_name=post.dish.name if post.dish else None,
            tags=post.tags or [],
            created_at=post.created_at
        ))
    
    return PostListResponse(
        posts=post_responses,
        total_count=total_count
    )

@router.post("/streaks", response_model=StreakResponse)
async def update_streak(
    streak: StreakUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """Update user's streak."""
    streak_data = await AsyncCommunityService.update_user_streak(
        db=db,
        user_id=current_user.id,
        streak_type=streak.streak_type,
        increment=streak.increment
    )
    
    return StreakResponse(
        streak_id=streak_data["streak_id"],
        streak_type=streak_data["streak_type"],
        current_count=streak_data["current_count"],
        last_updated=streak_data["last_updated"]
    ) 