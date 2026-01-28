/**
 * TypeScript types for Insights and Actions
 */

export type InsightType =
    | "performance"
    | "optimization"
    | "alert"
    | "opportunity"
    | "anomaly";

export type InsightPriority = "low" | "medium" | "high" | "critical";

export type ActionStatus =
    | "pending"
    | "approved"
    | "executed"
    | "dismissed"
    | "failed";

export interface RecommendedAction {
    id: string;
    insight_id: string;
    org_id: string;
    title: string;
    description?: string;
    action_type: string;
    platform?: string;
    target_entity_type?: string;
    target_entity_id?: string;
    action_params: Record<string, unknown>;
    expected_impact?: string;
    estimated_improvement?: number;
    status: ActionStatus;
    executed_at?: string;
    created_at: string;
}

export interface Insight {
    id: string;
    org_id: string;
    account_id?: string;
    campaign_id?: string;
    type: InsightType;
    priority: InsightPriority;
    title: string;
    summary: string;
    detailed_analysis?: string;
    ai_confidence?: number;
    is_read: boolean;
    is_dismissed: boolean;
    read_at?: string;
    created_at: string;
    valid_until?: string;
    actions: RecommendedAction[];
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
