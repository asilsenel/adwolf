/**
 * API Client for AdWolf Backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ApiError {
    code: string;
    message: string;
    details?: Record<string, unknown>;
}

interface ApiResponse<T> {
    success: boolean;
    data?: T;
    error?: ApiError;
}

class ApiClient {
    private baseUrl: string;
    private token: string | null = null;

    constructor(baseUrl: string) {
        this.baseUrl = baseUrl;
    }

    setToken(token: string | null) {
        this.token = token;
    }

    private async request<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<T> {
        const headers: HeadersInit = {
            "Content-Type": "application/json",
            ...options.headers,
        };

        if (this.token) {
            (headers as Record<string, string>)["Authorization"] = `Bearer ${this.token}`;
        }

        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            ...options,
            headers,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({
                code: "UNKNOWN_ERROR",
                message: "An unknown error occurred",
            }));
            throw new Error(error.message || `HTTP ${response.status}`);
        }

        return response.json();
    }

    // GET request
    async get<T>(endpoint: string): Promise<T> {
        return this.request<T>(endpoint, { method: "GET" });
    }

    // POST request
    async post<T>(endpoint: string, data?: unknown): Promise<T> {
        return this.request<T>(endpoint, {
            method: "POST",
            body: data ? JSON.stringify(data) : undefined,
        });
    }

    // PUT request
    async put<T>(endpoint: string, data?: unknown): Promise<T> {
        return this.request<T>(endpoint, {
            method: "PUT",
            body: data ? JSON.stringify(data) : undefined,
        });
    }

    // DELETE request
    async delete<T>(endpoint: string): Promise<T> {
        return this.request<T>(endpoint, { method: "DELETE" });
    }
}

export const apiClient = new ApiClient(API_BASE_URL);

// Convenience exports
export const api = {
    // Health check
    health: () => apiClient.get<{ status: string; version: string }>("/health"),

    // Accounts
    accounts: {
        list: () => apiClient.get("/api/v1/accounts"),
        get: (id: string) => apiClient.get(`/api/v1/accounts/${id}`),
        delete: (id: string) => apiClient.delete(`/api/v1/accounts/${id}`),
        triggerSync: (id: string, data?: { date_from?: string; date_to?: string }) =>
            apiClient.post(`/api/v1/accounts/${id}/sync`, data),
    },

    // Metrics
    metrics: {
        summary: (params?: {
            preset?: string;
            date_from?: string;
            date_to?: string;
            account_id?: string;
        }) => {
            const searchParams = new URLSearchParams(params as Record<string, string>);
            return apiClient.get(`/api/v1/metrics/summary?${searchParams}`);
        },
        daily: (params?: { preset?: string; account_id?: string }) => {
            const searchParams = new URLSearchParams(params as Record<string, string>);
            return apiClient.get(`/api/v1/metrics/daily?${searchParams}`);
        },
        campaigns: (params?: { preset?: string; page?: number; per_page?: number }) => {
            const searchParams = new URLSearchParams(params as Record<string, string>);
            return apiClient.get(`/api/v1/metrics/campaigns?${searchParams}`);
        },
        byPlatform: (params?: { preset?: string }) => {
            const searchParams = new URLSearchParams(params as Record<string, string>);
            return apiClient.get(`/api/v1/metrics/by-platform?${searchParams}`);
        },
    },

    // Insights
    insights: {
        list: (params?: { is_read?: boolean; type?: string; limit?: number }) => {
            const searchParams = new URLSearchParams(params as Record<string, string>);
            return apiClient.get(`/api/v1/insights?${searchParams}`);
        },
        get: (id: string) => apiClient.get(`/api/v1/insights/${id}`),
        markRead: (id: string) => apiClient.post(`/api/v1/insights/${id}/read`),
        dismiss: (id: string) => apiClient.post(`/api/v1/insights/${id}/dismiss`),
        todayDigest: () => apiClient.get("/api/v1/insights/digest/today"),
        digestHistory: () => apiClient.get("/api/v1/insights/digest/history"),
    },

    // Actions
    actions: {
        list: (params?: { status?: string }) => {
            const searchParams = new URLSearchParams(params as Record<string, string>);
            return apiClient.get(`/api/v1/insights/actions?${searchParams}`);
        },
        execute: (id: string) => apiClient.post(`/api/v1/insights/actions/${id}/execute`),
        dismiss: (id: string) => apiClient.post(`/api/v1/insights/actions/${id}/dismiss`),
    },

    // Auth (OAuth)
    auth: {
        initiateGoogle: (redirectUri?: string) =>
            apiClient.post("/api/v1/auth/google/initiate", { redirect_uri: redirectUri }),
        initiateMeta: (redirectUri?: string) =>
            apiClient.post("/api/v1/auth/meta/initiate", { redirect_uri: redirectUri }),
    },
};
