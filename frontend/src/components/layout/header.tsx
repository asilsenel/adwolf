"use client";

import { Bell, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DateRangePicker } from "@/components/dashboard/date-range-picker";

interface HeaderProps {
    title: string;
    subtitle?: string;
    showDatePicker?: boolean;
    showRefresh?: boolean;
    onRefresh?: () => void;
    isRefreshing?: boolean;
}

export function Header({
    title,
    subtitle,
    showDatePicker = false,
    showRefresh = false,
    onRefresh,
    isRefreshing = false
}: HeaderProps) {
    return (
        <header className="sticky top-0 z-30 bg-cream-light/80 backdrop-blur-sm border-b border-primary-light">
            <div className="flex items-center justify-between px-6 py-4">
                <div>
                    <h1 className="text-2xl font-bold text-foreground">{title}</h1>
                    {subtitle && (
                        <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>
                    )}
                </div>

                <div className="flex items-center gap-4">
                    {showDatePicker && <DateRangePicker />}

                    {showRefresh && (
                        <Button
                            variant="outline"
                            size="icon"
                            onClick={onRefresh}
                            disabled={isRefreshing}
                            className="border-primary-light hover:bg-cream"
                        >
                            <RefreshCw
                                size={18}
                                className={isRefreshing ? "animate-spin" : ""}
                            />
                        </Button>
                    )}

                    <Button
                        variant="ghost"
                        size="icon"
                        className="relative"
                    >
                        <Bell size={20} />
                        <span className="absolute -top-1 -right-1 w-5 h-5 bg-danger text-white text-xs rounded-full flex items-center justify-center">
                            3
                        </span>
                    </Button>
                </div>
            </div>
        </header>
    );
}
