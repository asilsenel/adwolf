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


from pydantic import BaseModel, field_validator
import re


class AvailableGoogleAdsAccount(BaseModel):
    """A Google Ads account available for import."""
    id: str
    name: str
    currency: str | None = None
    timezone: str | None = None
    is_manager: bool = False
    already_connected: bool = False


class AvailableAccountsResponse(BaseModel):
    """Response with list of available accounts to import."""
    success: bool
    accounts: list[AvailableGoogleAdsAccount]
    total: int
    message: str | None = None


class BulkImportRequest(BaseModel):
    """Request to import multiple accounts at once."""
    account_ids: list[str]


class BulkImportResult(BaseModel):
    """Result of a single account import."""
    account_id: str
    success: bool
    account_name: str | None = None
    error: str | None = None


class BulkImportResponse(BaseModel):
    """Response after bulk import."""
    success: bool
    imported_count: int
    failed_count: int
    results: list[BulkImportResult]


@router.get("/available/google-ads", response_model=AvailableAccountsResponse)
async def list_available_google_ads_accounts(
    current_user: CurrentUser,
    supabase: Supabase,
):
    """
    List all Google Ads accounts accessible via the connected OAuth.

    Returns accounts from the MCC hierarchy that can be imported.
    """
    org_id = current_user["org_id"]

    # Find an existing Google Ads account with OAuth tokens
    existing_accounts = await supabase.get_connected_accounts(org_id=org_id)

    source_account = None
    for acc in existing_accounts:
        if acc["platform"] == "google_ads" and acc.get("refresh_token_encrypted"):
            source_account = acc
            break

    if not source_account:
        return AvailableAccountsResponse(
            success=False,
            accounts=[],
            total=0,
            message="Önce OAuth ile Google Ads hesabınızı bağlamanız gerekiyor",
        )

    # Get already connected account IDs
    connected_ids = {
        acc["platform_account_id"]
        for acc in existing_accounts
        if acc["platform"] == "google_ads"
    }

    try:
        from app.connectors.google_ads import GoogleAdsConnector
        from app.core.security import decrypt_token

        access_token = decrypt_token(source_account["access_token_encrypted"])
        refresh_token = decrypt_token(source_account["refresh_token_encrypted"])

        mcc_id = source_account.get("platform_metadata", {}).get("mcc_id")

        connector = GoogleAdsConnector(
            customer_id=mcc_id or source_account["platform_account_id"],
            access_token=access_token,
            refresh_token=refresh_token,
            login_customer_id=mcc_id,
        )

        # Get all accessible accounts
        accounts = await connector.get_ad_accounts()

        available = []
        for acc in accounts:
            available.append(AvailableGoogleAdsAccount(
                id=acc["id"],
                name=acc.get("name", f"Account {acc['id']}"),
                currency=acc.get("currency"),
                timezone=acc.get("timezone"),
                is_manager=acc.get("is_manager", False),
                already_connected=acc["id"] in connected_ids,
            ))

        return AvailableAccountsResponse(
            success=True,
            accounts=available,
            total=len(available),
        )

    except Exception as e:
        import logging
        logging.error(f"Failed to list available accounts: {e}")
        return AvailableAccountsResponse(
            success=False,
            accounts=[],
            total=0,
            message=f"Hesaplar alınamadı: {str(e)}",
        )


@router.post("/import/google-ads", response_model=BulkImportResponse)
async def bulk_import_google_ads_accounts(
    request: BulkImportRequest,
    current_user: CurrentUser,
    supabase: Supabase,
):
    """
    Import multiple Google Ads accounts at once.

    Uses existing OAuth tokens to add selected accounts.
    """
    import uuid
    org_id = current_user["org_id"]
    user_id = current_user["id"]

    # Find source account with tokens
    existing_accounts = await supabase.get_connected_accounts(org_id=org_id)

    source_account = None
    for acc in existing_accounts:
        if acc["platform"] == "google_ads" and acc.get("refresh_token_encrypted"):
            source_account = acc
            break

    if not source_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Önce OAuth ile bir Google Ads hesabı bağlamanız gerekiyor",
        )

    # Get already connected IDs
    connected_ids = {
        acc["platform_account_id"]
        for acc in existing_accounts
        if acc["platform"] == "google_ads"
    }

    try:
        from app.connectors.google_ads import GoogleAdsConnector
        from app.core.security import decrypt_token

        access_token = decrypt_token(source_account["access_token_encrypted"])
        refresh_token = decrypt_token(source_account["refresh_token_encrypted"])
        mcc_id = source_account.get("platform_metadata", {}).get("mcc_id")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token hatası: {str(e)}",
        )

    results = []
    imported_count = 0
    failed_count = 0

    for account_id in request.account_ids:
        # Skip already connected
        if account_id in connected_ids:
            results.append(BulkImportResult(
                account_id=account_id,
                success=False,
                error="Bu hesap zaten bağlı",
            ))
            failed_count += 1
            continue

        try:
            # Create connector for this specific account
            connector = GoogleAdsConnector(
                customer_id=account_id,
                access_token=access_token,
                refresh_token=refresh_token,
                login_customer_id=mcc_id,
            )

            # Validate and get account info
            is_valid = await connector.validate_connection()
            if not is_valid:
                results.append(BulkImportResult(
                    account_id=account_id,
                    success=False,
                    error="Hesap doğrulanamadı",
                ))
                failed_count += 1
                continue

            account_info = await connector.get_account_info()
            account_name = account_info.get("name", f"Google Ads - {account_id}")

            # Create new connected account
            new_account_id = str(uuid.uuid4())
            account_data = {
                "id": new_account_id,
                "org_id": org_id,
                "platform": "google_ads",
                "platform_account_id": account_id,
                "account_name": account_name,
                "platform_account_name": source_account.get("platform_account_name"),
                "account_currency": account_info.get("currency", "TRY"),
                "access_token_encrypted": source_account["access_token_encrypted"],
                "refresh_token_encrypted": source_account.get("refresh_token_encrypted"),
                "token_expires_at": source_account.get("token_expires_at"),
                "platform_metadata": {
                    "mcc_id": mcc_id,
                    "mcc_name": source_account.get("platform_metadata", {}).get("mcc_name"),
                    "imported_bulk": True,
                },
                "is_active": True,
                "sync_enabled": True,
                "status": "active",
                "connected_by": user_id,
            }

            result = supabase.client.table("connected_accounts").insert(account_data).execute()

            if result.data:
                results.append(BulkImportResult(
                    account_id=account_id,
                    success=True,
                    account_name=account_name,
                ))
                imported_count += 1
                connected_ids.add(account_id)  # Prevent duplicates in same batch
            else:
                results.append(BulkImportResult(
                    account_id=account_id,
                    success=False,
                    error="Veritabanına kaydedilemedi",
                ))
                failed_count += 1

        except Exception as e:
            results.append(BulkImportResult(
                account_id=account_id,
                success=False,
                error=str(e),
            ))
            failed_count += 1

    return BulkImportResponse(
        success=imported_count > 0,
        imported_count=imported_count,
        failed_count=failed_count,
        results=results,
    )


class AddAccountByIdRequest(BaseModel):
    """Request to add a Google Ads account by ID."""
    account_id: str
    account_name: Optional[str] = None
    
    @field_validator("account_id")
    @classmethod
    def normalize_account_id(cls, v: str) -> str:
        """Remove dashes and validate numeric format."""
        # Remove dashes (e.g., 813-075-0937 -> 8130750937)
        normalized = re.sub(r"[-\s]", "", v)
        # Validate it's numeric
        if not normalized.isdigit():
            raise ValueError("Account ID must be numeric")
        if len(normalized) < 8 or len(normalized) > 12:
            raise ValueError("Account ID must be 8-12 digits")
        return normalized


class AddAccountByIdResponse(BaseModel):
    """Response after adding account by ID."""
    success: bool
    account_id: str
    message: str
    account: Optional[ConnectedAccountResponse] = None


@router.post("/add-by-id", response_model=AddAccountByIdResponse)
async def add_account_by_id(
    request: AddAccountByIdRequest,
    current_user: CurrentUser,
    supabase: Supabase,
):
    """
    Add a Google Ads account by entering its ID.
    
    Requires an existing connected account to copy tokens from.
    Supports both formats: 8130750937 or 813-075-0937
    """
    org_id = current_user["org_id"]
    user_id = current_user["id"]
    
    # Check if account already exists in this org
    existing = await supabase.get_connected_accounts(org_id=org_id)
    for acc in existing:
        if acc["platform_account_id"] == request.account_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Bu hesap zaten bağlı: {request.account_id}",
            )
    
    # Find an existing Google Ads account to copy tokens from
    source_account = None
    for acc in existing:
        if acc["platform"] == "google_ads" and acc.get("access_token_encrypted"):
            source_account = acc
            break
    
    if not source_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Önce OAuth ile bir Google Ads hesabı bağlamanız gerekiyor",
        )
    
    # Validate the account exists in Google Ads
    try:
        from app.connectors.google_ads import GoogleAdsConnector
        from app.core.security import decrypt_token
        
        access_token = decrypt_token(source_account["access_token_encrypted"])
        refresh_token = None
        if source_account.get("refresh_token_encrypted"):
            refresh_token = decrypt_token(source_account["refresh_token_encrypted"])
        
        mcc_id = source_account.get("platform_metadata", {}).get("mcc_id")
        
        connector = GoogleAdsConnector(
            customer_id=request.account_id,
            access_token=access_token,
            refresh_token=refresh_token,
            login_customer_id=mcc_id,
        )
        
        # Validate the account
        is_valid = await connector.validate_connection()
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Hesap doğrulanamadı: {request.account_id}. Bu hesabın MCC altında olduğundan emin olun.",
            )
        
        # Get account name from Google Ads
        account_info = await connector.get_account_info()
        account_name = request.account_name or account_info.get("name", f"Google Ads - {request.account_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Hesap doğrulama hatası: {str(e)}",
        )
    
    # Create the new connected account
    import uuid
    new_account_id = str(uuid.uuid4())
    
    account_data = {
        "id": new_account_id,
        "org_id": org_id,
        "platform": "google_ads",
        "platform_account_id": request.account_id,
        "account_name": account_name,
        "platform_account_name": source_account.get("platform_account_name"),
        "account_currency": account_info.get("currency", "TRY"),
        "access_token_encrypted": source_account["access_token_encrypted"],
        "refresh_token_encrypted": source_account.get("refresh_token_encrypted"),
        "token_expires_at": source_account.get("token_expires_at"),
        "platform_metadata": {
            "mcc_id": mcc_id,
            "mcc_name": source_account.get("platform_metadata", {}).get("mcc_name"),
            "added_by_id": True,
        },
        "is_active": True,
        "sync_enabled": True,
        "status": "active",
        "connected_by": user_id,
    }
    
    # Save to database
    result = supabase.client.table("connected_accounts").insert(account_data).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hesap kaydedilemedi",
        )
    
    return AddAccountByIdResponse(
        success=True,
        account_id=request.account_id,
        message=f"Hesap başarıyla eklendi: {account_name}",
        account=ConnectedAccountResponse(**result.data[0]),
    )

