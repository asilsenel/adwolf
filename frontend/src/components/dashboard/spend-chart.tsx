"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Legend
} from "recharts";

interface SpendChartProps {
    data: Array<{
        date: string;
        spend: number;
        clicks?: number;
        impressions?: number;
    }>;
}

export function SpendChart({ data }: SpendChartProps) {
    return (
        <Card className="bg-white  border-primary-light ">
            <CardHeader>
                <CardTitle className="text-lg">Harcama Trendi</CardTitle>
            </CardHeader>
            <CardContent>
                <div className="h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                            <XAxis
                                dataKey="date"
                                stroke="var(--muted-foreground)"
                                fontSize={12}
                                tickLine={false}
                            />
                            <YAxis
                                stroke="var(--muted-foreground)"
                                fontSize={12}
                                tickLine={false}
                                tickFormatter={(value) => `₺${(value / 1000).toFixed(0)}k`}
                            />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: "var(--card)",
                                    color: "var(--card-foreground)",
                                    border: "1px solid var(--border)",
                                    borderRadius: "8px",
                                }}
                                formatter={(value) => [
                                    `₺${(value as number)?.toLocaleString("tr-TR") ?? 0}`,
                                    "Harcama"
                                ]}
                            />
                            <Legend />
                            <Line
                                type="monotone"
                                dataKey="spend"
                                name="Harcama"
                                stroke="#8CA9FF"
                                strokeWidth={2}
                                dot={{ fill: "#8CA9FF", strokeWidth: 2 }}
                                activeDot={{ r: 6, fill: "#8CA9FF" }}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </CardContent>
        </Card>
    );
}
