/**
 * TypeScript types for Metrics
 */

export type DateRangePreset =
    | "today"
    | "yesterday"
    | "last_7_days"
    | "last_14_days"
    | "last_30_days"
    | "this_month"
    | "last_month"
    | "custom";

export interface DateRange {
    date_from: string;
    date_to: string;
    preset?: DateRangePreset;
}

export interface MetricChange {
    current: number;
    previous: number;
    change_absolute: number;
    change_percent: number | null;
}

export interface MetricsSummary {
    date_from: string;
    date_to: string;
    comparison_date_from?: string;
    comparison_date_to?: string;
    impressions: number;
    clicks: number;
    spend: number;
    conversions: number;
    conversion_value: number;
    currency: string;
    ctr: number | null;
    cpc: number | null;
    cpm: number | null;
    roas: number | null;
    cpa: number | null;
    impressions_change?: MetricChange;
    clicks_change?: MetricChange;
    spend_change?: MetricChange;
    conversions_change?: MetricChange;
    roas_change?: MetricChange;
    accounts_count: number;
    campaigns_count: number;
}

export interface MetricsByDate {
    date: string;
    impressions: number;
    clicks: number;
    spend: number;
    conversions: number;
    conversion_value: number;
}

export interface MetricsTrend {
    date_from: string;
    date_to: string;
    data: MetricsByDate[];
    summary: MetricsSummary;
}

export interface CampaignMetrics {
    id: string;
    account_id: string;
    platform: string;
    platform_campaign_id: string;
    name: string;
    status: string;
    campaign_type?: string;
    date_from: string;
    date_to: string;
    impressions: number;
    clicks: number;
    spend: number;
    currency: string;
    conversions: number;
    conversion_value: number;
    ctr?: number;
    cpc?: number;
    cpm?: number;
    roas?: number;
    cpa?: number;
}

export interface CampaignMetricsList {
    campaigns: CampaignMetrics[];
    total: number;
    page: number;
    per_page: number;
}
