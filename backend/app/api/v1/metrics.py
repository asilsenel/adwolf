"""
Ad Platform MVP - Metrics Endpoints

Metrics queries and aggregations.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Literal, Optional

from fastapi import APIRouter, Query

from app.api.deps import CurrentOrgId, Supabase
from app.models.account import Platform
from app.models.metrics import (
    DateRange,
    DateRangePreset,
    MetricsSummary,
    MetricsTrend,
    MetricsByDate,
    CampaignMetrics,
    CampaignMetricsList,
    MetricsByPlatform,
    PlatformMetrics,
)


router = APIRouter(prefix="/metrics", tags=["Metrics"])


def get_date_range(preset: DateRangePreset) -> tuple[date, date]:
    """Convert preset to actual date range."""
    today = date.today()
    
    if preset == DateRangePreset.TODAY:
        return today, today
    elif preset == DateRangePreset.YESTERDAY:
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    elif preset == DateRangePreset.LAST_7_DAYS:
        return today - timedelta(days=6), today
    elif preset == DateRangePreset.LAST_14_DAYS:
        return today - timedelta(days=13), today
    elif preset == DateRangePreset.LAST_30_DAYS:
        return today - timedelta(days=29), today
    elif preset == DateRangePreset.THIS_MONTH:
        return today.replace(day=1), today
    elif preset == DateRangePreset.LAST_MONTH:
        first_of_this_month = today.replace(day=1)
        last_of_prev_month = first_of_this_month - timedelta(days=1)
        first_of_prev_month = last_of_prev_month.replace(day=1)
        return first_of_prev_month, last_of_prev_month
    else:
        # Default to last 7 days
        return today - timedelta(days=6), today


@router.get("/summary", response_model=MetricsSummary)
async def get_metrics_summary(
    org_id: CurrentOrgId,
    supabase: Supabase,
    preset: DateRangePreset = Query(
        DateRangePreset.LAST_7_DAYS,
        description="Preset date range"
    ),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    compare: bool = Query(True, description="Include comparison with previous period"),
    account_id: Optional[str] = None,
    platform: Optional[Platform] = None,
):
    """
    Get aggregated metrics summary across all accounts.
    
    Includes comparison with previous period if requested.
    """
    # Determine date range
    if date_from and date_to:
        start_date, end_date = date_from, date_to
    else:
        start_date, end_date = get_date_range(preset)
    
    # Get metrics
    metrics = await supabase.get_daily_metrics(
        org_id=org_id,
        date_from=start_date.isoformat(),
        date_to=end_date.isoformat(),
        account_id=account_id,
    )
    
    # Aggregate - database stores spend directly in currency (not micros)
    total_impressions = sum(m.get("impressions", 0) for m in metrics)
    total_clicks = sum(m.get("clicks", 0) for m in metrics)
    # Database uses 'spend' column directly (numeric, in TRY)
    total_spend = sum(Decimal(str(m.get("spend", 0) or 0)) for m in metrics)
    total_conversions = sum(Decimal(str(m.get("conversions", 0) or 0)) for m in metrics)
    # Database uses 'conversion_value' column directly (numeric, in TRY)
    total_conv_value = sum(Decimal(str(m.get("conversion_value", 0) or 0)) for m in metrics)
    
    # Calculate rates
    ctr = None
    cpc = None
    cpm = None
    roas = None
    cpa = None
    
    if total_impressions > 0:
        ctr = Decimal(total_clicks) / Decimal(total_impressions) * 100
        cpm = total_spend / Decimal(total_impressions) * 1000
    
    if total_clicks > 0:
        cpc = total_spend / Decimal(total_clicks)
    
    if total_spend > 0:
        roas = total_conv_value / total_spend
    
    if total_conversions > 0:
        cpa = total_spend / total_conversions
    
    # Get unique counts - use entity_id for campaign ID
    account_ids = set(m.get("account_id") for m in metrics)
    campaign_ids = set(m.get("entity_id") for m in metrics if m.get("entity_id"))
    
    summary = MetricsSummary(
        date_from=start_date,
        date_to=end_date,
        impressions=total_impressions,
        clicks=total_clicks,
        spend=total_spend,
        conversions=total_conversions,
        conversion_value=total_conv_value,
        currency="TRY",
        ctr=ctr,
        cpc=cpc,
        cpm=cpm,
        roas=roas,
        cpa=cpa,
        accounts_count=len(account_ids),
        campaigns_count=len(campaign_ids),
    )
    
    # TODO: Add comparison period metrics
    
    return summary


@router.get("/daily", response_model=MetricsTrend)
async def get_daily_metrics(
    org_id: CurrentOrgId,
    supabase: Supabase,
    preset: DateRangePreset = Query(DateRangePreset.LAST_7_DAYS),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    account_id: Optional[str] = None,
):
    """
    Get daily metrics for charting.
    
    Returns metrics broken down by day.
    """
    # Determine date range
    if date_from and date_to:
        start_date, end_date = date_from, date_to
    else:
        start_date, end_date = get_date_range(preset)
    
    # Get metrics
    metrics = await supabase.get_daily_metrics(
        org_id=org_id,
        date_from=start_date.isoformat(),
        date_to=end_date.isoformat(),
        account_id=account_id,
    )
    
    # Group by date - database stores spend directly in currency
    from collections import defaultdict
    daily_agg = defaultdict(lambda: {
        "impressions": 0,
        "clicks": 0,
        "spend": Decimal("0"),
        "conversions": Decimal("0"),
        "conversion_value": Decimal("0"),
    })

    for m in metrics:
        d = m.get("date")
        daily_agg[d]["impressions"] += m.get("impressions", 0)
        daily_agg[d]["clicks"] += m.get("clicks", 0)
        daily_agg[d]["spend"] += Decimal(str(m.get("spend", 0) or 0))
        daily_agg[d]["conversions"] += Decimal(str(m.get("conversions", 0) or 0))
        daily_agg[d]["conversion_value"] += Decimal(str(m.get("conversion_value", 0) or 0))

    # Convert to list - spend is already in currency
    data = []
    for d, agg in sorted(daily_agg.items()):
        data.append(MetricsByDate(
            date=date.fromisoformat(d) if isinstance(d, str) else d,
            impressions=agg["impressions"],
            clicks=agg["clicks"],
            spend=agg["spend"],
            conversions=agg["conversions"],
            conversion_value=agg["conversion_value"],
        ))
    
    # Get summary
    summary = await get_metrics_summary(
        org_id=org_id,
        supabase=supabase,
        date_from=start_date,
        date_to=end_date,
        compare=False,
        account_id=account_id,
    )
    
    return MetricsTrend(
        date_from=start_date,
        date_to=end_date,
        data=data,
        summary=summary,
    )


@router.get("/campaigns", response_model=CampaignMetricsList)
async def get_campaign_metrics(
    org_id: CurrentOrgId,
    supabase: Supabase,
    preset: DateRangePreset = Query(DateRangePreset.LAST_7_DAYS),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    account_id: Optional[str] = None,
    platform: Optional[Platform] = None,
    sort_by: str = Query("spend", description="Sort by field"),
    sort_order: Literal["asc", "desc"] = Query("desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """
    Get metrics grouped by campaign.
    
    Supports pagination and sorting.
    """
    # Determine date range
    if date_from and date_to:
        start_date, end_date = date_from, date_to
    else:
        start_date, end_date = get_date_range(preset)
    
    # Get all campaigns for the org's accounts
    accounts = await supabase.get_connected_accounts(org_id=org_id)
    
    all_campaigns = []
    for account in accounts:
        if platform and account["platform"] != platform.value:
            continue
        if account_id and account["id"] != account_id:
            continue
        
        campaigns = await supabase.get_campaigns(account["id"])
        for c in campaigns:
            c["account_platform"] = account["platform"]
        all_campaigns.extend(campaigns)
    
    # Get metrics for each campaign
    metrics = await supabase.get_daily_metrics(
        org_id=org_id,
        date_from=start_date.isoformat(),
        date_to=end_date.isoformat(),
        account_id=account_id,
    )
    
    # Aggregate by campaign
    from collections import defaultdict
    campaign_metrics = defaultdict(lambda: {
        "impressions": 0,
        "clicks": 0,
        "spend": Decimal("0"),
        "conversions": Decimal("0"),
        "conversion_value": Decimal("0"),
    })

    for m in metrics:
        cid = m.get("campaign_id")
        if cid:
            campaign_metrics[cid]["impressions"] += m.get("impressions", 0)
            campaign_metrics[cid]["clicks"] += m.get("clicks", 0)
            campaign_metrics[cid]["spend"] += Decimal(str(m.get("spend", 0) or 0))
            campaign_metrics[cid]["conversions"] += Decimal(str(m.get("conversions", 0) or 0))
            campaign_metrics[cid]["conversion_value"] += Decimal(str(m.get("conversion_value", 0) or 0))

    # Build response
    result = []
    for campaign in all_campaigns:
        cid = campaign["id"]
        cm = campaign_metrics.get(cid, {})

        spend = cm.get("spend", Decimal("0"))
        conv_value = cm.get("conversion_value", Decimal("0"))
        
        result.append(CampaignMetrics(
            id=campaign["id"],
            account_id=campaign["account_id"],
            platform=Platform(campaign.get("account_platform", campaign["platform"])),
            platform_campaign_id=campaign["platform_campaign_id"],
            name=campaign["name"],
            status=campaign.get("status", "unknown"),
            campaign_type=campaign.get("campaign_type"),
            date_from=start_date,
            date_to=end_date,
            impressions=cm.get("impressions", 0),
            clicks=cm.get("clicks", 0),
            spend=spend,
            currency="TRY",
            conversions=cm.get("conversions", Decimal("0")),
            conversion_value=conv_value,
        ))
    
    # Sort
    reverse = sort_order == "desc"
    result.sort(key=lambda x: getattr(x, sort_by, 0) or 0, reverse=reverse)
    
    # Paginate
    total = len(result)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = result[start:end]
    
    return CampaignMetricsList(
        campaigns=paginated,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/by-platform", response_model=MetricsByPlatform)
async def get_metrics_by_platform(
    org_id: CurrentOrgId,
    supabase: Supabase,
    preset: DateRangePreset = Query(DateRangePreset.LAST_7_DAYS),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    account_id: Optional[str] = None,
):
    """
    Get metrics breakdown by platform.
    
    Useful for comparing Google Ads vs Meta Ads performance.
    """
    # Determine date range
    if date_from and date_to:
        start_date, end_date = date_from, date_to
    else:
        start_date, end_date = get_date_range(preset)
    
    # Get metrics (with optional account filter)
    metrics = await supabase.get_daily_metrics(
        org_id=org_id,
        date_from=start_date.isoformat(),
        date_to=end_date.isoformat(),
        account_id=account_id,
    )

    # Get accounts for platform info
    accounts = await supabase.get_connected_accounts(org_id=org_id)
    account_platform = {a["id"]: a["platform"] for a in accounts}
    
    # Aggregate by platform - database stores spend directly in currency
    from collections import defaultdict
    platform_agg = defaultdict(lambda: {
        "impressions": 0,
        "clicks": 0,
        "spend": Decimal("0"),
        "conversions": Decimal("0"),
        "conversion_value": Decimal("0"),
        "account_ids": set(),
        "campaign_ids": set(),
    })

    for m in metrics:
        p = m.get("platform") or account_platform.get(m.get("account_id"))
        if p:
            platform_agg[p]["impressions"] += m.get("impressions", 0)
            platform_agg[p]["clicks"] += m.get("clicks", 0)
            platform_agg[p]["spend"] += Decimal(str(m.get("spend", 0) or 0))
            platform_agg[p]["conversions"] += Decimal(str(m.get("conversions", 0) or 0))
            platform_agg[p]["conversion_value"] += Decimal(str(m.get("conversion_value", 0) or 0))
            platform_agg[p]["account_ids"].add(m.get("account_id"))
            if m.get("entity_id"):
                platform_agg[p]["campaign_ids"].add(m.get("entity_id"))

    # Build response - spend is already in currency
    platforms = []
    for p, agg in platform_agg.items():
        platforms.append(PlatformMetrics(
            platform=Platform(p),
            impressions=agg["impressions"],
            clicks=agg["clicks"],
            spend=agg["spend"],
            currency="TRY",
            conversions=agg["conversions"],
            conversion_value=agg["conversion_value"],
            accounts_count=len(agg["account_ids"]),
            campaigns_count=len(agg["campaign_ids"]),
        ))
    
    # Get total summary (with optional account filter)
    total = await get_metrics_summary(
        org_id=org_id,
        supabase=supabase,
        date_from=start_date,
        date_to=end_date,
        compare=False,
        account_id=account_id,
    )
    
    return MetricsByPlatform(
        date_from=start_date,
        date_to=end_date,
        platforms=platforms,
        total=total,
    )
