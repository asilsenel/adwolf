"use client";

import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PlatformIcon, getPlatformLabel } from "@/components/accounts/platform-icon";
import { ArrowLeft, ExternalLink, Loader2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/store/authStore";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const platforms = [
    {
        id: "google_ads",
        platform: "google_ads" as const,
        name: "Google Ads",
        description: "Google Arama, Display, YouTube ve Alışveriş reklamları",
        features: ["Arama Reklamları", "Display Ağı", "YouTube", "Shopping"],
    },
    {
        id: "meta_ads",
        platform: "meta_ads" as const,
        name: "Meta Ads",
        description: "Facebook, Instagram ve Audience Network reklamları",
        features: ["Facebook", "Instagram", "Messenger", "Audience Network"],
    },
];

export default function ConnectAccountPage() {
    const { user, hydrate } = useAuthStore();
    const [loadingPlatform, setLoadingPlatform] = useState<string | null>(null);

    useEffect(() => {
        hydrate();
    }, [hydrate]);

    const handleConnect = async (platform: string) => {
        if (!user?.id) {
            console.error("User not logged in");
            return;
        }

        setLoadingPlatform(platform);

        const redirectUri = `${window.location.origin}/accounts`;

        if (platform === "google_ads") {
            // Google Ads uses GET redirect (same as dashboard ConnectGoogleAds)
            const authUrl = `${API_URL}/api/v1/auth/google/authorize?user_id=${user.id}&redirect_uri=${encodeURIComponent(redirectUri)}`;
            window.location.href = authUrl;
        } else if (platform === "meta_ads") {
            // Meta Ads uses POST /meta/initiate
            try {
                const response = await fetch(
                    `${API_URL}/api/v1/auth/meta/initiate?user_id=${user.id}`,
                    {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ redirect_uri: redirectUri }),
                    }
                );

                if (response.ok) {
                    const data = await response.json();
                    window.location.href = data.authorization_url;
                } else {
                    console.error("Meta OAuth initiation failed");
                    setLoadingPlatform(null);
                }
            } catch (error) {
                console.error("Meta OAuth error:", error);
                setLoadingPlatform(null);
            }
        }
    };

    return (
        <div className="flex-1">
            <Header
                title="Hesap Bağla"
                subtitle="Reklam platformlarınızı bağlayın"
            />

            <div className="p-6 space-y-6">
                {/* Back Button */}
                <Link href="/accounts">
                    <Button variant="ghost" className="gap-2">
                        <ArrowLeft size={18} />
                        Geri
                    </Button>
                </Link>

                {/* Platform Cards */}
                <div className="grid gap-6 md:grid-cols-2 max-w-4xl">
                    {platforms.map((p) => (
                        <Card
                            key={p.id}
                            className="bg-white border-primary-light hover:shadow-lg transition-shadow"
                        >
                            <CardHeader>
                                <div className="flex items-center gap-4">
                                    <PlatformIcon platform={p.platform} size={48} />
                                    <div>
                                        <CardTitle>{p.name}</CardTitle>
                                        <CardDescription>{p.description}</CardDescription>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent>
                                <div className="mb-4">
                                    <p className="text-sm text-muted-foreground mb-2">Desteklenen:</p>
                                    <div className="flex flex-wrap gap-2">
                                        {p.features.map((feature) => (
                                            <span
                                                key={feature}
                                                className="text-xs bg-cream px-2 py-1 rounded-full"
                                            >
                                                {feature}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                                <Button
                                    className="w-full"
                                    onClick={() => handleConnect(p.id)}
                                    disabled={loadingPlatform === p.id}
                                >
                                    {loadingPlatform === p.id ? (
                                        <Loader2 size={16} className="animate-spin mr-2" />
                                    ) : (
                                        <ExternalLink size={16} className="mr-2" />
                                    )}
                                    {loadingPlatform === p.id ? "Yönlendiriliyor..." : `${p.name} Bağla`}
                                </Button>
                            </CardContent>
                        </Card>
                    ))}
                </div>

                {/* Info */}
                <div className="max-w-4xl">
                    <Card className="bg-cream border-primary-light">
                        <CardContent className="py-4">
                            <p className="text-sm text-muted-foreground">
                                ⓘ Hesaplarınızı bağladığınızda, yalnızca okuma izinleri istenir.
                                Verileriniz güvenlidir ve şifrelenmiş olarak saklanır.
                            </p>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
