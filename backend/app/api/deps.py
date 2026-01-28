"""
Ad Platform MVP - API Dependencies

FastAPI dependency injection functions.
"""

from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.security import verify_token
from app.core.supabase import get_supabase_service, SupabaseService


# Security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials],
        Depends(security)
    ],
) -> str:
    """
    Extract and validate user ID from JWT token.
    
    Raises:
        HTTPException: If token is missing or invalid
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = verify_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id


async def get_current_user(
    user_id: Annotated[str, Depends(get_current_user_id)],
    supabase: Annotated[SupabaseService, Depends(get_supabase_service)],
) -> dict:
    """
    Get the full user object from database.
    
    Returns:
        User dict with organization info
        
    Raises:
        HTTPException: If user not found
    """
    user = await supabase.get_user(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Update last seen
    await supabase.update_user_last_seen(user_id)
    
    return user


async def get_org_id(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> str:
    """Get organization ID from current user."""
    return current_user["org_id"]


async def require_admin(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """
    Require user to be org admin or owner.
    
    Raises:
        HTTPException: If user is not admin/owner
    """
    if current_user.get("role") not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def get_supabase() -> SupabaseService:
    """Get Supabase service instance."""
    return get_supabase_service()


# Type aliases for cleaner signatures
CurrentUser = Annotated[dict, Depends(get_current_user)]
CurrentUserId = Annotated[str, Depends(get_current_user_id)]
CurrentOrgId = Annotated[str, Depends(get_org_id)]
AdminUser = Annotated[dict, Depends(require_admin)]
Supabase = Annotated[SupabaseService, Depends(get_supabase)]
