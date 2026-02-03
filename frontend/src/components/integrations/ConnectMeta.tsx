"use client";

import { Button } from "@/components/ui/button";
import { Facebook, Loader2 } from "lucide-react";
import { useState } from "react";

interface ConnectMetaProps {
    variant?: "large" | "small";
    onSuccess?: () => void;
}

export function ConnectMeta({ variant = "large", onSuccess }: ConnectMetaProps) {
    const [isLoading, setIsLoading] = useState(false);

    const handleConnect = () => {
        // TODO: Implement Meta OAuth flow
        setIsLoading(true);

        // Placeholder - show coming soon message
        setTimeout(() => {
            setIsLoading(false);
            alert("Meta Ads entegrasyonu yakında eklenecek!");
        }, 500);
    };

    if (variant === "small") {
        return (
            <Button
                onClick={handleConnect}
                disabled={isLoading}
                size="sm"
                variant="outline"
                className="border-blue-500 text-blue-600 hover:bg-blue-50"
            >
                {isLoading ? (
                    <Loader2 className="animate-spin mr-2" size={16} />
                ) : (
                    <Facebook size={16} className="mr-2" />
                )}
                Meta Bağla
            </Button>
        );
    }

    // Large variant - Call to action card
    return (
        <div className="flex flex-col items-center justify-center p-12 bg-white rounded-xl border border-primary-light shadow-sm">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-600 to-blue-400 flex items-center justify-center mb-6">
                <Facebook size={40} className="text-white" />
            </div>

            <h2 className="text-2xl font-bold text-foreground mb-2">
                Meta Ads Hesabınızı Bağlayın
            </h2>
            <p className="text-muted-foreground text-center max-w-md mb-6">
                Meta Ads (Facebook & Instagram) hesabınızı bağlayarak tüm reklam verilerinizi
                tek bir yerden yönetebilirsiniz.
            </p>

            <Button
                onClick={handleConnect}
                disabled={isLoading}
                size="lg"
                className="text-lg px-8 bg-blue-600 hover:bg-blue-700"
            >
                {isLoading ? (
                    <Loader2 className="animate-spin mr-2" size={20} />
                ) : (
                    <Facebook size={20} className="mr-2" />
                )}
                Meta Ads ile Bağlan
            </Button>

            <p className="text-xs text-muted-foreground mt-4">
                Yakında kullanıma sunulacak
            </p>
        </div>
    );
}
