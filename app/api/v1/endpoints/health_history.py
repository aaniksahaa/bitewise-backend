from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.async_session import get_async_db
from app.schemas.health_history import HealthHistoryResponse
from app.services.async_health_history import AsyncHealthHistoryService

router = APIRouter()


@router.get("/{user_id}/history", response_model=List[HealthHistoryResponse])
async def get_user_health_history(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(deps.get_current_user),
) -> List[HealthHistoryResponse]:
    """
    Get health history for a specific user.
    Only the user themselves can access their health history.
    """
    if current_user["id"] != user_id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this user's health history",
        )

    health_history = await AsyncHealthHistoryService.get_user_health_history_async(db, user_id)
    return health_history


@router.get("/history/{history_id}", response_model=HealthHistoryResponse)
async def get_health_history_by_id(
    history_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(deps.get_current_user),
) -> HealthHistoryResponse:
    """
    Get a specific health history record by ID.
    Only the user who owns the record can access it.
    """
    health_history = await AsyncHealthHistoryService.get_health_history_by_id_async(db, history_id)
    if not health_history:
        raise HTTPException(status_code=404, detail="Health history record not found")

    if health_history.user_id != current_user["id"]:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this health history record",
        )

    return health_history
