"""
Ad Platform MVP - API Dependencies
Directly calls Supabase Auth API (Raw HTTP) to validate tokens.
"""

import httpx
from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase.client import Client

from app.core.config import settings
from app.core.supabase import get_supabase_service

# Security scheme
security = HTTPBearer(auto_error=False)


# --- 1. SUPABASE CLIENT ---
async def get_supabase() -> Client:
    """Get Supabase service instance for DB queries."""
    return get_supabase_service()


# --- 2. AUTHENTICATION (RAW HTTP) ---
async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
) -> dict:
    """
    Validate token by calling Supabase Auth API directly.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    
    # Supabase Auth URL'i (Config'den küçük harfle okuyoruz)
    auth_url = f"{settings.supabase_url}/auth/v1/user"

    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": settings.supabase_service_role_key, # Küçük harf
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(auth_url, headers=headers)
            
            if response.status_code != 200:
                print(f"Auth Failed: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                )
            
            user_data = response.json()
            # User objesini güvenli şekilde al
            user = user_data if "id" in user_data else user_data.get("user")
            
            if not user:
                 raise Exception("User object parsing failed")

            return {
                "id": user.get("id"),
                "email": user.get("email"),
                "role": user.get("role", "authenticated"),
                # MVP için Org ID fallback
                "org_id": user.get("user_metadata", {}).get("org_id", "11111111-1111-1111-1111-111111111111")
            }

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"CRITICAL AUTH ERROR: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed due to system error",
        )


# --- 3. HELPER DEPENDENCIES ---

async def get_current_user_id(
    current_user: Annotated[dict, Depends(get_current_user)]
) -> str:
    return current_user["id"]


async def get_org_id(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> str:
    return current_user["org_id"]


async def require_admin(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    # MVP: Rol kontrolü eklenebilir
    return current_user


# --- 4. EXPORTS (DİĞER DOSYALAR BUNLARI ARIYOR) ---
CurrentUser = Annotated[dict, Depends(get_current_user)]
CurrentUserId = Annotated[str, Depends(get_current_user_id)]
CurrentOrgId = Annotated[str, Depends(get_org_id)]
AdminUser = Annotated[dict, Depends(require_admin)]
Supabase = Annotated[Client, Depends(get_supabase)]