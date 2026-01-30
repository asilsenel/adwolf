/**
 * API Types
 */

export interface User {
    id: string;
    email: string;
    created_at?: string;
}

export interface LoginRequest {
    email: string;
    password: string;
}

export interface LoginResponse {
    access_token: string;
    token_type: string;
    expires_in: number;
    refresh_token?: string;
    user: User;
}

export interface ApiError {
    detail: string;
    code?: string;
}

export interface Account {
    id: string;
    org_id: string;
    platform: 'google_ads' | 'meta_ads';
    platform_account_id: string;
    platform_account_name: string | null;
    account_name?: string;
    status: 'active' | 'paused' | 'disconnected' | 'error';
    last_sync_at: string | null;
    last_sync_status: 'pending' | 'running' | 'completed' | 'failed' | null;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface AccountsListResponse {
    accounts: Account[];
    total: number;
}
