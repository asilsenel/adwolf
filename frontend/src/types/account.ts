/**
 * TypeScript types for Ad Accounts
 */

export type Platform = "google_ads" | "meta_ads" | "amazon_ads" | "tiktok_ads";

export type AccountStatus = "active" | "paused" | "disconnected" | "error";

export type SyncStatus = "pending" | "running" | "completed" | "failed";

export interface ConnectedAccount {
    id: string;
    org_id: string;
    platform: Platform;
    platform_account_id: string;
    platform_account_name: string | null;
    status: AccountStatus;
    last_sync_at: string | null;
    last_sync_status: SyncStatus | null;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface ConnectedAccountDetail extends ConnectedAccount {
    campaigns_count: number;
    total_spend_last_30_days: number;
    total_impressions_last_30_days: number;
}

export interface ConnectedAccountList {
    accounts: ConnectedAccount[];
    total: number;
}

export interface SyncJob {
    id: string;
    account_id: string;
    job_type: string;
    status: SyncStatus;
    started_at: string | null;
    completed_at: string | null;
    date_from: string | null;
    date_to: string | null;
    records_synced: number;
    error_message: string | null;
    created_at: string;
}
