/**
 * API Service - Axios instance with interceptors
 */

import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Create Axios instance
export const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        "Content-Type": "application/json",
    },
    timeout: 10000,
});

// Request Interceptor - Add token to headers
api.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        // Only run on client side
        if (typeof window !== "undefined") {
            const token = localStorage.getItem("access_token");
            if (token && config.headers) {
                config.headers.Authorization = `Bearer ${token}`;
            }
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response Interceptor - Handle 401 errors
api.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
        if (error.response?.status === 401) {
            // Only run on client side
            if (typeof window !== "undefined") {
                // Clear local storage
                localStorage.removeItem("access_token");
                localStorage.removeItem("user");

                // Redirect to login (avoid loop if already on login page)
                if (!window.location.pathname.includes("/login")) {
                    window.location.href = "/login";
                }
            }
        }
        return Promise.reject(error);
    }
);

export default api;
