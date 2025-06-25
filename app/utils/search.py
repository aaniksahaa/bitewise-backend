"""
Search utilities for fuzzy matching and scoring of dish names.
"""
import re
from typing import List, Tuple, Dict, Any
from fuzzywuzzy import fuzz, process
from sqlalchemy.orm import Session
from app.models.dish import Dish


class SearchUtils:
    """Utility class for intelligent dish searching with fuzzy matching and scoring."""
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for better matching."""
        if not text:
            return ""
        
        # Convert to lowercase and strip whitespace
        text = text.lower().strip()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    @staticmethod
    def extract_words(text: str) -> List[str]:
        """Extract words from text, filtering out common stop words."""
        if not text:
            return []
        
        # Split by word boundaries and filter out very short words
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Common stop words to filter out
        stop_words = {'a', 'an', 'and', 'the', 'with', 'of', 'in', 'on', 'at', 'by', 'for', 'to'}
        
        # Filter out stop words and very short words
        filtered_words = [word for word in words if len(word) > 2 and word not in stop_words]
        
        return filtered_words
    
    @staticmethod
    def calculate_match_score(search_term: str, dish_name: str, dish_description: str = None, dish_cuisine: str = None) -> float:
        """
        Calculate a comprehensive match score for a dish.
        
        Args:
            search_term: The search query
            dish_name: Name of the dish
            dish_description: Description of the dish (optional)
            dish_cuisine: Cuisine type of the dish (optional)
            
        Returns:
            float: Score between 0-100, higher is better match
        """
        if not search_term or not dish_name:
            return 0.0
        
        # Normalize inputs
        search_norm = SearchUtils.normalize_text(search_term)
        name_norm = SearchUtils.normalize_text(dish_name)
        desc_norm = SearchUtils.normalize_text(dish_description or "")
        cuisine_norm = SearchUtils.normalize_text(dish_cuisine or "")
        
        # Extract words from search term
        search_words = SearchUtils.extract_words(search_norm)
        if not search_words:
            # If no meaningful words, fall back to simple fuzzy matching
            return fuzz.partial_ratio(search_norm, name_norm)
        
        total_score = 0.0
        
        # 1. Exact substring match in name (highest priority) - 60% weight
        if search_norm in name_norm:
            total_score += 60.0
        else:
            # Fuzzy match on full name - weighted by similarity
            name_fuzzy = fuzz.partial_ratio(search_norm, name_norm)
            total_score += (name_fuzzy * 0.6)
        
        # 2. Word-level matching - 25% weight
        word_match_score = 0.0
        name_words = SearchUtils.extract_words(name_norm)
        
        for search_word in search_words:
            best_word_match = 0.0
            for name_word in name_words:
                # Exact word match
                if search_word == name_word:
                    best_word_match = 100.0
                    break
                # Fuzzy word match
                word_fuzzy = fuzz.ratio(search_word, name_word)
                if word_fuzzy > best_word_match:
                    best_word_match = word_fuzzy
            
            word_match_score += best_word_match
        
        # Average word match score
        if len(search_words) > 0:
            word_match_score = word_match_score / len(search_words)
            total_score += (word_match_score * 0.25)
        
        # 3. Description matching - 10% weight
        if desc_norm:
            desc_score = 0.0
            if search_norm in desc_norm:
                desc_score = 80.0
            else:
                desc_score = fuzz.partial_ratio(search_norm, desc_norm)
            total_score += (desc_score * 0.1)
        
        # 4. Cuisine matching - 5% weight
        if cuisine_norm:
            cuisine_score = 0.0
            if search_norm in cuisine_norm:
                cuisine_score = 100.0
            else:
                cuisine_score = fuzz.partial_ratio(search_norm, cuisine_norm)
            total_score += (cuisine_score * 0.05)
        
        return min(total_score, 100.0)  # Cap at 100
    
    @staticmethod
    def search_dishes_with_scoring(
        db: Session, 
        search_term: str, 
        page: int = 1, 
        page_size: int = 20,
        min_score_threshold: float = 10.0  # Minimum score to include in results
    ) -> Tuple[List[Tuple[Dish, float]], int]:
        """
        Search dishes with fuzzy matching and return scored results.
        
        Args:
            db: Database session
            search_term: Search query
            page: Page number for pagination
            page_size: Number of results per page
            min_score_threshold: Minimum score to include in results
            
        Returns:
            Tuple of (list of (dish, score) tuples, total_count)
        """
        if not search_term or not search_term.strip():
            return [], 0
        
        # Get all dishes from database
        all_dishes = db.query(Dish).all()
        
        # Calculate scores for all dishes
        scored_dishes = []
        for dish in all_dishes:
            score = SearchUtils.calculate_match_score(
                search_term=search_term,
                dish_name=dish.name,
                dish_description=dish.description,
                dish_cuisine=dish.cuisine
            )
            
            # Only include dishes above the threshold
            if score >= min_score_threshold:
                scored_dishes.append((dish, score))
        
        # Sort by score in descending order (highest score first)
        scored_dishes.sort(key=lambda x: x[1], reverse=True)
        
        # Apply pagination
        total_count = len(scored_dishes)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        paginated_results = scored_dishes[start_idx:end_idx]
        
        return paginated_results, total_count
    
    @staticmethod
    def find_best_dish_by_name(db: Session, dish_name: str) -> Tuple[Dish, float]:
        """
        Find the best matching dish by name for intake logging.
        
        Args:
            db: Database session
            dish_name: Name to search for
            
        Returns:
            Tuple of (best_dish, score) or (None, 0.0) if no good match found
        """
        if not dish_name or not dish_name.strip():
            return None, 0.0
        
        # Get all dishes and score them
        all_dishes = db.query(Dish).all()
        
        best_dish = None
        best_score = 0.0
        
        for dish in all_dishes:
            score = SearchUtils.calculate_match_score(
                search_term=dish_name,
                dish_name=dish.name,
                dish_description=dish.description,
                dish_cuisine=dish.cuisine
            )
            
            if score > best_score:
                best_score = score
                best_dish = dish
        
        # Return the best match only if score is reasonable (above 30)
        if best_score >= 30.0:
            return best_dish, best_score
        
        return None, 0.0 