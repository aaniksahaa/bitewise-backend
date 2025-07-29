from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload

from app.models.post import Post
from app.models.comment import Comment
from app.models.user import User
from app.models.dish import Dish


class AsyncCommunityService:
    """Async service for community-related operations."""

    @staticmethod
    async def create_post(
        db: AsyncSession,
        user_id: int,
        title: str,
        content: str,
        dish_id: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> Post:
        """Create a new community post."""
        post = Post(
            user_id=user_id,
            title=title,
            content=content,
            dish_id=dish_id,
            tags=tags or [],
            created_at=datetime.utcnow()
        )
        
        db.add(post)
        await db.commit()
        await db.refresh(post)
        return post

    @staticmethod
    async def get_community_feed(
        db: AsyncSession,
        limit: int = 20,
        offset: int = 0,
        tags: Optional[List[str]] = None
    ) -> tuple[List[Post], int]:
        """Get community feed with posts."""
        # Build base query
        query = select(Post).options(
            selectinload(Post.user),
            selectinload(Post.dish)
        )
        
        # Filter by tags if provided
        if tags:
            # This would need proper tag filtering logic based on your Post model
            # For now, we'll skip tag filtering
            pass
        
        # Get total count
        count_query = select(func.count(Post.id))
        if tags:
            # Apply same tag filtering to count query
            pass
        
        count_result = await db.execute(count_query)
        total_count = count_result.scalar() or 0
        
        # Get posts with pagination
        query = query.order_by(desc(Post.created_at)).offset(offset).limit(limit)
        result = await db.execute(query)
        posts = result.scalars().all()
        
        return posts, total_count

    @staticmethod
    async def get_post_by_id(db: AsyncSession, post_id: int) -> Optional[Post]:
        """Get a specific post by ID."""
        result = await db.execute(
            select(Post)
            .options(
                selectinload(Post.user),
                selectinload(Post.dish),
                selectinload(Post.comments).selectinload(Comment.user)
            )
            .where(Post.id == post_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_post(
        db: AsyncSession,
        post_id: int,
        user_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[Post]:
        """Update a post (only by the owner)."""
        result = await db.execute(
            select(Post).where(and_(Post.id == post_id, Post.user_id == user_id))
        )
        post = result.scalar_one_or_none()
        
        if not post:
            return None
        
        if title is not None:
            post.title = title
        if content is not None:
            post.content = content
        if tags is not None:
            post.tags = tags
        
        post.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(post)
        return post

    @staticmethod
    async def delete_post(db: AsyncSession, post_id: int, user_id: int) -> bool:
        """Delete a post (only by the owner)."""
        result = await db.execute(
            select(Post).where(and_(Post.id == post_id, Post.user_id == user_id))
        )
        post = result.scalar_one_or_none()
        
        if not post:
            return False
        
        await db.delete(post)
        await db.commit()
        return True

    @staticmethod
    async def create_comment(
        db: AsyncSession,
        post_id: int,
        user_id: int,
        content: str
    ) -> Optional[Comment]:
        """Create a comment on a post."""
        # First check if post exists
        post_result = await db.execute(select(Post).where(Post.id == post_id))
        post = post_result.scalar_one_or_none()
        
        if not post:
            return None
        
        comment = Comment(
            post_id=post_id,
            user_id=user_id,
            content=content,
            created_at=datetime.utcnow()
        )
        
        db.add(comment)
        await db.commit()
        await db.refresh(comment)
        return comment

    @staticmethod
    async def get_post_comments(
        db: AsyncSession,
        post_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Comment]:
        """Get comments for a specific post."""
        result = await db.execute(
            select(Comment)
            .options(selectinload(Comment.user))
            .where(Comment.post_id == post_id)
            .order_by(Comment.created_at)
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def get_user_posts(
        db: AsyncSession,
        user_id: int,
        limit: int = 20,
        offset: int = 0
    ) -> tuple[List[Post], int]:
        """Get posts by a specific user."""
        # Get total count
        count_result = await db.execute(
            select(func.count(Post.id)).where(Post.user_id == user_id)
        )
        total_count = count_result.scalar() or 0
        
        # Get posts
        result = await db.execute(
            select(Post)
            .options(
                selectinload(Post.user),
                selectinload(Post.dish)
            )
            .where(Post.user_id == user_id)
            .order_by(desc(Post.created_at))
            .offset(offset)
            .limit(limit)
        )
        posts = result.scalars().all()
        
        return posts, total_count

    @staticmethod
    async def update_user_streak(
        db: AsyncSession,
        user_id: int,
        streak_type: str,
        increment: bool = True
    ) -> dict:
        """Update user's streak (simplified implementation)."""
        # This is a simplified implementation
        # In a real app, you'd have a proper streaks table and logic
        
        # For now, return a mock response
        current_count = 5 if increment else 0
        
        return {
            "streak_id": 1,
            "user_id": user_id,
            "streak_type": streak_type,
            "current_count": current_count,
            "last_updated": datetime.utcnow()
        }

    @staticmethod
    async def get_user_streaks(db: AsyncSession, user_id: int) -> List[dict]:
        """Get all streaks for a user (simplified implementation)."""
        # This is a simplified implementation
        # In a real app, you'd query a proper streaks table
        
        return [
            {
                "streak_id": 1,
                "user_id": user_id,
                "streak_type": "daily_logging",
                "current_count": 7,
                "last_updated": datetime.utcnow()
            },
            {
                "streak_id": 2,
                "user_id": user_id,
                "streak_type": "healthy_choices",
                "current_count": 3,
                "last_updated": datetime.utcnow()
            }
        ]