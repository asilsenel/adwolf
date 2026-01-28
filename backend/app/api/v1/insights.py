"""
Ad Platform MVP - Insights Endpoints

AI-generated insights and recommendations.
"""

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
    InsightPriority,
    ActionStatus,
)


router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get("", response_model=InsightList)
async def list_insights(
    org_id: CurrentOrgId,
    supabase: Supabase,
    is_read: Optional[bool] = None,
    type: Optional[InsightType] = None,
    priority: Optional[InsightPriority] = None,
    limit: int = Query(20, ge=1, le=100),
):
    """
    List AI-generated insights for the organization.
    
    Filter by read status, type, or priority.
    """
    insights = await supabase.get_insights(
        org_id=org_id,
        is_read=is_read,
        limit=limit,
    )
    
    # Apply additional filters
    if type:
        insights = [i for i in insights if i.get("type") == type.value]
    if priority:
        insights = [i for i in insights if i.get("priority") == priority.value]
    
    # Count unread
    all_insights = await supabase.get_insights(org_id=org_id, limit=100)
    unread_count = sum(1 for i in all_insights if not i.get("is_read"))
    
    return InsightList(
        insights=[InsightResponse(**i) for i in insights],
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
        .single() \
        .execute()
    
    insight = result.data
    
    if not insight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found",
        )
    
    if insight["org_id"] != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    return InsightResponse(**insight)


@router.post("/{insight_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_insight_read(
    insight_id: str,
    org_id: CurrentOrgId,
    supabase: Supabase,
):
    """Mark an insight as read."""
    # Verify ownership
    result = supabase.client.table("insights") \
        .select("org_id") \
        .eq("id", insight_id) \
        .single() \
        .execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found",
        )
    
    if result.data["org_id"] != org_id:
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
    # Verify ownership
    result = supabase.client.table("insights") \
        .select("org_id") \
        .eq("id", insight_id) \
        .single() \
        .execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found",
        )
    
    if result.data["org_id"] != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    supabase.client.table("insights") \
        .update({
            "is_dismissed": True,
            "dismissed_at": "now()",
        }) \
        .eq("id", insight_id) \
        .execute()
    
    return None


# ===========================================
# ACTIONS
# ===========================================

@router.get("/actions", response_model=ActionList)
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
    
    # Get action
    result = supabase.client.table("recommended_actions") \
        .select("*") \
        .eq("id", action_id) \
        .single() \
        .execute()
    
    action = result.data
    
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found",
        )
    
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
        message="Aksiyon onaylandı. Uygulama kısa sürede gerçekleşecek.",
    )


@router.post("/actions/{action_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_action(
    action_id: str,
    request: ActionDismissRequest,
    org_id: CurrentOrgId,
    supabase: Supabase,
):
    """Dismiss a recommended action."""
    # Verify ownership
    result = supabase.client.table("recommended_actions") \
        .select("org_id") \
        .eq("id", action_id) \
        .single() \
        .execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found",
        )
    
    if result.data["org_id"] != org_id:
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
        .single() \
        .execute()
    
    if not result.data:
        return None
    
    return DailyDigestResponse(**result.data)


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
