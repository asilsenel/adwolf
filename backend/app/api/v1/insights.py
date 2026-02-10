"""
Ad Platform MVP - Insights Endpoints

AI-generated insights and recommendations.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, CurrentOrgId, Supabase
from app.models.insight import (
    InsightResponse,
    InsightList,
    InsightReadRequest,
    InsightDismissRequest,
    ActionResponse,
    ActionList,
    ActionExecuteRequest,
    ActionExecuteResponse,
    ActionDismissRequest,
    DailyDigestResponse,
    DigestList,
    InsightType,
    InsightSeverity,
    ActionStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights", tags=["Insights"])


# ===========================================
# GENERATE ENDPOINT (must be before /{insight_id})
# ===========================================

@router.post("/generate", response_model=InsightList)
async def generate_insights(
    org_id: CurrentOrgId,
    supabase: Supabase,
):
    """
    Manually trigger AI insight generation.

    Rate limited: max once every 15 minutes per org.
    """
    from app.tasks.insight_tasks import generate_org_insights

    # Rate limit check: 15 minutes
    latest_time = await supabase.get_latest_insight_time(org_id)
    if latest_time:
        try:
            latest_dt = datetime.fromisoformat(latest_time.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            diff_minutes = (now - latest_dt).total_seconds() / 60
            if diff_minutes < 15:
                remaining = int(15 - diff_minutes)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Insight olusturma icin {remaining} dakika beklemeniz gerekiyor.",
                )
        except (ValueError, TypeError):
            pass  # If parsing fails, allow generation

    # Generate insights synchronously
    try:
        created = await generate_org_insights(org_id)
    except Exception as e:
        logger.error(f"Insight generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Insight olusturma basarisiz: {str(e)}",
        )

    # Fetch fresh insights to return
    insights = await supabase.get_insights(org_id=org_id, limit=20)
    all_insights = await supabase.get_insights(org_id=org_id, limit=100)
    unread_count = sum(1 for i in all_insights if not i.get("is_read"))

    return InsightList(
        insights=[_parse_insight(i) for i in insights],
        total=len(insights),
        unread_count=unread_count,
    )


# ===========================================
# LIST / GET INSIGHTS
# ===========================================

@router.get("", response_model=InsightList)
async def list_insights(
    org_id: CurrentOrgId,
    supabase: Supabase,
    is_read: Optional[bool] = None,
    insight_type: Optional[InsightType] = Query(None, alias="type"),
    severity: Optional[InsightSeverity] = Query(None, alias="priority"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    List AI-generated insights for the organization.

    Filter by read status, type, or severity.
    """
    insights = await supabase.get_insights(
        org_id=org_id,
        is_read=is_read,
        limit=limit,
    )

    # Apply additional filters using correct DB column names
    if insight_type:
        insights = [i for i in insights if i.get("insight_type") == insight_type.value]
    if severity:
        insights = [i for i in insights if i.get("severity") == severity.value]

    # Count unread
    all_insights = await supabase.get_insights(org_id=org_id, limit=100)
    unread_count = sum(1 for i in all_insights if not i.get("is_read"))

    return InsightList(
        insights=[_parse_insight(i) for i in insights],
        total=len(insights),
        unread_count=unread_count,
    )


@router.get("/{insight_id}", response_model=InsightResponse)
async def get_insight(
    insight_id: str,
    org_id: CurrentOrgId,
    supabase: Supabase,
):
    """Get a specific insight by ID."""
    result = supabase.client.table("insights") \
        .select("*, recommended_actions(*)") \
        .eq("id", insight_id) \
        .limit(1) \
        .execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found",
        )

    insight = result.data[0]

    if insight["org_id"] != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return _parse_insight(insight)


# ===========================================
# INSIGHT ACTIONS
# ===========================================

@router.post("/{insight_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_insight_read(
    insight_id: str,
    org_id: CurrentOrgId,
    supabase: Supabase,
):
    """Mark an insight as read."""
    result = supabase.client.table("insights") \
        .select("org_id") \
        .eq("id", insight_id) \
        .limit(1) \
        .execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found",
        )

    if result.data[0]["org_id"] != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    await supabase.mark_insight_read(insight_id)
    return None


@router.post("/{insight_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_insight(
    insight_id: str,
    request: InsightDismissRequest,
    org_id: CurrentOrgId,
    supabase: Supabase,
):
    """Dismiss an insight (hide from list)."""
    result = supabase.client.table("insights") \
        .select("org_id") \
        .eq("id", insight_id) \
        .limit(1) \
        .execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found",
        )

    if result.data[0]["org_id"] != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    supabase.client.table("insights") \
        .update({
            "is_dismissed": True,
        }) \
        .eq("id", insight_id) \
        .execute()

    return None


# ===========================================
# RECOMMENDED ACTIONS
# ===========================================

@router.get("/actions/list", response_model=ActionList)
async def list_actions(
    org_id: CurrentOrgId,
    supabase: Supabase,
    status_filter: Optional[ActionStatus] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
):
    """List recommended actions for the organization."""
    query = supabase.client.table("recommended_actions") \
        .select("*") \
        .eq("org_id", org_id)

    if status_filter:
        query = query.eq("status", status_filter.value)

    result = query \
        .order("created_at", desc=True) \
        .limit(limit) \
        .execute()

    actions = result.data or []
    pending_count = sum(1 for a in actions if a.get("status") == "pending")

    return ActionList(
        actions=[ActionResponse(**a) for a in actions],
        total=len(actions),
        pending_count=pending_count,
    )


@router.post("/actions/{action_id}/execute", response_model=ActionExecuteResponse)
async def execute_action(
    action_id: str,
    request: ActionExecuteRequest,
    current_user: CurrentUser,
    supabase: Supabase,
):
    """
    Execute a recommended action.

    This will call the platform API to make the change.
    """
    org_id = current_user["org_id"]

    result = supabase.client.table("recommended_actions") \
        .select("*") \
        .eq("id", action_id) \
        .limit(1) \
        .execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found",
        )

    action = result.data[0]

    if action["org_id"] != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    if action["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Action is not pending (current: {action['status']})",
        )

    # TODO: Actually execute the action via platform connector
    # For now, just mark as approved
    supabase.client.table("recommended_actions") \
        .update({
            "status": "approved",
            "executed_at": "now()",
            "executed_by": current_user["id"],
        }) \
        .eq("id", action_id) \
        .execute()

    return ActionExecuteResponse(
        success=True,
        action_id=action_id,
        message="Aksiyon onaylandi. Uygulama kisa surede gerceklesecek.",
    )


@router.post("/actions/{action_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_action(
    action_id: str,
    request: ActionDismissRequest,
    org_id: CurrentOrgId,
    supabase: Supabase,
):
    """Dismiss a recommended action."""
    result = supabase.client.table("recommended_actions") \
        .select("org_id") \
        .eq("id", action_id) \
        .limit(1) \
        .execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found",
        )

    if result.data[0]["org_id"] != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    supabase.client.table("recommended_actions") \
        .update({"status": "dismissed"}) \
        .eq("id", action_id) \
        .execute()

    return None


# ===========================================
# DAILY DIGEST
# ===========================================

@router.get("/digest/today", response_model=Optional[DailyDigestResponse])
async def get_today_digest(
    org_id: CurrentOrgId,
    supabase: Supabase,
):
    """Get today's daily digest."""
    from datetime import date

    today = date.today().isoformat()

    result = supabase.client.table("daily_digests") \
        .select("*") \
        .eq("org_id", org_id) \
        .eq("digest_date", today) \
        .limit(1) \
        .execute()

    if not result.data:
        return None

    return DailyDigestResponse(**result.data[0])


@router.get("/digest/history", response_model=DigestList)
async def get_digest_history(
    org_id: CurrentOrgId,
    supabase: Supabase,
    limit: int = Query(7, ge=1, le=30),
):
    """Get historical daily digests."""
    result = supabase.client.table("daily_digests") \
        .select("*") \
        .eq("org_id", org_id) \
        .order("digest_date", desc=True) \
        .limit(limit) \
        .execute()

    digests = result.data or []

    return DigestList(
        digests=[DailyDigestResponse(**d) for d in digests],
        total=len(digests),
    )


# ===========================================
# HELPER FUNCTIONS
# ===========================================

def _parse_insight(data: dict) -> InsightResponse:
    """Parse raw insight dict into InsightResponse, handling nested actions."""
    # Make a copy to avoid mutating the original
    data = dict(data)

    # Extract recommended_actions from the join
    actions_data = data.pop("recommended_actions", []) or []
    # Also remove connected_accounts join data if present
    data.pop("connected_accounts", None)

    actions = []
    for a in actions_data:
        try:
            actions.append(ActionResponse(**a))
        except Exception:
            pass

    return InsightResponse(
        recommended_actions=actions,
        **data,
    )
