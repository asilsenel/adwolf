"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";
import { PlatformIcon } from "@/components/accounts/platform-icon";

interface PlatformSummaryProps {
    data: Array<{
        platform: "google_ads" | "meta_ads";
        spend: number;
        percentage: number;
    }>;
}

const COLORS: Record<string, string> = {
    google_ads: "#4285F4",
    meta_ads: "#0081FB",
};

const LABELS: Record<string, string> = {
    google_ads: "Google Ads",
    meta_ads: "Meta Ads",
};

export function PlatformSummary({ data }: PlatformSummaryProps) {
    const chartData = data.map((item) => ({
        name: LABELS[item.platform],
        value: item.spend,
        percentage: item.percentage,
    }));

    return (
        <Card className="bg-white border-primary-light">
            <CardHeader>
                <CardTitle className="text-lg">Platform Dağılımı</CardTitle>
            </CardHeader>
            <CardContent>
                <div className="h-[200px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie
                                data={chartData}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={80}
                                paddingAngle={5}
                                dataKey="value"
                            >
                                {data.map((entry, index) => (
                                    <Cell
                                        key={`cell-${index}`}
                                        fill={COLORS[entry.platform]}
                                    />
                                ))}
                            </Pie>
                            <Tooltip
                                formatter={(value) => `₺${(value as number)?.toLocaleString("tr-TR") ?? 0}`}
                            />
                        </PieChart>
                    </ResponsiveContainer>
                </div>

                {/* Legend */}
                <div className="mt-4 space-y-2">
                    {data.map((item) => (
                        <div
                            key={item.platform}
                            className="flex items-center justify-between text-sm"
                        >
                            <div className="flex items-center gap-2">
                                <PlatformIcon platform={item.platform} size={20} />
                                <span>{LABELS[item.platform]}</span>
                            </div>
                            <div className="text-right">
                                <span className="font-semibold">
                                    ₺{item.spend.toLocaleString("tr-TR")}
                                </span>
                                <span className="text-muted-foreground ml-2">
                                    ({item.percentage}%)
                                </span>
                            </div>
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
}
