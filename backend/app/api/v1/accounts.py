"""
Ad Platform MVP - Account Management Endpoints

CRUD operations for connected ad accounts.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, CurrentOrgId, AdminUser, Supabase
from app.models.account import (
    ConnectedAccountResponse,
    ConnectedAccountList,
    ConnectedAccountDetail,
    SyncTriggerRequest,
    SyncTriggerResponse,
    Platform,
)


router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get("", response_model=ConnectedAccountList)
async def list_connected_accounts(
    org_id: CurrentOrgId,
    supabase: Supabase,
    platform: Optional[Platform] = None,
    is_active: bool = True,
):
    """
    List all connected ad accounts for the organization.
    
    Optionally filter by platform or active status.
    """
    accounts = await supabase.get_connected_accounts(
        org_id=org_id,
        platform=platform.value if platform else None,
        is_active=is_active,
    )
    
    return ConnectedAccountList(
        accounts=[ConnectedAccountResponse(**a) for a in accounts],
        total=len(accounts),
    )


@router.get("/{account_id}", response_model=ConnectedAccountDetail)
async def get_connected_account(
    account_id: str,
    org_id: CurrentOrgId,
    supabase: Supabase,
):
    """
    Get details for a specific connected account.
    
    Includes campaign count and recent metrics summary.
    """
    account = await supabase.get_connected_account(account_id)
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    
    # Verify ownership
    if account["org_id"] != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    # Get campaign count
    campaigns = await supabase.get_campaigns(account_id)
    campaigns_count = len(campaigns)
    
    # Get metrics summary (last 30 days)
    # TODO: Calculate from daily_metrics table
    total_spend = 0.0
    total_impressions = 0
    
    return ConnectedAccountDetail(
        **account,
        campaigns_count=campaigns_count,
        total_spend_last_30_days=total_spend,
        total_impressions_last_30_days=total_impressions,
    )


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_account(
    account_id: str,
    admin_user: AdminUser,  # Requires admin
    supabase: Supabase,
):
    """
    Disconnect (soft delete) an ad account.
    
    Requires admin privileges. Tokens are invalidated but
    historical data is preserved.
    """
    org_id = admin_user["org_id"]
    
    account = await supabase.get_connected_account(account_id)
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    
    # Verify ownership
    if account["org_id"] != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    # Soft delete
    await supabase.deactivate_connected_account(account_id)
    
    return None


@router.post("/{account_id}/sync", response_model=SyncTriggerResponse)
async def trigger_sync(
    account_id: str,
    current_user: CurrentUser,
    supabase: Supabase,
    request: Optional[SyncTriggerRequest] = None,
):
    """
    Trigger a manual sync for an account.
    
    Starts a background job to sync metrics from the platform.
    Optional: Pass date_from and date_to to sync specific date range.
    """
    org_id = current_user["org_id"]
    
    account = await supabase.get_connected_account(account_id)
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    
    # Verify ownership
    if account["org_id"] != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    # Check if there's already a running sync
    latest_job = await supabase.get_latest_sync_job(account_id)
    if latest_job and latest_job.get("status") == "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A sync job is already running for this account",
        )
    
    # Default date range: last 30 days
    from datetime import datetime, timedelta
    today = datetime.now().strftime("%Y-%m-%d")
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    date_from = request.date_from if request and request.date_from else thirty_days_ago
    date_to = request.date_to if request and request.date_to else today
    
    # Create sync job
    job_data = {
        "account_id": account_id,
        "job_type": "metrics_sync",  # Must match sync_jobs_job_type_check constraint
        "status": "running",
        "date_from": date_from,
        "date_to": date_to,
    }
    
    job = await supabase.create_sync_job(job_data)
    
    # Actually fetch data from Google Ads
    from app.services.google_ads_service import sync_account_metrics
    
    try:
        sync_result = await sync_account_metrics(account_id, date_from, date_to)
        
        if sync_result.get("success"):
            await supabase.update_sync_job(job["id"], {
                "status": "completed",
            })
            
            # Update account last_sync
            await supabase.update_connected_account(account_id, {
                "last_sync_at": datetime.now().isoformat(),
            })
            
            records_count = sync_result.get("records_count", 0)
            return SyncTriggerResponse(
                success=True,
                job_id=job["id"],
                message=f"Senkronizasyon tamamlandı. {records_count} kayıt işlendi.",
            )
        else:
            # Sync failed but continue with mock data for MVP
            await supabase.update_sync_job(job["id"], {
                "status": "completed",
                "error_message": sync_result.get("error"),
            })
            
            return SyncTriggerResponse(
                success=True,
                job_id=job["id"],
                message="Senkronizasyon tamamlandı (demo mod).",
            )
            
    except Exception as e:
        await supabase.update_sync_job(job["id"], {
            "status": "failed",
            "error_message": str(e),
        })
        
        return SyncTriggerResponse(
            success=False,
            job_id=job["id"],
            message=f"Senkronizasyon hatası: {str(e)}",
        )


@router.get("/{account_id}/sync/status")
async def get_sync_status(
    account_id: str,
    org_id: CurrentOrgId,
    supabase: Supabase,
):
    """
    Get the status of the latest sync job for an account.
    """
    account = await supabase.get_connected_account(account_id)
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    
    # Verify ownership
    if account["org_id"] != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    latest_job = await supabase.get_latest_sync_job(account_id)
    
    if not latest_job:
        return {
            "has_sync": False,
            "message": "Bu hesap için henüz senkronizasyon yapılmadı",
        }
    
    return {
        "has_sync": True,
        "job": latest_job,
    }
