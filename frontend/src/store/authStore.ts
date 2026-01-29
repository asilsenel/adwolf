/**
 * Auth Store - Zustand store for authentication state
 */

import { create } from "zustand";
import { api } from "@/services/api";
import { User, LoginResponse, ApiError } from "@/types/api";
import { AxiosError } from "axios";

interface AuthState {
    user: User | null;
    token: string | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    error: string | null;
}

interface AuthActions {
    login: (email: string, password: string) => Promise<boolean>;
    logout: () => void;
    hydrate: () => void;
    clearError: () => void;
}

type AuthStore = AuthState & AuthActions;

export const useAuthStore = create<AuthStore>((set, get) => ({
    // Initial state
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,

    // Login action
    login: async (email: string, password: string): Promise<boolean> => {
        set({ isLoading: true, error: null });

        try {
            const response = await api.post<LoginResponse>("/api/v1/auth/login", {
                email,
                password,
            });

            const { access_token, user } = response.data;

            // Save to localStorage
            if (typeof window !== "undefined") {
                localStorage.setItem("access_token", access_token);
                localStorage.setItem("user", JSON.stringify(user));
            }

            // Update state
            set({
                user,
                token: access_token,
                isAuthenticated: true,
                isLoading: false,
                error: null,
            });

            console.log("Login Success", user);
            return true;
        } catch (error) {
            const axiosError = error as AxiosError<ApiError>;
            const errorMessage =
                axiosError.response?.data?.detail || "Giriş başarısız. Lütfen tekrar deneyin.";

            set({
                isLoading: false,
                error: errorMessage,
                isAuthenticated: false,
            });

            console.error("Login Failed:", errorMessage);
            return false;
        }
    },

    // Logout action
    logout: () => {
        // Clear localStorage
        if (typeof window !== "undefined") {
            localStorage.removeItem("access_token");
            localStorage.removeItem("user");
        }

        // Reset state
        set({
            user: null,
            token: null,
            isAuthenticated: false,
            error: null,
        });

        // Redirect to login
        if (typeof window !== "undefined") {
            window.location.href = "/login";
        }
    },

    // Hydrate action - restore state from localStorage on page load
    hydrate: () => {
        if (typeof window === "undefined") return;

        const token = localStorage.getItem("access_token");
        const userStr = localStorage.getItem("user");

        if (token && userStr) {
            try {
                const user = JSON.parse(userStr) as User;
                set({
                    user,
                    token,
                    isAuthenticated: true,
                });
            } catch {
                // Invalid user data, clear everything
                localStorage.removeItem("access_token");
                localStorage.removeItem("user");
            }
        }
    },

    // Clear error
    clearError: () => {
        set({ error: null });
    },
}));
