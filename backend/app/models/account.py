"""
Ad Platform MVP - Account Models

Pydantic models for connected ad accounts and OAuth.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Platform(str, Enum):
    """Supported ad platforms."""
    GOOGLE_ADS = "google_ads"
    META_ADS = "meta_ads"
    # Future platforms
    AMAZON_ADS = "amazon_ads"
    TIKTOK_ADS = "tiktok_ads"


class AccountStatus(str, Enum):
    """Account connection status."""
    ACTIVE = "active"
    PAUSED = "paused"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class SyncStatus(str, Enum):
    """Sync job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ===========================================
# OAUTH MODELS
# ===========================================

class OAuthInitiateRequest(BaseModel):
    """Request to initiate OAuth flow."""
    redirect_uri: Optional[str] = Field(
        None,
        description="Where to redirect after successful connection"
    )


class OAuthInitiateResponse(BaseModel):
    """Response with OAuth authorization URL."""
    authorization_url: str
    state: str
    platform: Platform


class OAuthCallbackRequest(BaseModel):
    """OAuth callback parameters."""
    code: str
    state: str
    error: Optional[str] = None
    error_description: Optional[str] = None


class OAuthCallbackResponse(BaseModel):
    """Response after successful OAuth callback."""
    success: bool
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    platform: Platform
    message: str
    redirect_uri: Optional[str] = None


# ===========================================
# CONNECTED ACCOUNT MODELS
# ===========================================

class ConnectedAccountBase(BaseModel):
    """Base model for connected accounts."""
    platform: Platform
    platform_account_id: str
    platform_account_name: Optional[str] = None
    settings: dict = Field(default_factory=dict)


class ConnectedAccountCreate(ConnectedAccountBase):
    """Model for creating a connected account (internal)."""
    org_id: str
    connected_by: str
    access_token_encrypted: str
    refresh_token_encrypted: Optional[str] = None
    token_expires_at: Optional[datetime] = None


class ConnectedAccountResponse(BaseModel):
    """Response model for connected account."""
    id: str
    org_id: str
    platform: Platform
    platform_account_id: str
    platform_account_name: Optional[str] = None
    status: AccountStatus
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[SyncStatus] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConnectedAccountList(BaseModel):
    """List response for connected accounts."""
    accounts: list[ConnectedAccountResponse]
    total: int


class ConnectedAccountDetail(ConnectedAccountResponse):
    """Detailed account with additional stats."""
    campaigns_count: int = 0
    total_spend_last_30_days: float = 0.0
    total_impressions_last_30_days: int = 0


# ===========================================
# SYNC JOB MODELS
# ===========================================

class SyncJobResponse(BaseModel):
    """Response model for sync job."""
    id: str
    account_id: str
    job_type: str
    status: SyncStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    records_synced: int = 0
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SyncTriggerRequest(BaseModel):
    """Request to trigger manual sync."""
    date_from: Optional[str] = Field(
        None,
        description="Start date for sync (YYYY-MM-DD)"
    )
    date_to: Optional[str] = Field(
        None,
        description="End date for sync (YYYY-MM-DD)"
    )


class SyncTriggerResponse(BaseModel):
    """Response after triggering sync."""
    success: bool
    job_id: str
    message: str
