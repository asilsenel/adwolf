import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface MetricCardProps {
    title: string;
    value: string | number;
    change?: number;
    changeLabel?: string;
    icon?: React.ReactNode;
    format?: "currency" | "number" | "percent";
    className?: string;
}

function formatValue(value: string | number, format?: string): string {
    if (typeof value === "string") return value;

    switch (format) {
        case "currency":
            return new Intl.NumberFormat("tr-TR", {
                style: "currency",
                currency: "TRY",
                minimumFractionDigits: 0,
                maximumFractionDigits: 0,
            }).format(value);
        case "percent":
            return `${value.toFixed(1)}%`;
        case "number":
        default:
            return new Intl.NumberFormat("tr-TR").format(value);
    }
}

export function MetricCard({
    title,
    value,
    change,
    changeLabel,
    icon,
    format,
    className
}: MetricCardProps) {
    const formattedValue = formatValue(value, format);
    const isPositive = change !== undefined && change > 0;
    const isNegative = change !== undefined && change < 0;
    const isNeutral = change === 0 || change === undefined;

    return (
        <Card className={cn(
            "bg-white  border-primary-light  hover:shadow-md transition-shadow",
            className
        )}>
            <CardContent className="p-6">
                <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-muted-foreground">{title}</p>
                    {icon && <div className="text-primary">{icon}</div>}
                </div>
                <div className="mt-2">
                    <p className="text-2xl font-bold text-foreground">{formattedValue}</p>
                    {change !== undefined && (
                        <div className={cn(
                            "text-sm mt-1 flex items-center gap-1",
                            isPositive && "text-success",
                            isNegative && "text-danger",
                            isNeutral && "text-muted-foreground"
                        )}>
                            {isPositive && <TrendingUp size={16} />}
                            {isNegative && <TrendingDown size={16} />}
                            {isNeutral && <Minus size={16} />}
                            <span>
                                {isPositive && "+"}
                                {change.toFixed(1)}%
                            </span>
                            {changeLabel && (
                                <span className="text-muted-foreground ml-1">
                                    {changeLabel}
                                </span>
                            )}
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
