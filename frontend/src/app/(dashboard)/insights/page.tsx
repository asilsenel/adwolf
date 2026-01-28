"use client";

import { Header } from "@/components/layout/header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PlatformIcon } from "@/components/accounts/platform-icon";
import {
    Sparkles,
    AlertTriangle,
    TrendingUp,
    TrendingDown,
    ChevronRight,
    Check,
    X,
    Clock
} from "lucide-react";

// Mock insights
const mockInsights = [
    {
        id: "1",
        type: "alert",
        priority: "high",
        title: "Google Ads CPC %25 Arttı",
        summary: "\"Ana Kampanya\" kampanyanızda CPC son 7 günde önemli ölçüde arttı. Bu durum bütçenizi hızla tüketebilir.",
        platform: "google_ads" as const,
        createdAt: "2 saat önce",
        isRead: false,
        actions: [
            { id: "a1", title: "Teklif Limitini Düşür", type: "decrease_budget" },
            { id: "a2", title: "Hedeflemeyi Daralt", type: "optimize_targeting" },
        ],
    },
    {
        id: "2",
        type: "opportunity",
        priority: "medium",
        title: "Meta Ads ROAS Fırsatı",
        summary: "Instagram Stories reklamlarınız %40 daha yüksek ROAS gösteriyor. Bu formata daha fazla bütçe ayırmayı düşünün.",
        platform: "meta_ads" as const,
        createdAt: "5 saat önce",
        isRead: true,
        actions: [
            { id: "a3", title: "Bütçe Artır", type: "increase_budget" },
        ],
    },
    {
        id: "3",
        type: "performance",
        priority: "low",
        title: "Haftalık Performans Özeti",
        summary: "Geçen haftaya göre toplam harcama %12 arttı, dönüşümler %8 arttı. Genel ROAS 3.2x seviyesinde.",
        platform: "google_ads" as const,
        createdAt: "1 gün önce",
        isRead: true,
        actions: [],
    },
];

const priorityConfig = {
    critical: { color: "border-l-danger bg-danger/5", icon: AlertTriangle, iconColor: "text-danger", label: "Kritik" },
    high: { color: "border-l-warning bg-warning/5", icon: AlertTriangle, iconColor: "text-warning", label: "Yüksek" },
    medium: { color: "border-l-primary bg-primary/5", icon: TrendingUp, iconColor: "text-primary", label: "Orta" },
    low: { color: "border-l-muted-foreground bg-muted/30", icon: Clock, iconColor: "text-muted-foreground", label: "Düşük" },
};

export default function InsightsPage() {
    return (
        <div className="flex-1">
            <Header
                title="Öneriler"
                subtitle="AI-powered analiz ve optimizasyon önerileri"
            />

            <div className="p-6 space-y-6">
                {/* Daily Digest */}
                <Card className="bg-gradient-to-r from-primary to-primary-dark text-white border-0">
                    <CardContent className="py-6">
                        <div className="flex items-start justify-between">
                            <div>
                                <div className="flex items-center gap-2 mb-2">
                                    <Sparkles size={20} />
                                    <h3 className="font-semibold">Günlük Özet</h3>
                                </div>
                                <p className="text-white/90 max-w-2xl">
                                    Dün toplam ₺2,450 harcama yapıldı. Google Ads'de CPC artışı dikkat çekiyor,
                                    Meta Ads'de ise ROAS iyileşmesi devam ediyor. Genel performans hedeflerin %95'inde.
                                </p>
                            </div>
                            <Button variant="secondary" size="sm">
                                Detaylar
                                <ChevronRight size={16} />
                            </Button>
                        </div>
                    </CardContent>
                </Card>

                {/* Filter Tabs */}
                <div className="flex gap-2 overflow-x-auto pb-2">
                    <Button variant="default" size="sm">Tümü</Button>
                    <Button variant="outline" size="sm">Okunmamış</Button>
                    <Button variant="outline" size="sm">Yüksek Öncelik</Button>
                    <Button variant="outline" size="sm">Aksiyon Bekleyen</Button>
                </div>

                {/* Insights List */}
                <div className="space-y-4">
                    {mockInsights.map((insight) => {
                        const config = priorityConfig[insight.priority as keyof typeof priorityConfig];
                        const IconComponent = config.icon;

                        return (
                            <Card
                                key={insight.id}
                                className={`bg-white border-l-4 ${config.color} hover:shadow-md transition-shadow`}
                            >
                                <CardContent className="py-4">
                                    <div className="flex items-start gap-4">
                                        {/* Icon */}
                                        <div className={`mt-1 ${config.iconColor}`}>
                                            <IconComponent size={20} />
                                        </div>

                                        {/* Content */}
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-1 flex-wrap">
                                                <PlatformIcon platform={insight.platform} size={18} />
                                                <h4 className="font-semibold">{insight.title}</h4>
                                                <Badge variant={insight.priority === "high" ? "warning" : "secondary"}>
                                                    {config.label}
                                                </Badge>
                                                {!insight.isRead && (
                                                    <span className="w-2 h-2 rounded-full bg-primary" />
                                                )}
                                            </div>
                                            <p className="text-sm text-muted-foreground mb-3">
                                                {insight.summary}
                                            </p>

                                            {/* Actions */}
                                            {insight.actions.length > 0 && (
                                                <div className="flex gap-2 flex-wrap">
                                                    {insight.actions.map((action) => (
                                                        <Button key={action.id} size="sm" variant="outline">
                                                            {action.title}
                                                        </Button>
                                                    ))}
                                                    <Button size="sm" variant="ghost" className="text-muted-foreground">
                                                        <X size={14} />
                                                        Kapat
                                                    </Button>
                                                </div>
                                            )}
                                        </div>

                                        {/* Time */}
                                        <span className="text-xs text-muted-foreground whitespace-nowrap">
                                            {insight.createdAt}
                                        </span>
                                    </div>
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>

                {/* Load More */}
                <div className="text-center">
                    <Button variant="outline">
                        Daha Fazla Yükle
                    </Button>
                </div>
            </div>
        </div>
    );
}
