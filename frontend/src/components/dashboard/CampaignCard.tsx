"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Target, TrendingUp, Pause, Trash2 } from "lucide-react";

interface Campaign {
    id: string;
    platform_campaign_id: string;
    name: string;
    status: string;
    campaign_type?: string;
    daily_budget?: number;
    budget_currency?: string;
}

interface CampaignCardProps {
    campaign: Campaign;
}

export function CampaignCard({ campaign }: CampaignCardProps) {
    const getStatusConfig = (status: string) => {
        switch (status) {
            case "enabled":
                return { icon: TrendingUp, label: "Aktif", badge: "success" as const };
            case "paused":
                return { icon: Pause, label: "Durduruldu", badge: "warning" as const };
            case "removed":
                return { icon: Trash2, label: "Silindi", badge: "secondary" as const };
            default:
                return { icon: Target, label: status, badge: "secondary" as const };
        }
    };

    const status = getStatusConfig(campaign.status);
    const StatusIcon = status.icon;

    const formatBudget = (budget?: number, currency?: string) => {
        if (!budget) return null;
        return new Intl.NumberFormat("tr-TR", {
            style: "currency",
            currency: currency || "TRY",
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(budget);
    };

    const formatCampaignType = (type?: string) => {
        if (!type) return null;
        const typeMap: Record<string, string> = {
            "SEARCH": "Arama",
            "DISPLAY": "Görüntülü",
            "SHOPPING": "Alışveriş",
            "VIDEO": "Video",
            "PERFORMANCE_MAX": "Performance Max",
            "SMART": "Akıllı",
            "APP": "Uygulama",
            "LOCAL": "Yerel",
            "DISCOVERY": "Keşfet",
        };
        return typeMap[type.toUpperCase()] || type;
    };

    return (
        <Card className="bg-white border-primary-light hover:shadow-sm transition-shadow">
            <CardContent className="p-3">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                        <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                            <Target size={16} className="text-primary" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <h4 className="font-medium text-sm truncate">{campaign.name}</h4>
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                {campaign.campaign_type && (
                                    <span>{formatCampaignType(campaign.campaign_type)}</span>
                                )}
                                {campaign.daily_budget && (
                                    <>
                                        <span>•</span>
                                        <span>Günlük: {formatBudget(campaign.daily_budget, campaign.budget_currency)}</span>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                    <Badge variant={status.badge} className="flex items-center gap-1 ml-2">
                        <StatusIcon size={12} />
                        {status.label}
                    </Badge>
                </div>
            </CardContent>
        </Card>
    );
}
