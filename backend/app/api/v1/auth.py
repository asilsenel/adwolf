"""
Ad Platform MVP - OAuth Authentication Endpoints

OAuth flows for Google Ads and Meta Ads.
"""

import urllib.parse
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
import httpx

from app.core.config import settings
from app.core.security import (
    create_oauth_state_token,
    decode_oauth_state_token,
    encrypt_token,
)
from app.core.supabase import get_supabase_service
from app.models.account import (
    Platform,
    OAuthInitiateRequest,
    OAuthInitiateResponse,
    OAuthCallbackResponse,
    LoginRequest,
    LoginResponse,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


# ===========================================
# USER LOGIN
# ===========================================

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate user with email and password.
    
    Uses Supabase Auth. Returns JWT access token for API authorization.
    Use the returned access_token in the 'Authorize' button in Swagger UI.
    """
    supabase = get_supabase_service()
    
    try:
        # Authenticate with Supabase Auth
        auth_response = supabase.client.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password,
        })
        
        session = auth_response.session
        user = auth_response.user
        
        if not session or not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz email veya şifre",
            )
        
        return LoginResponse(
            access_token=session.access_token,
            token_type="bearer",
            expires_in=session.expires_in or 3600,
            refresh_token=session.refresh_token,
            user={
                "id": user.id,
                "email": user.email,
                "created_at": user.created_at,
            },
        )
        
    except Exception as e:
        error_msg = str(e)
        if "Invalid login credentials" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz email veya şifre",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Giriş başarısız: {error_msg}",
        )


# ===========================================
# GOOGLE ADS OAUTH
# ===========================================

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_ADS_SCOPES = [
    "https://www.googleapis.com/auth/adwords",
    "openid",
    "email",
    "profile",
]


@router.post("/google/initiate", response_model=OAuthInitiateResponse)
async def initiate_google_oauth(
    request: OAuthInitiateRequest,
    user_id: str = Query(..., description="User ID initiating OAuth"),
):
    """
    Initiate Google Ads OAuth flow.
    
    Returns the authorization URL to redirect the user to.
    """
    # Create state token with user context
    state = create_oauth_state_token(
        user_id=user_id,
        platform=Platform.GOOGLE_ADS.value,
        redirect_uri=request.redirect_uri,
    )
    
    # Build authorization URL
    params = {
        "client_id": settings.google_ads_client_id,
        "redirect_uri": settings.google_ads_redirect_uri,
        "response_type": "code",
        "scope": " ".join(GOOGLE_ADS_SCOPES),
        "access_type": "offline",
        "prompt": "consent",  # Force consent to get refresh token
        "state": state,
    }
    
    authorization_url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
    
    return OAuthInitiateResponse(
        authorization_url=authorization_url,
        state=state,
        platform=Platform.GOOGLE_ADS,
    )


@router.get("/google/callback")
async def google_oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    """
    Handle Google OAuth callback.
    
    Exchanges authorization code for tokens and stores the connected account.
    """
    # Check for errors
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error} - {error_description}",
        )
    
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state parameter",
        )
    
    # Verify state token
    state_data = decode_oauth_state_token(state)
    if state_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state token",
        )
    
    user_id = state_data.get("sub")
    redirect_uri = state_data.get("redirect_uri")
    
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.google_ads_client_id,
                "client_secret": settings.google_ads_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.google_ads_redirect_uri,
            },
        )
    
    if token_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to exchange code: {token_response.text}",
        )
    
    tokens = token_response.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in", 3600)
    
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No access token received",
        )
    
    # Get user info from Google
    async with httpx.AsyncClient() as client:
        userinfo_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    
    email = None
    if userinfo_response.status_code == 200:
        userinfo = userinfo_response.json()
        email = userinfo.get("email")
    
    # Get Google Ads customer IDs
    # Note: In production, you'd use google-ads library here
    # For now, we'll create a placeholder account
    
    # Get user's org_id
    supabase = get_supabase_service()
    user = await supabase.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    org_id = user["org_id"]
    
    # Store connected account
    from datetime import datetime, timedelta, timezone
    
    account_data = {
        "org_id": org_id,
        "connected_by": user_id,
        "platform": Platform.GOOGLE_ADS.value,
        "platform_account_id": email or f"google_{user_id[:8]}",  # Temporary
        "platform_account_name": email or "Google Ads Account",
        "access_token_encrypted": encrypt_token(access_token),
        "refresh_token_encrypted": encrypt_token(refresh_token) if refresh_token else None,
        "token_expires_at": (
            datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        ).isoformat(),
        "status": "active",
    }
    
    try:
        account = await supabase.create_connected_account(account_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save account: {str(e)}",
        )
    
    # Redirect or return response
    if redirect_uri:
        return RedirectResponse(
            url=f"{redirect_uri}?success=true&account_id={account['id']}"
        )
    
    return OAuthCallbackResponse(
        success=True,
        account_id=account["id"],
        account_name=account["platform_account_name"],
        platform=Platform.GOOGLE_ADS,
        message="Google Ads hesabı başarıyla bağlandı",
        redirect_uri=redirect_uri,
    )


# ===========================================
# META ADS OAUTH
# ===========================================

META_AUTH_URL = "https://www.facebook.com/v18.0/dialog/oauth"
META_TOKEN_URL = "https://graph.facebook.com/v18.0/oauth/access_token"
META_SCOPES = [
    "ads_management",
    "ads_read",
    "business_management",
    "email",
]


@router.post("/meta/initiate", response_model=OAuthInitiateResponse)
async def initiate_meta_oauth(
    request: OAuthInitiateRequest,
    user_id: str = Query(..., description="User ID initiating OAuth"),
):
    """
    Initiate Meta (Facebook) Ads OAuth flow.
    
    Returns the authorization URL to redirect the user to.
    """
    # Create state token with user context
    state = create_oauth_state_token(
        user_id=user_id,
        platform=Platform.META_ADS.value,
        redirect_uri=request.redirect_uri,
    )
    
    # Build authorization URL
    params = {
        "client_id": settings.meta_app_id,
        "redirect_uri": settings.meta_redirect_uri,
        "response_type": "code",
        "scope": ",".join(META_SCOPES),
        "state": state,
    }
    
    authorization_url = f"{META_AUTH_URL}?{urllib.parse.urlencode(params)}"
    
    return OAuthInitiateResponse(
        authorization_url=authorization_url,
        state=state,
        platform=Platform.META_ADS,
    )


@router.get("/meta/callback")
async def meta_oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    error_reason: Optional[str] = None,
):
    """
    Handle Meta OAuth callback.
    
    Exchanges authorization code for tokens and stores the connected account.
    """
    # Check for errors
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error} - {error_description or error_reason}",
        )
    
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state parameter",
        )
    
    # Verify state token
    state_data = decode_oauth_state_token(state)
    if state_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state token",
        )
    
    user_id = state_data.get("sub")
    redirect_uri = state_data.get("redirect_uri")
    
    # Exchange code for short-lived token
    async with httpx.AsyncClient() as client:
        token_response = await client.get(
            META_TOKEN_URL,
            params={
                "client_id": settings.meta_app_id,
                "client_secret": settings.meta_app_secret,
                "code": code,
                "redirect_uri": settings.meta_redirect_uri,
            },
        )
    
    if token_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to exchange code: {token_response.text}",
        )
    
    tokens = token_response.json()
    short_lived_token = tokens.get("access_token")
    
    if not short_lived_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No access token received",
        )
    
    # Exchange for long-lived token
    async with httpx.AsyncClient() as client:
        long_lived_response = await client.get(
            META_TOKEN_URL,
            params={
                "grant_type": "fb_exchange_token",
                "client_id": settings.meta_app_id,
                "client_secret": settings.meta_app_secret,
                "fb_exchange_token": short_lived_token,
            },
        )
    
    if long_lived_response.status_code == 200:
        long_lived_data = long_lived_response.json()
        access_token = long_lived_data.get("access_token", short_lived_token)
        expires_in = long_lived_data.get("expires_in", 5184000)  # ~60 days
    else:
        access_token = short_lived_token
        expires_in = 3600
    
    # Get user info and ad accounts
    async with httpx.AsyncClient() as client:
        me_response = await client.get(
            "https://graph.facebook.com/v18.0/me",
            params={
                "fields": "id,name,email",
                "access_token": access_token,
            },
        )
    
    fb_user = me_response.json() if me_response.status_code == 200 else {}
    fb_name = fb_user.get("name", "Meta Ads Account")
    fb_id = fb_user.get("id", "unknown")
    
    # Get user's org_id
    supabase = get_supabase_service()
    user = await supabase.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    org_id = user["org_id"]
    
    # Store connected account
    from datetime import datetime, timedelta, timezone
    
    account_data = {
        "org_id": org_id,
        "connected_by": user_id,
        "platform": Platform.META_ADS.value,
        "platform_account_id": fb_id,
        "platform_account_name": fb_name,
        "access_token_encrypted": encrypt_token(access_token),
        "refresh_token_encrypted": None,  # Meta uses long-lived tokens
        "token_expires_at": (
            datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        ).isoformat(),
        "status": "active",
    }
    
    try:
        account = await supabase.create_connected_account(account_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save account: {str(e)}",
        )
    
    # Redirect or return response
    if redirect_uri:
        return RedirectResponse(
            url=f"{redirect_uri}?success=true&account_id={account['id']}"
        )
    
    return OAuthCallbackResponse(
        success=True,
        account_id=account["id"],
        account_name=account["platform_account_name"],
        platform=Platform.META_ADS,
        message="Meta Ads hesabı başarıyla bağlandı",
        redirect_uri=redirect_uri,
    )
