from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from fastapi import HTTPException, status
import math

from app.models.test import Test
from app.schemas.test import * 
# from app.utils.search import SearchUtils
# from app.utils.logger import test_logger


class TestService:
    @staticmethod
    def create_test(db: Session, test_data: TestCreate, current_user_id: int) -> TestResponse:
        """Create a new test."""
        # Create test with user as creator
        db_test = Test(
            **test_data.model_dump(),
            # created_by_user_id=current_user_id
        )
        
        db.add(db_test)
        db.commit()
        db.refresh(db_test)
        
        return TestResponse.model_validate(db_test)

    @staticmethod
    def get_test_by_id(db: Session, test_id: int) -> Optional[TestResponse]:
        """Get a test by its ID."""
        test = db.query(Test).filter(Test.id == test_id).first()
        if not test:
            return None
        
        return TestResponse.model_validate(test)

    @staticmethod
    def get_tests(
        db: Session, 
        search: Optional[str] = None,
        page: int = 1, 
        page_size: int = 20
    ) -> TestListResponse:
        """Get tests with optional search and filtering."""
        # # If there's a search term, use the new fuzzy search
        # if search and search.strip():
        #     return TestService._fuzzy_search_tests(
        #         db=db,
        #         search_term=search,
        #         page=page,
        #         page_size=page_size
        #     )
        
        # Otherwise, use the original filtering logic
        query = db.query(Test)
        
        # Apply cuisine filter
        if search:
            query = query.filter(Test.name.ilike(f"%{search}%"))
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        tests = query.offset(offset).limit(page_size).all()
        
        # Calculate total pages
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        
        # Convert to response format
        test_items = [TestListItem.model_validate(test) for test in tests]
        
        return TestListResponse(
            tests=test_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    @staticmethod
    def filter_tests(
        db: Session,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> TestListResponse:
        """Filter tests with comprehensive search."""
        return TestService.get_tests(db=db, search=search, page=page, page_size=page_size)
    
    @staticmethod
    def update_test(
        db: Session, 
        test_id: int, 
        test_update: TestUpdate, 
        current_user_id: int
    ) -> Optional[TestResponse]:
        """Update an existing dish."""
        test = db.query(Test).filter(Test.id == test_id).first()
        
        if not test:
            return None
        
        update_data = test_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(test, field, value)
        
        db.commit()
        db.refresh(test)
        
        return TestResponse.model_validate(test)
    
    @staticmethod
    def delete_test(db: Session, test_id: int, current_user_id: int) -> bool:
        """Delete a dish."""
        test = db.query(Test).filter(Test.id == test_id).first()
        
        if not test:
            return False
            
        # # Check if user owns this dish
        # if dish.created_by_user_id != current_user_id:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Not authorized to delete this dish"
        #     )
        
        db.delete(test)
        db.commit()
        
        return True