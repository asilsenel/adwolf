"use client";

import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/button";
import { Chrome, ArrowRight, Loader2 } from "lucide-react";
import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ConnectGoogleAdsProps {
    variant?: "large" | "small";
    onSuccess?: () => void;
}

export function ConnectGoogleAds({ variant = "large", onSuccess }: ConnectGoogleAdsProps) {
    const { user } = useAuthStore();
    const [isLoading, setIsLoading] = useState(false);

    const handleConnect = () => {
        if (!user?.id) {
            console.error("User not logged in");
            return;
        }

        setIsLoading(true);

        // Redirect to Google OAuth
        const redirectUri = `${window.location.origin}/dashboard`;
        const authUrl = `${API_URL}/api/v1/auth/google/authorize?user_id=${user.id}&redirect_uri=${encodeURIComponent(redirectUri)}`;

        // Open in same window (will redirect back after auth)
        window.location.href = authUrl;
    };

    if (variant === "small") {
        return (
            <Button onClick={handleConnect} disabled={isLoading} size="sm">
                {isLoading ? (
                    <Loader2 className="animate-spin mr-2" size={16} />
                ) : (
                    <Chrome size={16} className="mr-2" />
                )}
                Google Ads Bağla
            </Button>
        );
    }

    // Large variant - Call to action card
    return (
        <div className="flex flex-col items-center justify-center p-12 bg-white  rounded-xl border border-primary-light  shadow-sm">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 via-red-500 to-yellow-500 flex items-center justify-center mb-6">
                <Chrome size={40} className="text-white" />
            </div>

            <h2 className="text-2xl font-bold text-foreground mb-2">
                Google Ads Hesabınızı Bağlayın
            </h2>
            <p className="text-muted-foreground text-center max-w-md mb-6">
                Google Ads hesabınızı bağlayarak performans verilerinizi görüntüleyebilir,
                AI destekli öneriler alabilirsiniz.
            </p>

            <Button
                onClick={handleConnect}
                disabled={isLoading}
                size="lg"
                className="text-lg px-8"
            >
                {isLoading ? (
                    <Loader2 className="animate-spin mr-2" size={20} />
                ) : (
                    <Chrome size={20} className="mr-2" />
                )}
                Google Ads ile Bağlan
                <ArrowRight size={20} className="ml-2" />
            </Button>

            <p className="text-xs text-muted-foreground mt-4">
                🔒 Verileriniz güvenle şifrelenir
            </p>
        </div>
    );
}
