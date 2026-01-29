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
