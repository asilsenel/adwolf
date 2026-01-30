"""
Ad Platform MVP - Sync Tasks

Celery tasks for syncing data from ad platforms.
"""

import logging
from datetime import date, timedelta
from typing import Optional

from app.tasks import celery_app
from app.core.supabase import get_supabase_service
from app.core.security import decrypt_token

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.tasks.sync_tasks.sync_account_metrics",
)
def sync_account_metrics(
    self,
    job_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """
    Sync metrics for a single account.
    
    Args:
        job_id: Sync job ID from database
        date_from: Start date (YYYY-MM-DD), defaults to yesterday
        date_to: End date (YYYY-MM-DD), defaults to yesterday
    """
    import asyncio
    asyncio.run(_sync_account_metrics_async(self, job_id, date_from, date_to))


async def _sync_account_metrics_async(
    task,
    job_id: str,
    date_from: Optional[str],
    date_to: Optional[str],
):
    """Async implementation of sync_account_metrics."""
    supabase = get_supabase_service()
    
    try:
        # Get sync job
        job_result = supabase.client.table("sync_jobs") \
            .select("*, connected_accounts(*)") \
            .eq("id", job_id) \
            .single() \
            .execute()
        
        job = job_result.data
        if not job:
            logger.error(f"Sync job not found: {job_id}")
            return
        
        account = job.get("connected_accounts")
        if not account:
            logger.error(f"Account not found for job: {job_id}")
            await supabase.update_sync_job(job_id, {
                "status": "failed",
                "error_message": "Account not found",
            })
            return
        
        # Update job status to running
        await supabase.update_sync_job(job_id, {
            "status": "running",
            "started_at": "now()",
            "celery_task_id": task.request.id,
        })
        
        # Determine date range - default to last 30 days
        if not date_from or not date_to:
            today = date.today()
            sync_date_to = date.fromisoformat(date_to) if date_to else today - timedelta(days=1)
            sync_date_from = date.fromisoformat(date_from) if date_from else today - timedelta(days=30)
        else:
            sync_date_from = date.fromisoformat(date_from)
            sync_date_to = date.fromisoformat(date_to)
        
        # Decrypt tokens
        access_token = decrypt_token(account["access_token_encrypted"])
        refresh_token = None
        if account.get("refresh_token_encrypted"):
            refresh_token = decrypt_token(account["refresh_token_encrypted"])
        
        # Get appropriate connector
        platform = account["platform"]
        records_synced = 0
        
        if platform == "google_ads":
            from app.connectors.google_ads import GoogleAdsConnector
            
            logger.info(f"Syncing Google Ads for account {account['id']}")
            
            # Check if this is a client account under an MCC
            platform_metadata = account.get("platform_metadata") or {}
            mcc_id = platform_metadata.get("mcc_id")
            
            connector = GoogleAdsConnector(
                access_token=access_token,
                refresh_token=refresh_token,
                customer_id=account["platform_account_id"],
                login_customer_id=mcc_id,  # Use MCC for authentication if available
            )
            
            # Fetch campaign-level metrics
            metrics = await connector.get_metrics(
                date_from=sync_date_from,
                date_to=sync_date_to,
                level="campaign",
            )
            
            if metrics:
                records_synced = await _save_metrics(supabase, account["id"], metrics)
                logger.info(f"Saved {records_synced} metric records for account {account['id']}")
            else:
                logger.warning(f"No metrics returned for account {account['id']}")
            
        elif platform == "meta_ads":
            # TODO: Implement Meta Ads connector
            logger.info(f"Meta Ads sync not yet implemented for account {account['id']}")
        
        else:
            logger.warning(f"Unknown platform: {platform}")
        
        # Update job as completed
        await supabase.update_sync_job(job_id, {
            "status": "completed",
            "completed_at": "now()",
            "records_synced": records_synced,
            "date_from": sync_date_from.isoformat(),
            "date_to": sync_date_to.isoformat(),
        })
        
        # Update account last sync
        await supabase.update_connected_account(account["id"], {
            "last_sync_at": "now()",
            "last_sync_status": "completed",
        })
        
        logger.info(f"Sync completed for account {account['id']}: {records_synced} records")
        
    except Exception as e:
        logger.error(f"Sync failed for job {job_id}: {e}", exc_info=True)
        
        await supabase.update_sync_job(job_id, {
            "status": "failed",
            "error_message": str(e),
        })
        
        # Retry
        raise task.retry(exc=e)


@celery_app.task(name="app.tasks.sync_tasks.sync_all_accounts")
def sync_all_accounts():
    """
    Sync all active connected accounts.
    
    Scheduled to run daily at 6 AM.
    """
    import asyncio
    asyncio.run(_sync_all_accounts_async())


async def _sync_all_accounts_async():
    """Async implementation of sync_all_accounts."""
    supabase = get_supabase_service()
    
    # Get all active accounts
    result = supabase.client.table("connected_accounts") \
        .select("id") \
        .eq("is_active", True) \
        .eq("status", "active") \
        .execute()
    
    accounts = result.data or []
    logger.info(f"Starting daily sync for {len(accounts)} accounts")
    
    for account in accounts:
        try:
            # Create sync job
            job = await supabase.create_sync_job({
                "account_id": account["id"],
                "job_type": "daily_sync",
                "status": "pending",
            })
            
            # Queue the sync task
            sync_account_metrics.delay(job["id"])
            
        except Exception as e:
            logger.error(f"Failed to queue sync for account {account['id']}: {e}")
    
    logger.info("Daily sync jobs queued")


async def _save_metrics(
    supabase,
    account_id: str,
    metrics: list[dict],
) -> int:
    """
    Save normalized metrics to database.
    
    Args:
        supabase: Supabase service
        account_id: Connected account ID
        metrics: List of normalized metric records from connector
        
    Returns:
        Number of records saved
    """
    if not metrics:
        return 0
    
    # Format records for Supabase's actual schema
    # Converts from connector format (micros) to database format (decimals)
    records = []
    for m in metrics:
        records.append({
            'account_id': account_id,
            'date': m['date'],
            'platform': m.get('platform', 'google_ads'),
            'entity_type': 'campaign',
            'entity_id': m.get('campaign_id'),
            'entity_name': m.get('campaign_name'),
            'impressions': m['impressions'],
            'clicks': m['clicks'],
            'spend': m['spend_micros'] / 1_000_000,  # Convert from micros
            'conversions': float(m['conversions']),
            'conversion_value': m['conversion_value_micros'] / 1_000_000,
            'currency': m['currency'],
            # Note: ctr, cpc, cpm, roas, cpa are generated columns in Supabase
        })
    
    # Upsert metrics
    result = await supabase.upsert_daily_metrics(records)
    return len(result) if result else 0

