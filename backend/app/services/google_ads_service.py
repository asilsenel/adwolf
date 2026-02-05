"""
Ad Platform MVP - Google Ads Service

Service for fetching data from Google Ads API.
"""

from datetime import datetime, timedelta
from typing import Optional
import httpx

from app.core.config import settings
from app.core.security import decrypt_token
from app.core.supabase import get_supabase_service


class GoogleAdsService:
    """
    Service for interacting with Google Ads API.
    
    Uses REST API for simplicity in MVP phase.
    For production, consider using the official google-ads library.
    """
    
    GOOGLE_ADS_API_VERSION = "v15"
    GOOGLE_ADS_BASE_URL = f"https://googleads.googleapis.com/{GOOGLE_ADS_API_VERSION}"
    
    def __init__(self, access_token: str, developer_token: str):
        self.access_token = access_token
        self.developer_token = developer_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "developer-token": developer_token,
            "Content-Type": "application/json",
        }
    
    async def list_accessible_customers(self) -> list[str]:
        """Get list of accessible customer IDs."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.GOOGLE_ADS_BASE_URL}/customers:listAccessibleCustomers",
                headers=self.headers,
            )
            
            if response.status_code == 200:
                data = response.json()
                return [rn.split("/")[-1] for rn in data.get("resourceNames", [])]
            else:
                print(f"Failed to list customers: {response.text}")
                return []
    
    async def get_account_metrics(
        self,
        customer_id: str,
        date_from: str,
        date_to: str,
    ) -> dict:
        """
        Fetch account-level metrics for a date range.
        
        Returns aggregated metrics: impressions, clicks, cost, conversions.
        """
        # GAQL query for account metrics
        query = f"""
            SELECT
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                segments.date
            FROM customer
            WHERE segments.date >= '{date_from}'
                AND segments.date <= '{date_to}'
        """
        
        return await self._execute_query(customer_id, query)
    
    async def _execute_query(self, customer_id: str, query: str) -> dict:
        """Execute a GAQL query."""
        url = f"{self.GOOGLE_ADS_BASE_URL}/customers/{customer_id}/googleAds:searchStream"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=self.headers,
                json={"query": query},
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Query failed: {response.text}")
                return {"error": response.text}


async def sync_account_metrics(account_id: str, date_from: str, date_to: str) -> dict:
    """
    Sync metrics for a connected Google Ads account.

    Uses GoogleAdsConnector (google-ads library) for reliable API access.
    Fetches campaign-level metrics and stores in database.
    """
    import logging
    from datetime import datetime
    from app.connectors.google_ads import GoogleAdsConnector

    logger = logging.getLogger(__name__)
    logger.info(f"=== SYNC STARTED for account {account_id} ===")
    logger.info(f"Date range: {date_from} to {date_to}")

    supabase = get_supabase_service()

    # Get account with encrypted tokens
    account = await supabase.get_connected_account(account_id)
    if not account:
        logger.error("Account not found!")
        return {"success": False, "error": "Account not found"}

    logger.info(f"Account found: {account.get('platform_account_id')}")

    if account["platform"] != "google_ads":
        logger.error("Not a Google Ads account")
        return {"success": False, "error": "Not a Google Ads account"}

    # Check if developer token is configured
    dev_token = settings.google_ads_developer_token
    logger.info(f"Developer token configured: {bool(dev_token and dev_token != 'placeholder')}")

    if not dev_token or dev_token == "placeholder":
        logger.info("No developer token, generating demo data...")
        return await generate_and_store_demo_metrics(account_id, date_from, date_to)

    # Decrypt tokens
    try:
        access_token = decrypt_token(account["access_token_encrypted"])
        refresh_token = None
        if account.get("refresh_token_encrypted"):
            refresh_token = decrypt_token(account["refresh_token_encrypted"])
        logger.info("Tokens decrypted successfully")
    except Exception as e:
        logger.error(f"Failed to decrypt tokens: {e}")
        logger.info("Falling back to demo data...")
        return await generate_and_store_demo_metrics(account_id, date_from, date_to)

    # Get MCC ID from platform_metadata
    mcc_id = account.get("platform_metadata", {}).get("mcc_id")
    customer_id = account.get("platform_account_id")

    logger.info(f"Customer ID: {customer_id}, MCC ID: {mcc_id}")

    try:
        # Use GoogleAdsConnector (google-ads library) for reliable API access
        connector = GoogleAdsConnector(
            access_token=access_token,
            refresh_token=refresh_token,
            customer_id=customer_id,
            login_customer_id=mcc_id,
        )

        # Validate connection
        is_valid = await connector.validate_connection()
        if not is_valid:
            logger.warning("Connection validation failed, using demo data")
            return await generate_and_store_demo_metrics(account_id, date_from, date_to)

        # Parse dates
        start_date = datetime.strptime(date_from, "%Y-%m-%d").date()
        end_date = datetime.strptime(date_to, "%Y-%m-%d").date()

        # Fetch and store campaigns first
        campaigns = await connector.get_campaigns(account_id=customer_id)
        logger.info(f"Fetched {len(campaigns)} campaigns from Google Ads API")

        # Store campaigns in database
        for campaign in campaigns:
            try:
                # Convert micros to actual currency
                daily_budget = None
                if campaign.get("daily_budget_micros"):
                    daily_budget = campaign["daily_budget_micros"] / 1_000_000

                await supabase.upsert_campaign({
                    "account_id": account_id,
                    "platform_campaign_id": campaign["id"],
                    "platform": "google_ads",
                    "name": campaign["name"],
                    "status": campaign["status"],
                    "campaign_type": campaign.get("channel_type", "unknown"),
                    "daily_budget": daily_budget,
                    "budget_currency": "TRY",
                })
            except Exception as e:
                logger.warning(f"Failed to upsert campaign {campaign['id']}: {e}")

        # Fetch campaign-level metrics using the connector
        metrics = await connector.get_metrics(
            date_from=start_date,
            date_to=end_date,
            level="campaign",
            account_id=customer_id,
        )

        logger.info(f"Fetched {len(metrics)} metric records from Google Ads API")

        if not metrics:
            logger.warning("No metrics returned from API")
            return {
                "success": True,
                "customer_id": customer_id,
                "records_count": 0,
                "message": "No metrics data available for this date range"
            }

        # Convert connector metrics to database format
        # Note: ctr, cpc, cpm, roas, cpa are generated columns in database - don't include them
        records = []
        for m in metrics:
            records.append({
                "account_id": account_id,
                "date": m["date"],
                "entity_type": m.get("entity_type", "campaign"),
                "entity_id": m.get("campaign_id") or m.get("entity_id"),
                "entity_name": m.get("campaign_name") or m.get("entity_name"),
                "platform": "google_ads",
                "impressions": m.get("impressions", 0),
                "clicks": m.get("clicks", 0),
                "spend": m.get("spend", 0),
                "conversions": m.get("conversions", 0),
                "conversion_value": m.get("conversion_value", 0),
                "currency": m.get("currency", "TRY"),
                # ctr, cpc, cpm, roas, cpa are generated columns - database calculates them automatically
            })

        # Store in database
        if records:
            await supabase.upsert_daily_metrics(records)
            logger.info(f"Stored {len(records)} metric records in database")

        return {
            "success": True,
            "customer_id": customer_id,
            "records_count": len(records),
        }

    except Exception as e:
        logger.error(f"Error syncing from Google Ads: {e}", exc_info=True)
        logger.info("Falling back to demo data...")
        return await generate_and_store_demo_metrics(account_id, date_from, date_to)


def parse_google_ads_response(account_id: str, api_response: dict) -> list[dict]:
    """Parse Google Ads API response into daily_metrics records."""
    records = []

    # Google Ads API returns data in batches
    for batch in api_response.get("results", [api_response]):
        results = batch.get("results", [])
        for row in results:
            metrics = row.get("metrics", {})
            segments = row.get("segments", {})

            # Convert micros to actual currency (database stores in TRY, not micros)
            cost_micros = metrics.get("costMicros", 0)
            spend = cost_micros / 1_000_000 if cost_micros else 0

            record = {
                "account_id": account_id,
                "date": segments.get("date"),
                "entity_type": "account",
                "entity_id": account_id,
                "platform": "google_ads",
                "impressions": metrics.get("impressions", 0),
                "clicks": metrics.get("clicks", 0),
                "spend": spend,  # Database uses 'spend' column (numeric)
                "conversions": float(metrics.get("conversions", 0)),
                "conversion_value": 0,  # Database uses 'conversion_value' column
                "currency": "TRY",
            }
            records.append(record)

    return records


async def generate_and_store_demo_metrics(account_id: str, date_from: str, date_to: str) -> dict:
    """Generate demo metrics for testing when API is not available."""
    from random import randint, uniform
    from datetime import datetime, timedelta

    supabase = get_supabase_service()

    # Parse dates
    start = datetime.strptime(date_from, "%Y-%m-%d")
    end = datetime.strptime(date_to, "%Y-%m-%d")

    records = []
    current = start

    while current <= end:
        # Generate realistic-looking demo data
        impressions = randint(1000, 15000)
        clicks = randint(int(impressions * 0.02), int(impressions * 0.05))
        spend = round(uniform(50, 500), 2)  # 50-500 TRY (database stores in currency, not micros)
        conversions = round(uniform(0, clicks * 0.1), 2)

        records.append({
            "account_id": account_id,
            "platform": "google_ads",
            "date": current.strftime("%Y-%m-%d"),
            "entity_type": "account",
            "entity_id": account_id,
            "impressions": impressions,
            "clicks": clicks,
            "spend": spend,  # Database uses 'spend' column (numeric in TRY)
            "conversions": conversions,
            "conversion_value": 0,  # Database uses 'conversion_value' column
            "currency": "TRY",
        })

        current += timedelta(days=1)

    # Store in database
    try:
        await supabase.upsert_daily_metrics(records)
        print(f"Stored {len(records)} demo metric records")

        return {
            "success": True,
            "records_count": len(records),
            "demo_mode": True,
        }
    except Exception as e:
        print(f"Failed to store demo metrics: {e}")
        return {"success": False, "error": str(e)}
