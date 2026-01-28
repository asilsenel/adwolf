"""
Ad Platform MVP - Base Connector

Abstract base class for platform connectors.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from app.models.account import Platform


class BaseConnector(ABC):
    """
    Abstract base class for ad platform connectors.
    
    All platform-specific connectors must inherit from this class
    and implement the required methods.
    """

    platform: Platform

    def __init__(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        account_id: Optional[str] = None,
    ):
        """
        Initialize connector with OAuth tokens.
        
        Args:
            access_token: OAuth access token
            refresh_token: OAuth refresh token (for token refresh)
            account_id: Platform-specific account ID
        """
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.account_id = account_id

    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        Validate that the connection is working.
        
        Returns:
            True if connection is valid, False otherwise
        """
        pass

    @abstractmethod
    async def refresh_access_token(self) -> tuple[str, Optional[str], int]:
        """
        Refresh the access token using refresh token.
        
        Returns:
            Tuple of (new_access_token, new_refresh_token, expires_in_seconds)
        """
        pass

    @abstractmethod
    async def get_ad_accounts(self) -> list[dict]:
        """
        Get list of accessible ad accounts.
        
        Returns:
            List of account dicts with id, name, etc.
        """
        pass

    @abstractmethod
    async def get_campaigns(self, account_id: Optional[str] = None) -> list[dict]:
        """
        Get campaigns for the account.
        
        Args:
            account_id: Specific account ID (if managing multiple)
            
        Returns:
            List of campaign dicts
        """
        pass

    @abstractmethod
    async def get_ad_sets(
        self,
        campaign_id: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> list[dict]:
        """
        Get ad sets/groups for campaigns.
        
        Args:
            campaign_id: Filter by specific campaign
            account_id: Filter by specific account
            
        Returns:
            List of ad set dicts
        """
        pass

    @abstractmethod
    async def get_metrics(
        self,
        date_from: date,
        date_to: date,
        level: str = "campaign",  # account, campaign, ad_set
        account_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
    ) -> list[dict]:
        """
        Get performance metrics for a date range.
        
        Args:
            date_from: Start date
            date_to: End date
            level: Aggregation level
            account_id: Filter by account
            campaign_id: Filter by campaign
            
        Returns:
            List of metric records with normalized fields
        """
        pass

    @abstractmethod
    async def pause_campaign(self, campaign_id: str) -> bool:
        """
        Pause a campaign.
        
        Args:
            campaign_id: Platform campaign ID
            
        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def enable_campaign(self, campaign_id: str) -> bool:
        """
        Enable/resume a paused campaign.
        
        Args:
            campaign_id: Platform campaign ID
            
        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def update_budget(
        self,
        campaign_id: str,
        daily_budget: float,
        currency: str = "TRY",
    ) -> bool:
        """
        Update campaign daily budget.
        
        Args:
            campaign_id: Platform campaign ID
            daily_budget: New daily budget amount
            currency: Budget currency
            
        Returns:
            True if successful
        """
        pass

    def normalize_metrics(self, raw_metrics: dict, source_date: date) -> dict:
        """
        Normalize platform-specific metrics to our schema.
        
        Override in subclasses for platform-specific normalization.
        
        Args:
            raw_metrics: Raw metrics from platform API
            source_date: Date of the metrics
            
        Returns:
            Normalized metrics dict
        """
        return {
            "date": source_date.isoformat(),
            "platform": self.platform.value,
            "impressions": raw_metrics.get("impressions", 0),
            "clicks": raw_metrics.get("clicks", 0),
            "spend_micros": int(raw_metrics.get("spend", 0) * 1_000_000),
            "conversions": raw_metrics.get("conversions", 0),
            "conversion_value_micros": int(
                raw_metrics.get("conversion_value", 0) * 1_000_000
            ),
            "currency": raw_metrics.get("currency", "TRY"),
        }
