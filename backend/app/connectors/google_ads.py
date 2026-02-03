"""
Ad Platform MVP - Google Ads Connector

Read-only connector for fetching Google Ads metrics.
Uses google-ads Python library.
"""

import logging
from datetime import date, timedelta
from typing import Optional

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.protobuf import json_format

from app.connectors.base import BaseConnector
from app.models.account import Platform
from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleAdsConnector(BaseConnector):
    """
    Read-only connector for Google Ads.
    
    Fetches campaign metrics, ad group data, and performance statistics.
    Does NOT support editing campaigns (viewer-only mode).
    """

    platform = Platform.GOOGLE_ADS

    def __init__(
        self,
        access_token: str,
        refresh_token: str,
        customer_id: str,
        login_customer_id: Optional[str] = None,
    ):
        """
        Initialize Google Ads connector.
        
        Args:
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            customer_id: Google Ads customer ID (without dashes)
            login_customer_id: MCC account ID if using manager account
        """
        super().__init__(access_token, refresh_token, customer_id)
        self.customer_id = customer_id.replace("-", "")
        self.login_customer_id = login_customer_id.replace("-", "") if login_customer_id else None
        self._client = None

    def _get_client(self) -> GoogleAdsClient:
        """Get or create Google Ads API client."""
        if self._client is None:
            credentials = {
                "developer_token": settings.google_ads_developer_token,
                "client_id": settings.google_ads_client_id,
                "client_secret": settings.google_ads_client_secret,
                "refresh_token": self.refresh_token,
                "use_proto_plus": True,
            }
            
            if self.login_customer_id:
                credentials["login_customer_id"] = self.login_customer_id
            
            self._client = GoogleAdsClient.load_from_dict(credentials)
        
        return self._client

    async def validate_connection(self) -> bool:
        """Validate that the connection is working."""
        try:
            client = self._get_client()
            ga_service = client.get_service("GoogleAdsService")
            
            # Simple query to test connection
            query = """
                SELECT customer.id, customer.descriptive_name
                FROM customer
                LIMIT 1
            """
            
            response = ga_service.search(
                customer_id=self.customer_id,
                query=query,
            )
            
            for row in response:
                logger.info(f"Connected to Google Ads: {row.customer.descriptive_name}")
                return True
            
            return True
        except GoogleAdsException as ex:
            logger.error(f"Google Ads validation failed: {ex.failure.errors}")
            return False
        except Exception as e:
            logger.error(f"Connection validation error: {e}")
            return False

    async def refresh_access_token(self) -> tuple[str, Optional[str], int]:
        """
        Refresh access token using refresh token.
        
        Note: google-ads library handles this automatically,
        but we implement for interface compliance.
        """
        # The library handles refresh internally
        # Return existing tokens - they'll be refreshed on next API call
        return self.access_token, self.refresh_token, 3600

    async def get_account_info(self) -> dict:
        """Get account name and details from Google Ads."""
        try:
            client = self._get_client()
            ga_service = client.get_service("GoogleAdsService")
            
            query = """
                SELECT 
                    customer.id,
                    customer.descriptive_name,
                    customer.currency_code,
                    customer.time_zone
                FROM customer
                LIMIT 1
            """
            
            response = ga_service.search(
                customer_id=self.customer_id,
                query=query,
            )
            
            for row in response:
                return {
                    "id": str(row.customer.id),
                    "name": row.customer.descriptive_name,
                    "currency": row.customer.currency_code,
                    "timezone": row.customer.time_zone,
                }
            
            return {"id": self.customer_id, "name": f"Google Ads - {self.customer_id}"}
            
        except GoogleAdsException as ex:
            logger.error(f"Failed to get account info: {ex.failure.errors}")
            return {"id": self.customer_id, "name": f"Google Ads - {self.customer_id}"}
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {"id": self.customer_id, "name": f"Google Ads - {self.customer_id}"}

    async def get_ad_accounts(self) -> list[dict]:
        """Get accessible Google Ads accounts (sub-accounts of the MCC)."""
        try:
            client = self._get_client()
            ga_service = client.get_service("GoogleAdsService")
            
            # If we are an MCC (have login_customer_id), we should query the hierarchy
            # If not, we fall back to listing accessible customers
            
            target_id = self.login_customer_id or self.customer_id
            
            # Query for sub-accounts
            # Relaxed filters to ensure we catch all accessible accounts
            query = """
                SELECT 
                    customer_client.id,
                    customer_client.descriptive_name,
                    customer_client.currency_code,
                    customer_client.time_zone,
                    customer_client.manager,
                    customer_client.status
                FROM customer_client
                WHERE customer_client.status != 'CANCELED'
            """
            
            response = ga_service.search(
                customer_id=target_id,
                query=query,
            )
            
            accounts = []
            for row in response:
                # Skip the manager account itself if it appears in the list
                if row.customer_client.id == int(target_id):
                    continue
                    
                accounts.append({
                    "id": str(row.customer_client.id),
                    "platform": "google_ads",
                    "name": row.customer_client.descriptive_name or f"Account {row.customer_client.id}",
                    "currency": row.customer_client.currency_code,
                    "timezone": row.customer_client.time_zone,
                    "is_manager": row.customer_client.manager,
                })
            
            logger.info(f"Found {len(accounts)} sub-accounts for MCC {target_id}")
            return accounts
            
        except GoogleAdsException as ex:
            logger.error(f"Failed to get ad accounts: {ex.failure.errors}")
            return []
        except Exception as e:
            logger.error(f"Error getting ad accounts: {e}")
            return []

    async def get_campaigns(self, account_id: Optional[str] = None) -> list[dict]:
        """Get campaigns for the account."""
        try:
            client = self._get_client()
            ga_service = client.get_service("GoogleAdsService")
            
            customer = account_id or self.customer_id
            
            query = """
                SELECT
                    campaign.id,
                    campaign.name,
                    campaign.status,
                    campaign.advertising_channel_type,
                    campaign_budget.amount_micros
                FROM campaign
                WHERE campaign.status != 'REMOVED'
                ORDER BY campaign.name
            """
            
            response = ga_service.search(customer_id=customer, query=query)
            
            campaigns = []
            for row in response:
                campaigns.append({
                    "id": str(row.campaign.id),
                    "platform_id": str(row.campaign.id),
                    "name": row.campaign.name,
                    "status": row.campaign.status.name.lower(),
                    "channel_type": row.campaign.advertising_channel_type.name,
                    "daily_budget_micros": row.campaign_budget.amount_micros,
                })
            
            logger.info(f"Found {len(campaigns)} campaigns for customer {customer}")
            return campaigns
            
        except GoogleAdsException as ex:
            logger.error(f"Failed to get campaigns: {ex.failure.errors}")
            return []
        except Exception as e:
            logger.error(f"Error getting campaigns: {e}")
            return []

    async def get_ad_sets(
        self,
        campaign_id: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> list[dict]:
        """Get ad groups for campaigns."""
        try:
            client = self._get_client()
            ga_service = client.get_service("GoogleAdsService")
            
            customer = account_id or self.customer_id
            
            query = """
                SELECT
                    ad_group.id,
                    ad_group.name,
                    ad_group.status,
                    ad_group.campaign,
                    campaign.name
                FROM ad_group
                WHERE ad_group.status != 'REMOVED'
            """
            
            if campaign_id:
                query += f" AND campaign.id = {campaign_id}"
            
            query += " ORDER BY ad_group.name"
            
            response = ga_service.search(customer_id=customer, query=query)
            
            ad_groups = []
            for row in response:
                ad_groups.append({
                    "id": str(row.ad_group.id),
                    "platform_id": str(row.ad_group.id),
                    "name": row.ad_group.name,
                    "status": row.ad_group.status.name.lower(),
                    "campaign_id": row.ad_group.campaign.split("/")[-1],
                    "campaign_name": row.campaign.name,
                })
            
            return ad_groups
            
        except GoogleAdsException as ex:
            logger.error(f"Failed to get ad groups: {ex.failure.errors}")
            return []
        except Exception as e:
            logger.error(f"Error getting ad groups: {e}")
            return []

    async def get_metrics(
        self,
        date_from: date,
        date_to: date,
        level: str = "campaign",
        account_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
    ) -> list[dict]:
        """
        Get performance metrics for a date range.
        
        Args:
            date_from: Start date
            date_to: End date
            level: Aggregation level (account, campaign, ad_group)
            account_id: Customer ID
            campaign_id: Filter by specific campaign
            
        Returns:
            List of normalized metric records
        """
        try:
            client = self._get_client()
            ga_service = client.get_service("GoogleAdsService")
            
            customer = account_id or self.customer_id
            
            # Build query based on level
            if level == "account":
                query = self._build_account_metrics_query(date_from, date_to)
            elif level == "ad_group":
                query = self._build_ad_group_metrics_query(date_from, date_to, campaign_id)
            else:  # campaign (default)
                query = self._build_campaign_metrics_query(date_from, date_to, campaign_id)
            
            logger.info(f"Fetching {level} metrics for {customer} from {date_from} to {date_to}")
            
            response = ga_service.search(customer_id=customer, query=query)
            
            metrics = []
            for row in response:
                metric = self._parse_metrics_row(row, level)
                if metric:
                    metrics.append(metric)
            
            logger.info(f"Fetched {len(metrics)} metric records")
            return metrics
            
        except GoogleAdsException as ex:
            for error in ex.failure.errors:
                logger.error(f"Google Ads API error: {error.message}")
            return []
        except Exception as e:
            logger.error(f"Error getting metrics: {e}", exc_info=True)
            return []

    def _build_account_metrics_query(self, date_from: date, date_to: date) -> str:
        """Build query for account-level metrics."""
        return f"""
            SELECT
                segments.date,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                customer.currency_code
            FROM customer
            WHERE segments.date BETWEEN '{date_from.isoformat()}' AND '{date_to.isoformat()}'
            ORDER BY segments.date DESC
        """

    def _build_campaign_metrics_query(
        self, 
        date_from: date, 
        date_to: date,
        campaign_id: Optional[str] = None,
    ) -> str:
        """Build query for campaign-level metrics."""
        query = f"""
            SELECT
                segments.date,
                campaign.id,
                campaign.name,
                campaign.status,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                customer.currency_code
            FROM campaign
            WHERE segments.date BETWEEN '{date_from.isoformat()}' AND '{date_to.isoformat()}'
        """
        
        if campaign_id:
            query += f" AND campaign.id = {campaign_id}"
        
        query += " ORDER BY segments.date DESC, campaign.name"
        return query

    def _build_ad_group_metrics_query(
        self,
        date_from: date,
        date_to: date,
        campaign_id: Optional[str] = None,
    ) -> str:
        """Build query for ad group-level metrics."""
        query = f"""
            SELECT
                segments.date,
                campaign.id,
                campaign.name,
                ad_group.id,
                ad_group.name,
                ad_group.status,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                customer.currency_code
            FROM ad_group
            WHERE segments.date BETWEEN '{date_from.isoformat()}' AND '{date_to.isoformat()}'
        """
        
        if campaign_id:
            query += f" AND campaign.id = {campaign_id}"
        
        query += " ORDER BY segments.date DESC, ad_group.name"
        return query

    def _parse_metrics_row(self, row, level: str) -> Optional[dict]:
        """Parse a metrics row into normalized format."""
        try:
            # Convert micros to actual currency (database stores in TRY, not micros)
            spend = row.metrics.cost_micros / 1_000_000 if row.metrics.cost_micros else 0
            conversion_value = row.metrics.conversions_value if row.metrics.conversions_value else 0

            base_metrics = {
                "date": str(row.segments.date),
                "platform": "google_ads",
                "impressions": row.metrics.impressions,
                "clicks": row.metrics.clicks,
                "spend": spend,  # Database uses 'spend' column (numeric in TRY)
                "conversions": int(row.metrics.conversions),
                "conversion_value": conversion_value,  # Database uses 'conversion_value' column
                "currency": row.customer.currency_code,
            }

            # Add CTR, CPC, etc.
            if base_metrics["impressions"] > 0:
                base_metrics["ctr"] = base_metrics["clicks"] / base_metrics["impressions"]
            else:
                base_metrics["ctr"] = 0.0

            if base_metrics["clicks"] > 0:
                base_metrics["cpc"] = base_metrics["spend"] / base_metrics["clicks"]
            else:
                base_metrics["cpc"] = 0

            if base_metrics["impressions"] > 0:
                base_metrics["cpm"] = (base_metrics["spend"] / base_metrics["impressions"]) * 1000
            else:
                base_metrics["cpm"] = 0

            if base_metrics["spend"] > 0 and base_metrics["conversion_value"] > 0:
                base_metrics["roas"] = base_metrics["conversion_value"] / base_metrics["spend"]
            else:
                base_metrics["roas"] = 0.0

            if base_metrics["conversions"] > 0:
                base_metrics["cpa"] = base_metrics["spend"] / base_metrics["conversions"]
            else:
                base_metrics["cpa"] = 0

            # Add level-specific fields
            if level == "campaign":
                base_metrics["entity_type"] = "campaign"
                base_metrics["entity_id"] = str(row.campaign.id)
                base_metrics["entity_name"] = row.campaign.name
                base_metrics["campaign_id"] = str(row.campaign.id)
                base_metrics["campaign_name"] = row.campaign.name
                base_metrics["campaign_status"] = row.campaign.status.name.lower()
            elif level == "ad_group":
                base_metrics["entity_type"] = "ad_group"
                base_metrics["entity_id"] = str(row.ad_group.id)
                base_metrics["entity_name"] = row.ad_group.name
                base_metrics["campaign_id"] = str(row.campaign.id)
                base_metrics["campaign_name"] = row.campaign.name
                base_metrics["ad_set_id"] = str(row.ad_group.id)
                base_metrics["ad_set_name"] = row.ad_group.name
                base_metrics["ad_set_status"] = row.ad_group.status.name.lower()
            else:
                base_metrics["entity_type"] = "account"
                base_metrics["entity_id"] = self.customer_id

            return base_metrics

        except Exception as e:
            logger.error(f"Error parsing metrics row: {e}")
            return None

    # =========================================
    # READ-ONLY: These methods are not implemented
    # =========================================
    
    async def pause_campaign(self, campaign_id: str) -> bool:
        """Not implemented - read-only connector."""
        logger.warning("pause_campaign not implemented - read-only mode")
        return False

    async def enable_campaign(self, campaign_id: str) -> bool:
        """Not implemented - read-only connector."""
        logger.warning("enable_campaign not implemented - read-only mode")
        return False

    async def update_budget(
        self,
        campaign_id: str,
        daily_budget: float,
        currency: str = "TRY",
    ) -> bool:
        """Not implemented - read-only connector."""
        logger.warning("update_budget not implemented - read-only mode")
        return False
