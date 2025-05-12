from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

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
async def create_post(post: PostCreate):
    """Create a new community post."""
    return PostResponse(
        post_id=1,
        title=post.title,
        created_at=datetime.now()
    )

@router.get("/posts", response_model=PostListResponse)
async def get_community_feed(
    limit: int = 20,
    offset: int = 0,
    tags: Optional[List[str]] = None
):
    """Get community feed."""
    return PostListResponse(
        posts=[
            PostDetailResponse(
                post_id=1,
                user_id=1,
                username="Dummy User",
                title="Dummy Post",
                content="This is a dummy post content",
                dish_id=1,
                dish_name="Dummy Dish",
                tags=["dummy", "test"],
                created_at=datetime.now()
            )
        ],
        total_count=1
    )

@router.post("/streaks", response_model=StreakResponse)
async def update_streak(streak: StreakUpdate):
    """Update user's streak."""
    return StreakResponse(
        streak_id=1,
        streak_type=streak.streak_type,
        current_count=5 if streak.increment else 0,
        last_updated=datetime.now()
    ) 