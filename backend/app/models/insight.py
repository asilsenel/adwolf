"""
Ad Platform MVP - Insight Models

Pydantic models for AI-generated insights and actions.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.models.account import Platform


class InsightType(str, Enum):
    """Types of insights."""
    PERFORMANCE = "performance"  # Performance summary/analysis
    OPTIMIZATION = "optimization"  # Optimization opportunity
    ALERT = "alert"  # Warning or issue
    OPPORTUNITY = "opportunity"  # Growth opportunity
    ANOMALY = "anomaly"  # Unusual pattern detected


class InsightPriority(str, Enum):
    """Insight priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionStatus(str, Enum):
    """Status of recommended actions."""
    PENDING = "pending"
    APPROVED = "approved"
    EXECUTED = "executed"
    DISMISSED = "dismissed"
    FAILED = "failed"


# ===========================================
# INSIGHT MODELS
# ===========================================

class InsightBase(BaseModel):
    """Base insight model."""
    type: InsightType
    priority: InsightPriority = InsightPriority.MEDIUM
    title: str = Field(..., max_length=500)
    summary: str
    detailed_analysis: Optional[str] = None


class InsightCreate(InsightBase):
    """Model for creating insight (internal)."""
    org_id: str
    account_id: Optional[str] = None
    campaign_id: Optional[str] = None
    ai_model: Optional[str] = None
    ai_confidence: Optional[Decimal] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    metrics_snapshot: Optional[dict] = None
    comparison_period: Optional[str] = None
    valid_until: Optional[datetime] = None


class InsightResponse(InsightBase):
    """Response model for insight."""
    id: str
    org_id: str
    account_id: Optional[str] = None
    campaign_id: Optional[str] = None
    
    # AI metadata
    ai_confidence: Optional[Decimal] = None
    
    # Status
    is_read: bool = False
    is_dismissed: bool = False
    read_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime
    valid_until: Optional[datetime] = None
    
    # Related actions
    actions: list["ActionResponse"] = []

    class Config:
        from_attributes = True


class InsightList(BaseModel):
    """List of insights."""
    insights: list[InsightResponse]
    total: int
    unread_count: int


class InsightReadRequest(BaseModel):
    """Request to mark insight as read."""
    pass  # No body needed


class InsightDismissRequest(BaseModel):
    """Request to dismiss insight."""
    reason: Optional[str] = None


# ===========================================
# RECOMMENDED ACTION MODELS
# ===========================================

class ActionBase(BaseModel):
    """Base action model."""
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    action_type: str  # pause_campaign, increase_budget, etc.


class ActionCreate(ActionBase):
    """Model for creating action (internal)."""
    insight_id: str
    org_id: str
    platform: Optional[Platform] = None
    target_entity_type: Optional[str] = None  # campaign, ad_set, ad
    target_entity_id: Optional[str] = None
    action_params: dict = Field(default_factory=dict)
    expected_impact: Optional[str] = None
    estimated_improvement: Optional[Decimal] = None


class ActionResponse(ActionBase):
    """Response model for action."""
    id: str
    insight_id: str
    org_id: str
    platform: Optional[Platform] = None
    target_entity_type: Optional[str] = None
    target_entity_id: Optional[str] = None
    action_params: dict = Field(default_factory=dict)
    expected_impact: Optional[str] = None
    estimated_improvement: Optional[Decimal] = None
    status: ActionStatus = ActionStatus.PENDING
    executed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ActionList(BaseModel):
    """List of actions."""
    actions: list[ActionResponse]
    total: int
    pending_count: int


class ActionExecuteRequest(BaseModel):
    """Request to execute action."""
    confirm: bool = True


class ActionExecuteResponse(BaseModel):
    """Response after action execution."""
    success: bool
    action_id: str
    message: str
    execution_result: Optional[dict] = None


class ActionDismissRequest(BaseModel):
    """Request to dismiss action."""
    reason: Optional[str] = None


# ===========================================
# DAILY DIGEST MODELS
# ===========================================

class DigestSection(BaseModel):
    """A section in daily digest."""
    title: str
    content: str
    metrics: Optional[dict] = None


class DailyDigestResponse(BaseModel):
    """Daily digest response."""
    id: str
    org_id: str
    digest_date: str  # YYYY-MM-DD
    title: Optional[str] = None
    summary: str
    
    # Metrics summary
    total_spend: Decimal = Decimal("0.00")
    total_impressions: int = 0
    total_clicks: int = 0
    total_conversions: Decimal = Decimal("0")
    currency: str = "TRY"
    
    # Comparisons
    spend_change_percent: Optional[Decimal] = None
    impressions_change_percent: Optional[Decimal] = None
    conversions_change_percent: Optional[Decimal] = None
    
    # Structured content
    sections: list[DigestSection] = []
    
    # Related insights
    insight_ids: list[str] = []
    
    # Delivery info
    sent_via: Optional[str] = None
    sent_at: Optional[datetime] = None
    
    created_at: datetime

    class Config:
        from_attributes = True


class DigestList(BaseModel):
    """List of digests."""
    digests: list[DailyDigestResponse]
    total: int


# Forward reference resolution
InsightResponse.model_rebuild()
