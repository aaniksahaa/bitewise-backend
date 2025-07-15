from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.services.auth import get_current_active_user
from app.services.test import TestService
from app.schemas.test import TestCreate, TestUpdate, TestResponse, TestListResponse
from app.models.user import User

router = APIRouter()


# Create a function to optionally get current user
async def get_current_user_optional(
    db: Session = Depends(get_db),
    token: Optional[str] = None
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None."""
    if not token:
        return None
    try:
        from app.services.auth import AuthService
        return AuthService.get_current_user(db=db, token=token)
    except:
        return None


@router.post("/", response_model=TestResponse, status_code=status.HTTP_201_CREATED)
async def create_test(
    test_data: TestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new test."""
    return TestService.create_test(
        db=db, 
        test_data=test_data, 
        current_user_id=current_user.id
    )


@router.get("/", response_model=TestListResponse)
async def get_tests(
    search: Optional[str] = Query(None, description="Search term for name, description, or cuisine"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Get tests with optional search and filtering."""
    
    return TestService.get_tests(
        db=db,
        search=search,
        page=page,
        page_size=page_size
    )


@router.put("/{test_id}", response_model=TestResponse)
async def update_test(
    test_id: int,
    test_update: TestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a test."""
    test = TestService.update_test(
        db=db,
        test_id=test_id,
        test_update=test_update,
        current_user_id=current_user.id
    )
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    return test


@router.delete("/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a test."""
    success = TestService.delete_test(
        db=db,
        test_id=test_id,
        current_user_id=current_user.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        ) 