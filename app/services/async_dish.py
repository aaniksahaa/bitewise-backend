from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_, and_, select
from fastapi import HTTPException, status
import math

from app.models.dish import Dish
from app.models.dish_ingredient import DishIngredient
from app.schemas.dish import DishCreate, DishUpdate, DishResponse, DishListItem, DishListResponse, DishCreateWithIngredients
from app.utils.logger import dish_logger


class AsyncDishService:
    """
    Async dish service providing dish management operations using async database connections.
    
    This service handles all dish-related operations including creation, retrieval,
    updating, deletion, and search functionality with async/await patterns.
    """

    @staticmethod
    async def create_dish(db: AsyncSession, dish_data: DishCreate, current_user_id: int) -> DishResponse:
        """Create a new dish asynchronously."""
        # Create dish with user as creator
        db_dish = Dish(
            **dish_data.model_dump(),
            created_by_user_id=current_user_id
        )
        
        db.add(db_dish)
        await db.commit()
        await db.refresh(db_dish)
        
        return DishResponse.model_validate(db_dish)

    @staticmethod
    async def create_dish_with_ingredients(
        db: AsyncSession, 
        dish_data: DishCreateWithIngredients, 
        current_user_id: int
    ) -> DishResponse:
        """Create a new dish with ingredients asynchronously."""
        try:
            # Extract ingredients data before creating dish
            ingredients_data = dish_data.ingredients or []
            
            # Remove ingredients from dish data to avoid issues with model creation
            dish_dict = dish_data.model_dump(exclude={'ingredients'})
            
            # Create dish with user as creator
            db_dish = Dish(
                **dish_dict,
                created_by_user_id=current_user_id
            )
            
            db.add(db_dish)
            await db.commit()
            await db.refresh(db_dish)
            
            # Create dish-ingredient relationships if ingredients are provided
            if ingredients_data:
                for ingredient_data in ingredients_data:
                    dish_ingredient = DishIngredient(
                        dish_id=db_dish.id,
                        ingredient_id=ingredient_data.ingredient_id,
                        quantity=ingredient_data.quantity
                    )
                    db.add(dish_ingredient)
                
                await db.commit()
            
            dish_logger.success(
                f"Created dish with {len(ingredients_data)} ingredients", 
                "CREATE",
                dish_id=db_dish.id,
                dish_name=db_dish.name,
                user_id=current_user_id
            )
            
            return DishResponse.model_validate(db_dish)
            
        except Exception as e:
            await db.rollback()
            dish_logger.error(f"Failed to create dish with ingredients: {e}", "CREATE")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create dish: {str(e)}"
            )

    @staticmethod
    async def get_dish_by_id(db: AsyncSession, dish_id: int) -> Optional[DishResponse]:
        """Get a dish by its ID asynchronously."""
        stmt = select(Dish).where(Dish.id == dish_id)
        result = await db.execute(stmt)
        dish = result.scalar_one_or_none()
        
        if not dish:
            return None
        
        return DishResponse.model_validate(dish)

    @staticmethod
    async def get_dishes(
        db: AsyncSession, 
        search: Optional[str] = None,
        cuisine: Optional[str] = None,
        created_by_user_id: Optional[int] = None,
        page: int = 1, 
        page_size: int = 20
    ) -> DishListResponse:
        """Get dishes with optional search and filtering asynchronously."""
        # If there's a search term, use the new fuzzy search
        if search and search.strip():
            return await AsyncDishService._fuzzy_search_dishes(
                db=db,
                search_term=search,
                cuisine=cuisine,
                created_by_user_id=created_by_user_id,
                page=page,
                page_size=page_size
            )
        
        # Otherwise, use the original filtering logic
        stmt = select(Dish)
        
        # Filter out dishes without images
        stmt = stmt.where(
            and_(
                Dish.image_urls.is_not(None),
                func.array_length(Dish.image_urls, 1) > 0
            )
        )
        
        # Apply cuisine filter
        if cuisine:
            stmt = stmt.where(Dish.cuisine.ilike(f"%{cuisine}%"))
            
        # Apply creator filter
        if created_by_user_id:
            stmt = stmt.where(Dish.created_by_user_id == created_by_user_id)
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        paginated_stmt = stmt.offset(offset).limit(page_size)
        result = await db.execute(paginated_stmt)
        dishes = result.scalars().all()
        
        # Calculate total pages
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        
        # Convert to response format
        dish_items = [DishListItem.model_validate(dish) for dish in dishes]
        
        return DishListResponse(
            dishes=dish_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    @staticmethod
    async def _fuzzy_search_dishes(
        db: AsyncSession,
        search_term: str,
        cuisine: Optional[str] = None,
        created_by_user_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> DishListResponse:
        """Internal method for fuzzy search with additional filters asynchronously."""
        # Get scored results from enhanced search
        scored_dishes, total_before_filters = await AsyncDishService._async_search_dishes_with_scoring(
            db=db,
            search_term=search_term,
            page=1,  # Get all results first for filtering
            page_size=1000,  # Large number to get all results
            min_score_threshold=0.1  # Low threshold for inclusive results
        )
        
        # Apply additional filters if specified
        if cuisine or created_by_user_id:
            filtered_dishes = []
            for dish, score in scored_dishes:
                # Apply cuisine filter
                if cuisine and not (dish.cuisine and cuisine.lower() in dish.cuisine.lower()):
                    continue
                
                # Apply creator filter
                if created_by_user_id and dish.created_by_user_id != created_by_user_id:
                    continue
                
                filtered_dishes.append((dish, score))
            
            scored_dishes = filtered_dishes
        
        # Apply pagination to filtered results
        total_count = len(scored_dishes)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_dishes = scored_dishes[start_idx:end_idx]
        
        # Calculate total pages
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        
        # Convert to response format (ignoring scores in final response)
        dish_items = [DishListItem.model_validate(dish) for dish, score in paginated_dishes]
        
        return DishListResponse(
            dishes=dish_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    @staticmethod
    def _generate_spelling_variations(search_term: str) -> List[str]:
        """
        Generate common spelling variations to improve typo tolerance.
        
        Args:
            search_term: The original search term
            
        Returns:
            List of spelling variations including the original term
        """
        variations = [search_term]
        words = search_term.split()
        
        # Common spelling corrections for food-related terms
        spelling_corrections = {
            'piza': 'pizza',
            'pizzza': 'pizza', 
            'chiken': 'chicken',
            'chikken': 'chicken',
            'chickn': 'chicken',
            'burrito': 'burrito',  # Keep original
            'burito': 'burrito',
            'burrito': 'burrito',
            'pasta': 'pasta',  # Keep original
            'psta': 'pasta',
            'spagetti': 'spaghetti',
            'spagheti': 'spaghetti',
            'spghetti': 'spaghetti',
            'salad': 'salad',  # Keep original
            'salade': 'salad',
            'curry': 'curry',  # Keep original
            'currie': 'curry',
            'curie': 'curry',
            'rice': 'rice',  # Keep original
            'ric': 'rice',
            'ryce': 'rice',
            'salmon': 'salmon',  # Keep original
            'salomon': 'salmon',
            'salmn': 'salmon',
            'beef': 'beef',  # Keep original  
            'beaf': 'beef',
            'pork': 'pork',  # Keep original
            'porc': 'pork',
            'vegetable': 'vegetable',  # Keep original
            'vegetabel': 'vegetable',
            'vegatable': 'vegetable',
            'vegtable': 'vegetable',
        }
        
        # Generate variations with corrected spellings
        corrected_words = []
        has_corrections = False
        
        for word in words:
            word_lower = word.lower()
            if word_lower in spelling_corrections:
                corrected_words.append(spelling_corrections[word_lower])
                has_corrections = True
            else:
                corrected_words.append(word)
        
        if has_corrections:
            corrected_term = ' '.join(corrected_words)
            if corrected_term not in variations:
                variations.append(corrected_term)
        
        return variations

    @staticmethod
    async def _async_search_dishes_with_scoring(
        db: AsyncSession,
        search_term: str,
        page: int = 1,
        page_size: int = 20,
        min_score_threshold: float = 0.1
    ) -> Tuple[List[Tuple[Dish, float]], int]:
        """
        Enhanced async dish search with robust text matching and scoring.
        
        Uses PostgreSQL's full-text search capabilities for:
        - Multi-word queries (e.g., "pepperoni pizza")
        - Partial word matching
        - Better relevance scoring
        - Some typo tolerance through similarity matching and spelling corrections
        """
        # Generate spelling variations to improve typo tolerance
        search_variations = AsyncDishService._generate_spelling_variations(search_term)
        
        all_scored_dishes = []
        processed_dish_ids = set()
        
        # Search with each variation
        for variation in search_variations:
            # Clean and prepare search term
            variation_clean = variation.strip().lower()
            search_words = variation_clean.split()
            
            # Build the main query
            stmt = select(Dish).where(
                and_(
                    Dish.image_urls.is_not(None),
                    func.array_length(Dish.image_urls, 1) > 0
                )
            )
            
            # Create multiple search strategies and combine results
            search_filters = []
            
            # Strategy 1: Full-text search using PostgreSQL's tsvector
            # This handles multi-word queries well
            fts_condition = or_(
                func.to_tsvector('english', func.coalesce(Dish.name, '')).op('@@')(
                    func.plainto_tsquery('english', variation_clean)
                ),
                func.to_tsvector('english', func.coalesce(Dish.description, '')).op('@@')(
                    func.plainto_tsquery('english', variation_clean)
                ),
                func.to_tsvector('english', func.coalesce(Dish.cuisine, '')).op('@@')(
                    func.plainto_tsquery('english', variation_clean)
                )
            )
            search_filters.append(fts_condition)
            
            # Strategy 2: Partial word matching for each word in the search term
            for word in search_words:
                if len(word) >= 2:  # Only search for words with 2+ characters
                    word_condition = or_(
                        Dish.name.ilike(f"%{word}%"),
                        Dish.description.ilike(f"%{word}%"),
                        Dish.cuisine.ilike(f"%{word}%")
                    )
                    search_filters.append(word_condition)
            
            # Strategy 3: Exact phrase matching
            phrase_condition = or_(
                Dish.name.ilike(f"%{variation_clean}%"),
                Dish.description.ilike(f"%{variation_clean}%"),
                Dish.cuisine.ilike(f"%{variation_clean}%")
            )
            search_filters.append(phrase_condition)
            
            # Combine all search strategies
            if search_filters:
                combined_filter = or_(*search_filters)
                stmt = stmt.where(combined_filter)
                
                # Execute the search query
                result = await db.execute(stmt)
                dishes = result.scalars().all()
                
                # Enhanced scoring algorithm
                for dish in dishes:
                    if dish.id not in processed_dish_ids:
                        score = await AsyncDishService._calculate_search_score(dish, variation_clean, search_words)
                        
                        # Boost score if this came from a spelling correction
                        if variation != search_term:
                            score *= 0.95  # Slight penalty for corrected terms
                        
                        if score >= min_score_threshold:
                            all_scored_dishes.append((dish, score))
                            processed_dish_ids.add(dish.id)
        
        # Sort by score descending
        all_scored_dishes.sort(key=lambda x: x[1], reverse=True)
        
        # Get total count before pagination
        total_count = len(all_scored_dishes)
        
        # Apply pagination to scored results
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_dishes = all_scored_dishes[start_idx:end_idx]
        
        return paginated_dishes, total_count

    @staticmethod
    async def _calculate_search_score(dish: Dish, search_term: str, search_words: List[str]) -> float:
        """
        Calculate relevance score for a dish based on search term.
        Higher score means more relevant.
        """
        score = 0.0
        dish_name = (dish.name or "").lower()
        dish_description = (dish.description or "").lower()
        dish_cuisine = (dish.cuisine or "").lower()
        search_term_lower = search_term.lower()
        
        # Exact phrase match (highest priority)
        if search_term_lower == dish_name:
            score += 100.0
        elif search_term_lower in dish_name:
            score += 50.0
        elif search_term_lower in dish_description:
            score += 25.0
        elif search_term_lower in dish_cuisine:
            score += 30.0
        
        # Individual word matches
        for word in search_words:
            word_lower = word.lower()
            if len(word_lower) >= 2:
                # Name matches (high priority)
                if word_lower == dish_name:
                    score += 40.0
                elif dish_name.startswith(word_lower):
                    score += 30.0
                elif dish_name.endswith(word_lower):
                    score += 25.0
                elif word_lower in dish_name:
                    score += 20.0
                
                # Description matches (medium priority)
                if word_lower in dish_description:
                    score += 10.0
                
                # Cuisine matches (medium-high priority)
                if word_lower in dish_cuisine:
                    score += 15.0
        
        # Bonus for dishes with all search words present
        if len(search_words) > 1:
            words_found = sum(1 for word in search_words 
                            if word.lower() in dish_name or 
                               word.lower() in dish_description or 
                               word.lower() in dish_cuisine)
            if words_found == len(search_words):
                score += 20.0
            elif words_found >= len(search_words) * 0.7:  # 70% of words found
                score += 10.0
        
        # Length penalty for very long names (prefer more specific matches)
        if dish.name:
            name_length = len(dish.name)
            if name_length > 50:
                score *= 0.9
            elif name_length > 100:
                score *= 0.8
        
        # Bonus for dishes with complete nutritional information
        if dish.calories and dish.protein_g and dish.carbs_g and dish.fats_g:
            score += 2.0
        
        return score

    @staticmethod
    async def search_dishes_by_name(
        db: AsyncSession,
        search_term: str,
        page: int = 1,
        page_size: int = 20
    ) -> DishListResponse:
        """Enhanced search dishes by name with robust text matching."""
        
        dish_logger.debug(f"🔍 Enhanced async searching dishes: '{search_term}'", "SEARCH", 
                         page=page, page_size=page_size)
        
        # Use the enhanced scoring search method
        scored_dishes, total_count = await AsyncDishService._async_search_dishes_with_scoring(
            db=db,
            search_term=search_term,
            page=page,
            page_size=page_size,
            min_score_threshold=0.1  # Very low threshold to be inclusive
        )
        
        # Calculate total pages
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        
        # Convert to list items (ignoring scores in final response)
        dish_items = [
            DishListItem(
                id=dish.id,
                name=dish.name,
                description=dish.description,
                cuisine=dish.cuisine,
                calories=dish.calories,
                protein_g=dish.protein_g,
                created_at=dish.created_at,
                image_urls=dish.image_urls,
                prep_time_minutes=dish.prep_time_minutes,
                cook_time_minutes=dish.cook_time_minutes,
                servings=dish.servings,
                created_by_user_id=dish.created_by_user_id,
                carbs_g=dish.carbs_g,
                fats_g=dish.fats_g
            )
            for dish, score in scored_dishes
        ]
        
        dish_logger.success(f"Found {len(scored_dishes)} dishes with enhanced search", "SEARCH",
                          search_term=search_term, returned_count=len(dish_items), total_count=total_count)
        
        if dish_items and len(dish_items) <= 3:
            # Log the names and scores of found dishes for debugging
            dish_names_scores = [(dish.name, score) for dish, score in scored_dishes[:3]]
            dish_logger.debug(f"Top results: {dish_names_scores}", "SEARCH")
        
        return DishListResponse(
            dishes=dish_items,
            total_count=len(scored_dishes),  # Use actual filtered count
            page=page,
            page_size=page_size,
            total_pages=math.ceil(len(scored_dishes) / page_size) if scored_dishes else 1
        )

    @staticmethod
    async def update_dish(
        db: AsyncSession, 
        dish_id: int, 
        dish_update: DishUpdate, 
        current_user_id: int
    ) -> Optional[DishResponse]:
        """Update an existing dish asynchronously."""
        stmt = select(Dish).where(Dish.id == dish_id)
        result = await db.execute(stmt)
        dish = result.scalar_one_or_none()
        
        if not dish:
            return None
            
        # Check if user owns this dish or is admin (for now just check ownership)
        if dish.created_by_user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this dish"
            )
        
        # Update only provided fields
        update_data = dish_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(dish, field, value)
        
        await db.commit()
        await db.refresh(dish)
        
        return DishResponse.model_validate(dish)

    @staticmethod
    async def delete_dish(db: AsyncSession, dish_id: int, current_user_id: int) -> bool:
        """Delete a dish asynchronously."""
        stmt = select(Dish).where(Dish.id == dish_id)
        result = await db.execute(stmt)
        dish = result.scalar_one_or_none()
        
        if not dish:
            return False
            
        # Check if user owns this dish
        if dish.created_by_user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this dish"
            )
        
        await db.delete(dish)
        await db.commit()
        
        return True

    @staticmethod
    async def get_user_dishes(
        db: AsyncSession, 
        user_id: int, 
        page: int = 1, 
        page_size: int = 20
    ) -> DishListResponse:
        """Get all dishes created by a specific user asynchronously."""
        return await AsyncDishService.get_dishes(
            db=db,
            created_by_user_id=user_id,
            page=page,
            page_size=page_size
        )

    @staticmethod
    async def get_dishes_by_cuisine(
        db: AsyncSession, 
        cuisine: str, 
        page: int = 1, 
        page_size: int = 20
    ) -> DishListResponse:
        """Get dishes filtered by cuisine asynchronously."""
        return await AsyncDishService.get_dishes(
            db=db,
            cuisine=cuisine,
            page=page,
            page_size=page_size
        )

    @staticmethod
    async def get_dishes_with_ingredients(
        db: AsyncSession,
        dish_ids: List[int]
    ) -> List[Dish]:
        """
        Get dishes with their ingredient relationships loaded asynchronously.
        
        This method demonstrates async relationship handling for dish-ingredient relationships.
        """
        if not dish_ids:
            return []
        
        # Use selectinload or joinedload for async relationship loading
        # For now, we'll use a simple approach without explicit relationship loading
        stmt = select(Dish).where(Dish.id.in_(dish_ids))
        result = await db.execute(stmt)
        dishes = result.scalars().all()
        
        # If we had dish-ingredient relationships defined in the model,
        # we would use something like:
        # stmt = select(Dish).options(selectinload(Dish.ingredients)).where(Dish.id.in_(dish_ids))
        
        return dishes

    @staticmethod
    async def bulk_update_dishes(
        db: AsyncSession,
        dish_updates: List[Tuple[int, DishUpdate]],
        current_user_id: int
    ) -> List[DishResponse]:
        """
        Bulk update multiple dishes asynchronously.
        
        This method demonstrates async bulk operations for better performance
        when updating multiple dishes at once.
        """
        updated_dishes = []
        
        for dish_id, dish_update in dish_updates:
            try:
                updated_dish = await AsyncDishService.update_dish(
                    db=db,
                    dish_id=dish_id,
                    dish_update=dish_update,
                    current_user_id=current_user_id
                )
                if updated_dish:
                    updated_dishes.append(updated_dish)
            except HTTPException:
                # Skip dishes that can't be updated (permission issues, not found, etc.)
                continue
        
        return updated_dishes

    @staticmethod
    async def get_popular_dishes(
        db: AsyncSession,
        limit: int = 10
    ) -> List[DishListItem]:
        """
        Get popular dishes based on some criteria (placeholder implementation).
        
        This method demonstrates how to implement complex queries with async patterns.
        In a real implementation, this might consider factors like:
        - Number of times a dish has been logged in intakes
        - User ratings
        - Recent activity
        """
        # For now, just return the most recently created dishes
        stmt = select(Dish).order_by(Dish.created_at.desc()).limit(limit)
        result = await db.execute(stmt)
        dishes = result.scalars().all()
        
        return [DishListItem.model_validate(dish) for dish in dishes]

    @staticmethod
    async def search_dishes_by_nutrition(
        db: AsyncSession,
        min_protein: Optional[float] = None,
        max_calories: Optional[float] = None,
        min_fiber: Optional[float] = None,
        page: int = 1,
        page_size: int = 20
    ) -> DishListResponse:
        """
        Search dishes by nutritional criteria asynchronously.
        
        This method demonstrates complex filtering with async patterns.
        """
        stmt = select(Dish)
        
        # Apply nutritional filters
        if min_protein is not None:
            stmt = stmt.where(Dish.protein_g >= min_protein)
        
        if max_calories is not None:
            stmt = stmt.where(Dish.calories <= max_calories)
        
        if min_fiber is not None:
            stmt = stmt.where(Dish.fiber_g >= min_fiber)
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        paginated_stmt = stmt.offset(offset).limit(page_size)
        result = await db.execute(paginated_stmt)
        dishes = result.scalars().all()
        
        # Calculate total pages
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        
        # Convert to response format
        dish_items = [DishListItem.model_validate(dish) for dish in dishes]
        
        return DishListResponse(
            dishes=dish_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )