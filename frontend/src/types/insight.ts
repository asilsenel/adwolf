/**
 * TypeScript types for Insights and Actions
 * Aligned with database schema (insights, recommended_actions tables)
 */

export type InsightType =
    | "performance"
    | "optimization"
    | "alert"
    | "opportunity"
    | "anomaly";

export type InsightSeverity = "low" | "medium" | "high" | "critical";

export type ActionStatus =
    | "pending"
    | "approved"
    | "executed"
    | "dismissed"
    | "failed";

export interface RecommendedAction {
    id: string;
    insight_id?: string;
    org_id: string;
    action_type: string;
    platform: string;
    account_id?: string;
    campaign_id?: string;
    entity_type?: string;
    entity_id?: string;
    title: string;
    description: string;
    rationale?: string;
    expected_impact?: string;
    is_executable: boolean;
    api_payload?: Record<string, unknown>;
    priority: number;
    recommended_by?: string;
    status: ActionStatus;
    executed_at?: string;
    executed_by?: string;
    execution_result?: Record<string, unknown>;
    created_at: string;
}

export interface Insight {
    id: string;
    org_id: string;
    insight_type: InsightType;
    severity: InsightSeverity;
    category?: string;
    platform?: string;
    account_id?: string;
    campaign_id?: string;
    entity_type?: string;
    entity_id?: string;
    title: string;
    summary: string;
    detailed_analysis?: string;
    metric_data?: Record<string, unknown>;
    comparison_period?: Record<string, unknown>;
    is_read: boolean;
    is_dismissed: boolean;
    is_actioned: boolean;
    read_at?: string;
    actioned_at?: string;
    ai_model?: string;
    ai_confidence?: number;
    created_at: string;
    expires_at?: string;
    recommended_actions: RecommendedAction[];
}

export interface InsightList {
    insights: Insight[];
    total: number;
    unread_count: number;
}

export interface DigestSection {
    title: string;
    content: string;
    metrics?: Record<string, unknown>;
}

export interface DailyDigest {
    id: string;
    org_id: string;
    digest_date: string;
    title?: string;
    summary: string;
    total_spend: number;
    total_impressions: number;
    total_clicks: number;
    total_conversions: number;
    currency: string;
    spend_change_percent?: number;
    impressions_change_percent?: number;
    conversions_change_percent?: number;
    sections: DigestSection[];
    insight_ids: string[];
    sent_via?: string;
    sent_at?: string;
    created_at: string;
}

export interface DigestList {
    digests: DailyDigest[];
    total: number;
}
