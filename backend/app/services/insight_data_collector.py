"""
Ad Platform MVP - Insight Data Collector

Collects and structures campaign-level data for AI insight generation.
Provides rich context including trends, anomalies, and per-campaign metrics.
"""

import logging
from datetime import date, timedelta
from typing import Optional

from app.core.supabase import SupabaseService, get_supabase_service

logger = logging.getLogger(__name__)


class InsightDataCollector:
    """Collects rich campaign-level data for AI analysis."""

    def __init__(self, supabase: Optional[SupabaseService] = None):
        self.supabase = supabase or get_supabase_service()

    async def collect_org_data(self, org_id: str) -> dict:
        """
        Collect comprehensive org data for AI insight generation.

        Returns structured data with:
        - Account summaries
        - Per-campaign metrics (current + previous period)
        - Trend calculations (week-over-week)
        - Anomaly flags
        """
        today = date.today()
        week_ago = today - timedelta(days=7)
        two_weeks_ago = today - timedelta(days=14)

        # Get active accounts
        accounts = await self.supabase.get_connected_accounts(org_id)
        if not accounts:
            logger.info(f"No active accounts for org {org_id}")
            return {"accounts": [], "campaigns": [], "has_data": False}

        # Get campaign-level metrics for current and previous periods
        current_metrics = await self.supabase.get_campaign_metrics_for_org(
            org_id=org_id,
            date_from=week_ago.isoformat(),
            date_to=today.isoformat(),
        )

        previous_metrics = await self.supabase.get_campaign_metrics_for_org(
            org_id=org_id,
            date_from=two_weeks_ago.isoformat(),
            date_to=week_ago.isoformat(),
        )

        # Also get account-level metrics
        current_account_metrics = await self.supabase.get_daily_metrics(
            org_id=org_id,
            date_from=week_ago.isoformat(),
            date_to=today.isoformat(),
        )

        previous_account_metrics = await self.supabase.get_daily_metrics(
            org_id=org_id,
            date_from=two_weeks_ago.isoformat(),
            date_to=week_ago.isoformat(),
        )

        if not current_metrics and not current_account_metrics:
            logger.info(f"No metrics data for org {org_id}")
            return {"accounts": accounts, "campaigns": [], "has_data": False}

        # Aggregate per-campaign
        campaign_data = self._aggregate_campaign_metrics(current_metrics, previous_metrics)

        # Aggregate org-level totals
        org_current = self._aggregate_totals(current_account_metrics)
        org_previous = self._aggregate_totals(previous_account_metrics)
        org_changes = self._calc_changes(org_current, org_previous)

        # Detect anomalies
        anomalies = self._detect_anomalies(campaign_data)

        # Get active campaigns list
        active_campaigns = await self.supabase.get_active_campaigns_for_org(org_id)

        return {
            "has_data": True,
            "period": {
                "current": f"{week_ago.isoformat()} ~ {today.isoformat()}",
                "previous": f"{two_weeks_ago.isoformat()} ~ {week_ago.isoformat()}",
            },
            "accounts": [
                {
                    "id": a["id"],
                    "platform": a["platform"],
                    "name": a.get("account_name", "Unknown"),
                }
                for a in accounts
            ],
            "org_totals": {
                "current": org_current,
                "previous": org_previous,
                "changes": org_changes,
            },
            "campaigns": campaign_data,
            "active_campaign_count": len(active_campaigns),
            "anomalies": anomalies,
        }

    def _aggregate_campaign_metrics(
        self,
        current_metrics: list[dict],
        previous_metrics: list[dict],
    ) -> list[dict]:
        """Aggregate metrics per campaign for current and previous periods."""
        # Group by entity_id (campaign)
        current_by_campaign = self._group_by_campaign(current_metrics)
        previous_by_campaign = self._group_by_campaign(previous_metrics)

        campaign_data = []
        all_campaign_ids = set(current_by_campaign.keys()) | set(previous_by_campaign.keys())

        for campaign_id in all_campaign_ids:
            current = current_by_campaign.get(campaign_id)
            previous = previous_by_campaign.get(campaign_id)

            current_agg = self._aggregate_totals(current["metrics"]) if current else self._empty_totals()
            previous_agg = self._aggregate_totals(previous["metrics"]) if previous else self._empty_totals()
            changes = self._calc_changes(current_agg, previous_agg)

            campaign_data.append({
                "campaign_id": campaign_id,
                "campaign_name": (current or previous or {}).get("name", "Unknown"),
                "account_id": (current or previous or {}).get("account_id", ""),
                "platform": (current or previous or {}).get("platform", ""),
                "current": current_agg,
                "previous": previous_agg,
                "changes": changes,
            })

        # Sort by spend descending
        campaign_data.sort(key=lambda c: c["current"]["spend"], reverse=True)

        # Limit to top 30 campaigns to keep prompt manageable
        return campaign_data[:30]

    def _group_by_campaign(self, metrics: list[dict]) -> dict:
        """Group metrics list by campaign entity_id."""
        groups = {}
        for m in metrics:
            entity_id = m.get("entity_id", "")
            if not entity_id:
                continue
            if entity_id not in groups:
                groups[entity_id] = {
                    "name": m.get("entity_name", "Unknown"),
                    "account_id": m.get("account_id", ""),
                    "platform": m.get("platform", ""),
                    "metrics": [],
                }
            groups[entity_id]["metrics"].append(m)
        return groups

    def _aggregate_totals(self, metrics_list: list[dict]) -> dict:
        """Aggregate a list of daily metric records into totals."""
        if not metrics_list:
            return self._empty_totals()

        impressions = sum(int(m.get("impressions", 0) or 0) for m in metrics_list)
        clicks = sum(int(m.get("clicks", 0) or 0) for m in metrics_list)
        spend = sum(float(m.get("spend", 0) or 0) for m in metrics_list)
        conversions = sum(float(m.get("conversions", 0) or 0) for m in metrics_list)
        conversion_value = sum(float(m.get("conversion_value", 0) or 0) for m in metrics_list)

        ctr = round(clicks / impressions * 100, 2) if impressions > 0 else 0
        cpc = round(spend / clicks, 2) if clicks > 0 else 0
        cpm = round(spend / impressions * 1000, 2) if impressions > 0 else 0
        roas = round(conversion_value / spend, 2) if spend > 0 else 0
        cpa = round(spend / conversions, 2) if conversions > 0 else 0

        return {
            "impressions": impressions,
            "clicks": clicks,
            "spend": round(spend, 2),
            "conversions": round(conversions, 2),
            "conversion_value": round(conversion_value, 2),
            "ctr": ctr,
            "cpc": cpc,
            "cpm": cpm,
            "roas": roas,
            "cpa": cpa,
        }

    def _empty_totals(self) -> dict:
        """Return empty metrics dict."""
        return {
            "impressions": 0, "clicks": 0, "spend": 0,
            "conversions": 0, "conversion_value": 0,
            "ctr": 0, "cpc": 0, "cpm": 0, "roas": 0, "cpa": 0,
        }

    def _calc_changes(self, current: dict, previous: dict) -> dict:
        """Calculate percentage changes between two periods."""
        changes = {}
        for key in ["impressions", "clicks", "spend", "conversions", "ctr", "cpc", "cpm", "roas", "cpa"]:
            curr = current.get(key, 0)
            prev = previous.get(key, 0)
            if prev == 0:
                changes[f"{key}_change"] = None
            else:
                changes[f"{key}_change"] = round((curr - prev) / prev * 100, 2)
        return changes

    def _detect_anomalies(self, campaign_data: list[dict]) -> list[dict]:
        """Detect anomalies in campaign performance."""
        anomalies = []

        for campaign in campaign_data:
            changes = campaign.get("changes", {})
            name = campaign.get("campaign_name", "Unknown")
            campaign_id = campaign.get("campaign_id", "")

            # Spend spike > 30%
            spend_change = changes.get("spend_change")
            if spend_change is not None and spend_change > 30:
                anomalies.append({
                    "campaign_id": campaign_id,
                    "campaign_name": name,
                    "type": "spend_spike",
                    "message": f"{name}: Harcama %{spend_change:.0f} artti",
                    "severity": "high" if spend_change > 50 else "medium",
                })

            # CTR drop > 20%
            ctr_change = changes.get("ctr_change")
            if ctr_change is not None and ctr_change < -20:
                anomalies.append({
                    "campaign_id": campaign_id,
                    "campaign_name": name,
                    "type": "ctr_drop",
                    "message": f"{name}: CTR %{abs(ctr_change):.0f} dustu",
                    "severity": "high" if ctr_change < -40 else "medium",
                })

            # Conversion drop > 25%
            conv_change = changes.get("conversions_change")
            if conv_change is not None and conv_change < -25:
                anomalies.append({
                    "campaign_id": campaign_id,
                    "campaign_name": name,
                    "type": "conversion_drop",
                    "message": f"{name}: Donusumler %{abs(conv_change):.0f} dustu",
                    "severity": "critical" if conv_change < -50 else "high",
                })

            # CPA spike > 30%
            cpa_change = changes.get("cpa_change")
            if cpa_change is not None and cpa_change > 30:
                anomalies.append({
                    "campaign_id": campaign_id,
                    "campaign_name": name,
                    "type": "cpa_spike",
                    "message": f"{name}: CPA %{cpa_change:.0f} artti",
                    "severity": "high" if cpa_change > 50 else "medium",
                })

        return anomalies
