"""
Async Health History Service.

This module provides async services for managing user health history records.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_history import HealthHistory
from app.schemas.health_history import HealthHistoryResponse


class AsyncHealthHistoryService:
    """Service for async health history operations."""
    
    @staticmethod
    async def get_user_health_history_async(
        db: AsyncSession, user_id: int
    ) -> List[HealthHistoryResponse]:
        """
        Get health history records for a specific user.
        
        Args:
            db: Async database session
            user_id: User ID to get history for
            
        Returns:
            List of health history records
        """
        result = await db.execute(
            select(HealthHistory)
            .where(HealthHistory.user_id == user_id)
            .order_by(HealthHistory.created_at.desc())
        )
        
        history_records = result.scalars().all()
        return [HealthHistoryResponse.from_orm(record) for record in history_records]
    
    @staticmethod
    async def get_health_history_by_id_async(
        db: AsyncSession, history_id: int
    ) -> Optional[HealthHistoryResponse]:
        """
        Get a specific health history record by ID.
        
        Args:
            db: Async database session
            history_id: ID of the health history record
            
        Returns:
            Health history record if found, None otherwise
        """
        result = await db.execute(
            select(HealthHistory)
            .where(HealthHistory.id == history_id)
        )
        
        history_record = result.scalar_one_or_none()
        if history_record:
            return HealthHistoryResponse.from_orm(history_record)
        return None