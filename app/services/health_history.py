from typing import List

from sqlalchemy.orm import Session

from app.models.health_history import HealthHistory
from app.schemas.health_history import HealthHistoryCreate


class HealthHistoryService:
    @staticmethod
    def get_user_health_history(db: Session, user_id: int) -> List[HealthHistory]:
        """Get all health history records for a user."""
        return db.query(HealthHistory).filter(HealthHistory.user_id == user_id).all()

    @staticmethod
    def get_health_history_by_id(db: Session, history_id: int) -> HealthHistory | None:
        """Get a specific health history record by ID."""
        return db.query(HealthHistory).filter(HealthHistory.id == history_id).first()

    @staticmethod
    def create_health_history(
        db: Session, health_history: HealthHistoryCreate, user_id: int
    ) -> HealthHistory:
        """Create a new health history record."""
        db_health_history = HealthHistory(
            user_id=user_id,
            height_cm=health_history.height_cm,
            weight_kg=health_history.weight_kg,
        )
        db.add(db_health_history)
        db.commit()
        db.refresh(db_health_history)
        return db_health_history
