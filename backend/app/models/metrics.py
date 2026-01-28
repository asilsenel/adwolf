"""
Ad Platform MVP - Metrics Models

Pydantic models for metrics data.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, computed_field

from app.models.account import Platform


# ===========================================
# DATE RANGE
# ===========================================

class DateRangePreset(str, Enum):
    """Preset date ranges."""
    TODAY = "today"
    YESTERDAY = "yesterday"
    LAST_7_DAYS = "last_7_days"
    LAST_14_DAYS = "last_14_days"
    LAST_30_DAYS = "last_30_days"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    CUSTOM = "custom"


class DateRange(BaseModel):
    """Date range for metrics queries."""
    date_from: date
    date_to: date
    preset: Optional[DateRangePreset] = None


# ===========================================
# CORE METRICS
# ===========================================

class BaseMetrics(BaseModel):
    """Base metrics that all levels share."""
    impressions: int = 0
    clicks: int = 0
    spend: Decimal = Decimal("0.00")  # Converted from micros
    currency: str = "TRY"
    conversions: Decimal = Decimal("0")
    conversion_value: Decimal = Decimal("0.00")

    @computed_field
    @property
    def ctr(self) -> Optional[Decimal]:
        """Click-through rate."""
        if self.impressions == 0:
            return None
        return Decimal(self.clicks) / Decimal(self.impressions) * 100

    @computed_field
    @property
    def cpc(self) -> Optional[Decimal]:
        """Cost per click."""
        if self.clicks == 0:
            return None
        return self.spend / Decimal(self.clicks)

    @computed_field
    @property
    def cpm(self) -> Optional[Decimal]:
        """Cost per mille (1000 impressions)."""
        if self.impressions == 0:
            return None
        return self.spend / Decimal(self.impressions) * 1000

    @computed_field
    @property
    def roas(self) -> Optional[Decimal]:
        """Return on ad spend."""
        if self.spend == 0:
            return None
        return self.conversion_value / self.spend

    @computed_field
    @property
    def cpa(self) -> Optional[Decimal]:
        """Cost per acquisition."""
        if self.conversions == 0:
            return None
        return self.spend / self.conversions


class DailyMetrics(BaseMetrics):
    """Daily metrics for a specific entity."""
    id: str
    account_id: str
    campaign_id: Optional[str] = None
    ad_set_id: Optional[str] = None
    platform: Platform
    date: date
    
    # Extra platform-specific metrics
    extra_metrics: dict = Field(default_factory=dict)

    class Config:
        from_attributes = True


# ===========================================
# AGGREGATED METRICS
# ===========================================

class MetricChange(BaseModel):
    """Metric change compared to previous period."""
    current: Decimal
    previous: Decimal
    change_absolute: Decimal
    change_percent: Optional[Decimal] = None

    @classmethod
    def calculate(cls, current: Decimal, previous: Decimal) -> "MetricChange":
        """Calculate change from two values."""
        change_absolute = current - previous
        change_percent = None
        if previous != 0:
            change_percent = (change_absolute / previous) * 100
        
        return cls(
            current=current,
            previous=previous,
            change_absolute=change_absolute,
            change_percent=change_percent
        )


class MetricsSummary(BaseModel):
    """Summary metrics with period comparison."""
    date_from: date
    date_to: date
    comparison_date_from: Optional[date] = None
    comparison_date_to: Optional[date] = None
    
    # Current period metrics
    impressions: int = 0
    clicks: int = 0
    spend: Decimal = Decimal("0.00")
    conversions: Decimal = Decimal("0")
    conversion_value: Decimal = Decimal("0.00")
    currency: str = "TRY"
    
    # Calculated metrics
    ctr: Optional[Decimal] = None
    cpc: Optional[Decimal] = None
    cpm: Optional[Decimal] = None  
    roas: Optional[Decimal] = None
    cpa: Optional[Decimal] = None
    
    # Changes (if comparison period provided)
    impressions_change: Optional[MetricChange] = None
    clicks_change: Optional[MetricChange] = None
    spend_change: Optional[MetricChange] = None
    conversions_change: Optional[MetricChange] = None
    roas_change: Optional[MetricChange] = None
    
    # Breakdown
    accounts_count: int = 0
    campaigns_count: int = 0


class MetricsByDate(BaseModel):
    """Metrics grouped by date for charts."""
    date: date
    impressions: int = 0
    clicks: int = 0
    spend: Decimal = Decimal("0.00")
    conversions: Decimal = Decimal("0")
    conversion_value: Decimal = Decimal("0.00")


class MetricsTrend(BaseModel):
    """Metrics trend over time."""
    date_from: date
    date_to: date
    data: list[MetricsByDate]
    summary: MetricsSummary


# ===========================================
# CAMPAIGN METRICS
# ===========================================

class CampaignMetrics(BaseMetrics):
    """Campaign with aggregated metrics."""
    id: str
    account_id: str
    platform: Platform
    platform_campaign_id: str
    name: str
    status: str
    campaign_type: Optional[str] = None
    
    # Period being reported
    date_from: date
    date_to: date
    
    # Previous period comparison
    impressions_change_percent: Optional[Decimal] = None
    spend_change_percent: Optional[Decimal] = None
    roas_change_percent: Optional[Decimal] = None

    class Config:
        from_attributes = True


class CampaignMetricsList(BaseModel):
    """List of campaigns with metrics."""
    campaigns: list[CampaignMetrics]
    total: int
    page: int
    per_page: int


# ===========================================
# PLATFORM BREAKDOWN
# ===========================================

class PlatformMetrics(BaseMetrics):
    """Metrics breakdown by platform."""
    platform: Platform
    accounts_count: int = 0
    campaigns_count: int = 0


class MetricsByPlatform(BaseModel):
    """Metrics grouped by platform."""
    date_from: date
    date_to: date
    platforms: list[PlatformMetrics]
    total: MetricsSummary
