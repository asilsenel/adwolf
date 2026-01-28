"use client";

import { Header } from "@/components/layout/header";
import { MetricCard } from "@/components/dashboard/metric-card";
import { SpendChart } from "@/components/dashboard/spend-chart";
import { PlatformSummary } from "@/components/dashboard/platform-summary";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
    DollarSign,
    MousePointer,
    Eye,
    TrendingUp,
    AlertCircle,
    Sparkles
} from "lucide-react";

// Mock data - will be replaced with API calls
const mockMetrics = {
    spend: 12450,
    spendChange: 12.5,
    clicks: 3245,
    clicksChange: -5.2,
    impressions: 124500,
    impressionsChange: 8.3,
    roas: 3.2,
    roasChange: 15.1,
};

const mockChartData = [
    { date: "22 Oca", spend: 1800 },
    { date: "23 Oca", spend: 2100 },
    { date: "24 Oca", spend: 1950 },
    { date: "25 Oca", spend: 2400 },
    { date: "26 Oca", spend: 1700 },
    { date: "27 Oca", spend: 2200 },
    { date: "28 Oca", spend: 2300 },
];

const mockPlatformData = [
    { platform: "google_ads" as const, spend: 7470, percentage: 60 },
    { platform: "meta_ads" as const, spend: 4980, percentage: 40 },
];

const mockInsights = [
    {
        id: 1,
        priority: "high" as const,
        title: "Google Ads CPC artışı",
        description: "Son 7 günde CPC %15 arttı. Teklif stratejinizi gözden geçirin.",
    },
    {
        id: 2,
        priority: "medium" as const,
        title: "Meta Ads ROAS iyileşmesi",
        description: "Meta reklamlarınız %20 daha iyi performans gösteriyor.",
    },
    {
        id: 3,
        priority: "low" as const,
        title: "Bütçe kullanımı",
        description: "Günlük bütçenizin %85'ini kullandınız.",
    },
];

export default function DashboardPage() {
    return (
        <div className="flex-1">
            <Header
                title="Dashboard"
                subtitle="Reklam performansınıza genel bakış"
                showDatePicker
                showRefresh
            />

            <div className="p-6 space-y-6">
                {/* Metric Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <MetricCard
                        title="Toplam Harcama"
                        value={mockMetrics.spend}
                        change={mockMetrics.spendChange}
                        format="currency"
                        icon={<DollarSign size={20} />}
                    />
                    <MetricCard
                        title="Tıklama"
                        value={mockMetrics.clicks}
                        change={mockMetrics.clicksChange}
                        format="number"
                        icon={<MousePointer size={20} />}
                    />
                    <MetricCard
                        title="Gösterim"
                        value={mockMetrics.impressions}
                        change={mockMetrics.impressionsChange}
                        format="number"
                        icon={<Eye size={20} />}
                    />
                    <MetricCard
                        title="ROAS"
                        value={`${mockMetrics.roas}x`}
                        change={mockMetrics.roasChange}
                        icon={<TrendingUp size={20} />}
                    />
                </div>

                {/* Charts Row */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-2">
                        <SpendChart data={mockChartData} />
                    </div>
                    <div>
                        <PlatformSummary data={mockPlatformData} />
                    </div>
                </div>

                {/* Recent Insights */}
                <Card className="bg-white border-primary-light">
                    <CardHeader className="flex flex-row items-center justify-between">
                        <CardTitle className="text-lg flex items-center gap-2">
                            <Sparkles size={20} className="text-primary" />
                            Son Öneriler
                        </CardTitle>
                        <a href="/insights" className="text-sm text-primary hover:underline">
                            Tümünü Gör →
                        </a>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            {mockInsights.map((insight) => (
                                <div
                                    key={insight.id}
                                    className={`p-4 rounded-lg border-l-4 ${insight.priority === "high"
                                            ? "border-l-warning bg-warning/5"
                                            : insight.priority === "medium"
                                                ? "border-l-primary bg-primary/5"
                                                : "border-l-muted-foreground bg-muted/30"
                                        }`}
                                >
                                    <div className="flex items-start justify-between gap-4">
                                        <div>
                                            <div className="flex items-center gap-2 mb-1">
                                                <h4 className="font-semibold">{insight.title}</h4>
                                                <Badge
                                                    variant={
                                                        insight.priority === "high"
                                                            ? "warning"
                                                            : insight.priority === "medium"
                                                                ? "default"
                                                                : "secondary"
                                                    }
                                                >
                                                    {insight.priority === "high" ? "Yüksek" : insight.priority === "medium" ? "Orta" : "Düşük"}
                                                </Badge>
                                            </div>
                                            <p className="text-sm text-muted-foreground">
                                                {insight.description}
                                            </p>
                                        </div>
                                        <AlertCircle
                                            size={20}
                                            className={
                                                insight.priority === "high"
                                                    ? "text-warning"
                                                    : insight.priority === "medium"
                                                        ? "text-primary"
                                                        : "text-muted-foreground"
                                            }
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
