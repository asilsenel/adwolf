"""
Ad Platform MVP - Insight Models

Pydantic models for AI-generated insights and actions.
Aligned with database schema (insights, recommended_actions tables).
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.account import Platform


class InsightType(str, Enum):
    """Types of insights (maps to insight_type column)."""
    PERFORMANCE = "performance"
    OPTIMIZATION = "optimization"
    ALERT = "alert"
    OPPORTUNITY = "opportunity"
    ANOMALY = "anomaly"


class InsightSeverity(str, Enum):
    """Insight severity levels (maps to severity column)."""
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
# RECOMMENDED ACTION MODELS
# ===========================================

class ActionResponse(BaseModel):
    """Response model for recommended action. Aligned with recommended_actions table."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    insight_id: Optional[str] = None
    org_id: str
    action_type: str
    platform: str
    account_id: Optional[str] = None
    campaign_id: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    title: str
    description: str
    rationale: Optional[str] = None
    expected_impact: Optional[str] = None
    is_executable: bool = False
    api_payload: Optional[dict] = None
    priority: int = 50
    recommended_by: Optional[datetime] = None
    status: str = "pending"
    executed_at: Optional[datetime] = None
    executed_by: Optional[str] = None
    execution_result: Optional[dict] = None
    created_at: datetime


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
# INSIGHT MODELS
# ===========================================

class InsightResponse(BaseModel):
    """Response model for insight. Aligned with insights table."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    org_id: str
    insight_type: str = Field(..., alias="insight_type")
    severity: str = Field(..., alias="severity")
    category: Optional[str] = None
    platform: Optional[str] = None
    account_id: Optional[str] = None
    campaign_id: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    title: str
    summary: str
    detailed_analysis: Optional[str] = None
    metric_data: Optional[dict] = Field(None, alias="metric_data")
    comparison_period: Optional[dict] = None

    # Status
    is_read: bool = False
    is_dismissed: bool = False
    is_actioned: bool = False
    read_at: Optional[datetime] = None
    actioned_at: Optional[datetime] = None

    # AI metadata
    ai_model: Optional[str] = None
    ai_confidence: Optional[Decimal] = None

    # Timestamps
    created_at: datetime
    expires_at: Optional[datetime] = None

    # Related actions
    recommended_actions: list[ActionResponse] = []


class InsightList(BaseModel):
    """List of insights."""
    insights: list[InsightResponse]
    total: int
    unread_count: int


class InsightReadRequest(BaseModel):
    """Request to mark insight as read."""
    pass


class InsightDismissRequest(BaseModel):
    """Request to dismiss insight."""
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
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    digest_date: str
    title: Optional[str] = None
    summary: str

    total_spend: Decimal = Decimal("0.00")
    total_impressions: int = 0
    total_clicks: int = 0
    total_conversions: Decimal = Decimal("0")
    currency: str = "TRY"

    spend_change_percent: Optional[Decimal] = None
    impressions_change_percent: Optional[Decimal] = None
    conversions_change_percent: Optional[Decimal] = None

    sections: list[DigestSection] = []
    insight_ids: list[str] = []

    sent_via: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime


class DigestList(BaseModel):
    """List of digests."""
    digests: list[DailyDigestResponse]
    total: int
