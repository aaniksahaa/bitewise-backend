"""
API dependency injection module.

This module provides dependency injection functions for API endpoints,
including database sessions and authentication.

IMPORTANT: This module is maintained for backward compatibility.
New code should use async dependencies directly from their respective modules.
"""

import logging
from typing import Generator, Dict, Any
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.async_session import get_async_db
from app.services.async_auth import AsyncAuthService

logger = logging.getLogger(__name__)

# Re-export the synchronous get_db for backward compatibility
# New code should use get_async_db directly

# Authentication dependencies
async def get_current_user(
    token: str = Depends(AsyncAuthService.oauth2_scheme)
) -> Dict[str, Any]:
    """
    Get the current authenticated user from the token.
    
    Args:
        token: JWT token from the request
        
    Returns:
        Dict containing user information
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        return await AsyncAuthService.get_current_user(token)
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the current active user.
    
    Args:
        current_user: User information from get_current_user
        
    Returns:
        Dict containing user information
        
    Raises:
        HTTPException: If the user is inactive
    """
    if not current_user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user