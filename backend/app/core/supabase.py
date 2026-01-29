"""
Ad Platform MVP - Supabase Client

Supabase client initialization for backend operations.
Uses service_role key which bypasses RLS for admin operations.
"""

from functools import lru_cache
from typing import Optional

from supabase import create_client, Client

from app.core.config import settings


@lru_cache
def get_supabase_client() -> Client:
    """
    Get cached Supabase client instance.
    
    Uses service_role key for backend operations.
    This bypasses Row Level Security - use carefully!
    
    Returns:
        Supabase client instance
    """
    return create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_service_role_key,
    )


class SupabaseService:
    """
    Service wrapper for Supabase operations.
    
    Provides typed methods for common database operations.
    """

    def __init__(self, client: Optional[Client] = None):
        self._client = client or get_supabase_client()

    @property
    def client(self) -> Client:
        """Get the Supabase client."""
        return self._client

    # ===========================================
    # ORGANIZATION OPERATIONS
    # ===========================================

    async def get_organization(self, org_id: str) -> Optional[dict]:
        """Get organization by ID."""
        result = self._client.table("organizations") \
            .select("*") \
            .eq("id", org_id) \
            .limit(1) \
            .execute()
        return result.data[0] if result.data else None

    async def get_organization_by_slug(self, slug: str) -> Optional[dict]:
        """Get organization by slug."""
        result = self._client.table("organizations") \
            .select("*") \
            .eq("slug", slug) \
            .limit(1) \
            .execute()
        return result.data[0] if result.data else None

    # ===========================================
    # USER OPERATIONS
    # ===========================================

    async def get_user(self, user_id: str) -> Optional[dict]:
        """Get user by ID. Returns None if not found (no PGRST116 error)."""
        result = self._client.table("users") \
            .select("*, organizations(*)") \
            .eq("id", user_id) \
            .limit(1) \
            .execute()
        return result.data[0] if result.data else None

    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get user by email. Returns None if not found."""
        result = self._client.table("users") \
            .select("*, organizations(*)") \
            .eq("email", email) \
            .limit(1) \
            .execute()
        return result.data[0] if result.data else None

    async def update_user_last_seen(self, user_id: str) -> None:
        """Update user's last_seen_at timestamp."""
        self._client.table("users") \
            .update({"last_seen_at": "now()"}) \
            .eq("id", user_id) \
            .execute()

    # ===========================================
    # CONNECTED ACCOUNTS OPERATIONS
    # ===========================================

    async def get_connected_accounts(
        self,
        org_id: str,
        platform: Optional[str] = None,
        is_active: bool = True
    ) -> list[dict]:
        """Get connected accounts for an organization."""
        query = self._client.table("connected_accounts") \
            .select("*") \
            .eq("org_id", org_id) \
            .eq("is_active", is_active)
        
        if platform:
            query = query.eq("platform", platform)
        
        result = query.execute()
        return result.data

    async def get_connected_account(self, account_id: str) -> Optional[dict]:
        """Get a specific connected account. Returns None if not found."""
        result = self._client.table("connected_accounts") \
            .select("*") \
            .eq("id", account_id) \
            .limit(1) \
            .execute()
        return result.data[0] if result.data else None

    async def create_connected_account(self, data: dict) -> dict:
        """Create a new connected account."""
        result = self._client.table("connected_accounts") \
            .insert(data) \
            .execute()
        return result.data[0]

    async def update_connected_account(self, account_id: str, data: dict) -> dict:
        """Update a connected account."""
        result = self._client.table("connected_accounts") \
            .update(data) \
            .eq("id", account_id) \
            .execute()
        return result.data[0]

    async def deactivate_connected_account(self, account_id: str) -> None:
        """Soft delete a connected account."""
        self._client.table("connected_accounts") \
            .update({"is_active": False, "status": "disconnected"}) \
            .eq("id", account_id) \
            .execute()

    # ===========================================
    # CAMPAIGNS OPERATIONS
    # ===========================================

    async def get_campaigns(
        self,
        account_id: str,
        is_active: bool = True
    ) -> list[dict]:
        """Get campaigns for an account."""
        result = self._client.table("campaigns") \
            .select("*") \
            .eq("account_id", account_id) \
            .eq("is_active", is_active) \
            .execute()
        return result.data

    async def upsert_campaign(self, data: dict) -> dict:
        """Upsert a campaign (insert or update)."""
        result = self._client.table("campaigns") \
            .upsert(data, on_conflict="account_id,platform_campaign_id") \
            .execute()
        return result.data[0]

    # ===========================================
    # METRICS OPERATIONS
    # ===========================================

    async def upsert_daily_metrics(self, records: list[dict]) -> list[dict]:
        """Bulk upsert daily metrics."""
        result = self._client.table("daily_metrics") \
            .upsert(
                records,
                on_conflict="account_id,campaign_id,ad_set_id,date"
            ) \
            .execute()
        return result.data

    async def get_daily_metrics(
        self,
        org_id: str,
        date_from: str,
        date_to: str,
        account_id: Optional[str] = None,
        campaign_id: Optional[str] = None
    ) -> list[dict]:
        """Get daily metrics with filters."""
        # First get connected accounts for the org
        accounts = await self.get_connected_accounts(org_id)
        account_ids = [a["id"] for a in accounts]
        
        if not account_ids:
            return []
        
        query = self._client.table("daily_metrics") \
            .select("*, campaigns(*)") \
            .in_("account_id", account_ids) \
            .gte("date", date_from) \
            .lte("date", date_to)
        
        if account_id:
            query = query.eq("account_id", account_id)
        
        if campaign_id:
            query = query.eq("campaign_id", campaign_id)
        
        result = query.order("date", desc=True).execute()
        return result.data

    # ===========================================
    # INSIGHTS OPERATIONS
    # ===========================================

    async def create_insight(self, data: dict) -> dict:
        """Create a new insight."""
        result = self._client.table("insights") \
            .insert(data) \
            .execute()
        return result.data[0]

    async def get_insights(
        self,
        org_id: str,
        is_read: Optional[bool] = None,
        limit: int = 20
    ) -> list[dict]:
        """Get insights for an organization."""
        query = self._client.table("insights") \
            .select("*, recommended_actions(*)") \
            .eq("org_id", org_id) \
            .eq("is_dismissed", False)
        
        if is_read is not None:
            query = query.eq("is_read", is_read)
        
        result = query \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        return result.data

    async def mark_insight_read(self, insight_id: str) -> None:
        """Mark an insight as read."""
        self._client.table("insights") \
            .update({"is_read": True, "read_at": "now()"}) \
            .eq("id", insight_id) \
            .execute()

    # ===========================================
    # SYNC JOBS OPERATIONS
    # ===========================================

    async def create_sync_job(self, data: dict) -> dict:
        """Create a new sync job."""
        result = self._client.table("sync_jobs") \
            .insert(data) \
            .execute()
        return result.data[0]

    async def update_sync_job(self, job_id: str, data: dict) -> dict:
        """Update sync job status."""
        result = self._client.table("sync_jobs") \
            .update(data) \
            .eq("id", job_id) \
            .execute()
        return result.data[0]

    async def get_latest_sync_job(self, account_id: str) -> Optional[dict]:
        """Get the latest sync job for an account."""
        result = self._client.table("sync_jobs") \
            .select("*") \
            .eq("account_id", account_id) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
        return result.data[0] if result.data else None


# Convenience function for dependency injection
def get_supabase_service() -> SupabaseService:
    """Get SupabaseService instance for dependency injection."""
    return SupabaseService()
