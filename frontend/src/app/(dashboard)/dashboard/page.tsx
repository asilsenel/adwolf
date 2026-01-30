"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { MetricCard } from "@/components/dashboard/metric-card";
import { SpendChart } from "@/components/dashboard/spend-chart";
import { PlatformSummary } from "@/components/dashboard/platform-summary";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ConnectGoogleAds } from "@/components/integrations/ConnectGoogleAds";
import { AccountCard } from "@/components/integrations/AccountCard";
import { AddAccountById } from "@/components/integrations/AddAccountById";
import { AccountSelector } from "@/components/dashboard/AccountSelector";
import { api } from "@/services/api";
import { Account, AccountsListResponse } from "@/types/api";
import { useAuthStore } from "@/store/authStore";
import {
    DollarSign,
    MousePointer,
    Eye,
    TrendingUp,
    AlertCircle,
    Sparkles,
    Loader2,
    RefreshCw,
    Calendar,
    Filter,
} from "lucide-react";
import { Button } from "@/components/ui/button";

// Date range options
const DATE_RANGES = [
    { label: "Son 7 Gün", value: 7 },
    { label: "Son 14 Gün", value: 14 },
    { label: "Son 30 Gün", value: 30 },
    { label: "Son 90 Gün", value: 90 },
];

// Types for real API data
interface MetricsSummary {
    date_from: string;
    date_to: string;
    impressions: number;
    clicks: number;
    spend: number;
    conversions: number;
    ctr: number | null;
    cpc: number | null;
    roas: number | null;
    accounts_count: number;
    campaigns_count: number;
}

interface DailyMetric {
    date: string;
    impressions: number;
    clicks: number;
    spend: number;
    conversions: number;
}

interface MetricsTrend {
    date_from: string;
    date_to: string;
    data: DailyMetric[];
    summary: MetricsSummary;
}

interface PlatformMetric {
    platform: string;
    impressions: number;
    clicks: number;
    spend: number;
    conversions: number;
    accounts_count: number;
    campaigns_count: number;
}

interface MetricsByPlatform {
    date_from: string;
    date_to: string;
    platforms: PlatformMetric[];
    total: MetricsSummary;
}

export default function DashboardPage() {
    const { hydrate, isAuthenticated, user } = useAuthStore();
    const [accounts, setAccounts] = useState<Account[]>([]);
    const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
    const [dailyData, setDailyData] = useState<DailyMetric[]>([]);
    const [platformData, setPlatformData] = useState<PlatformMetric[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [dateRange, setDateRange] = useState(30); // Default to 30 days
    const [selectedAccountId, setSelectedAccountId] = useState<string>("all"); // "all" or account ID

    // Hydrate auth state on mount
    useEffect(() => {
        hydrate();
    }, [hydrate]);

    // Fetch all data when authenticated or date range changes
    useEffect(() => {
        if (isAuthenticated) {
            fetchAllData();
        } else {
            setIsLoading(false);
        }
    }, [isAuthenticated, dateRange, selectedAccountId]);

    const fetchAllData = async () => {
        try {
            setIsLoading(true);

            // Calculate date range
            const today = new Date();
            const dateFrom = new Date(today);
            dateFrom.setDate(dateFrom.getDate() - dateRange);
            const dateFromStr = dateFrom.toISOString().split('T')[0];
            const dateToStr = today.toISOString().split('T')[0];

            // Fetch accounts
            try {
                const accountsRes = await api.get<AccountsListResponse>("/api/v1/accounts");
                if (accountsRes.data.accounts) {
                    setAccounts(accountsRes.data.accounts);
                } else if (Array.isArray(accountsRes.data)) {
                    setAccounts(accountsRes.data as unknown as Account[]);
                }
            } catch (err) {
                console.log("No accounts or error:", err);
                setAccounts([]);
            }

            // Fetch metrics summary (with optional account filter)
            try {
                let metricsUrl = `/api/v1/metrics/summary?date_from=${dateFromStr}&date_to=${dateToStr}`;
                if (selectedAccountId !== "all") {
                    metricsUrl += `&account_id=${selectedAccountId}`;
                }
                const metricsRes = await api.get<MetricsSummary>(metricsUrl);
                setMetrics(metricsRes.data);
            } catch (err) {
                console.log("No metrics:", err);
                setMetrics(null);
            }

            // Fetch daily metrics for chart (with optional account filter)
            try {
                let dailyUrl = `/api/v1/metrics/daily?date_from=${dateFromStr}&date_to=${dateToStr}`;
                if (selectedAccountId !== "all") {
                    dailyUrl += `&account_id=${selectedAccountId}`;
                }
                const dailyRes = await api.get<MetricsTrend>(dailyUrl);
                setDailyData(dailyRes.data.data || []);
            } catch (err) {
                console.log("No daily metrics:", err);
                setDailyData([]);
            }

            // Fetch platform breakdown (with optional account filter)
            try {
                let platformUrl = `/api/v1/metrics/by-platform?date_from=${dateFromStr}&date_to=${dateToStr}`;
                if (selectedAccountId !== "all") {
                    platformUrl += `&account_id=${selectedAccountId}`;
                }
                const platformRes = await api.get<MetricsByPlatform>(platformUrl);
                setPlatformData(platformRes.data.platforms || []);
            } catch (err) {
                console.log("No platform metrics:", err);
                setPlatformData([]);
            }

        } finally {
            setIsLoading(false);
            setIsRefreshing(false);
        }
    };

    const handleRefresh = () => {
        setIsRefreshing(true);
        fetchAllData();
    };

    const handleSync = async (accountId: string) => {
        try {
            console.log("Starting sync for account:", accountId);
            await api.post(`/api/v1/accounts/${accountId}/sync`);

            // Refresh all data after sync (silently)
            await fetchAllData();
        } catch (error: unknown) {
            console.error("Sync failed:", error);
        }
    };

    // Convert daily data for chart component
    const chartData = dailyData.map(d => ({
        date: new Date(d.date).toLocaleDateString('tr-TR', { day: 'numeric', month: 'short' }),
        spend: d.spend,
    }));

    // Convert platform data for component
    const platformSummary = platformData.map(p => ({
        platform: p.platform as 'google_ads' | 'meta_ads',
        spend: p.spend,
        percentage: metrics && metrics.spend > 0
            ? Math.round((p.spend / metrics.spend) * 100)
            : 0,
    }));

    // Loading state
    if (isLoading) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <Loader2 className="animate-spin text-primary" size={40} />
            </div>
        );
    }

    // No accounts - show connect CTA
    if (accounts.length === 0) {
        return (
            <div className="flex-1">
                <Header
                    title="Dashboard"
                    subtitle="Reklam performansınıza genel bakış"
                />
                <div className="p-6 flex items-center justify-center min-h-[60vh]">
                    <ConnectGoogleAds variant="large" />
                </div>
            </div>
        );
    }

    // Has accounts but no metrics yet
    const hasMetrics = metrics && (metrics.impressions > 0 || metrics.clicks > 0 || metrics.spend > 0);

    return (
        <div className="flex-1">
            <Header
                title="Dashboard"
                subtitle="Reklam performansınıza genel bakış"
            />

            <div className="p-6 space-y-6">
                {/* Connected Accounts Section */}
                <Card className="bg-white border-primary-light">
                    <CardHeader className="flex flex-row items-center justify-between">
                        <CardTitle className="text-lg">Bağlı Hesaplar ({accounts.length})</CardTitle>
                        <div className="flex gap-2">
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handleRefresh}
                                disabled={isRefreshing}
                            >
                                <RefreshCw size={14} className={isRefreshing ? "animate-spin mr-1" : "mr-1"} />
                                Yenile
                            </Button>
                            <AddAccountById onSuccess={handleRefresh} />
                            <ConnectGoogleAds variant="small" />
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="grid gap-4 md:grid-cols-2">
                            {accounts.map((account) => (
                                <AccountCard
                                    key={account.id}
                                    account={account}
                                    onSync={handleSync}
                                />
                            ))}
                        </div>
                    </CardContent>
                </Card>

                {/* Metrics Section - Only show if we have real data */}
                {hasMetrics ? (
                    <>
                        {/* Date Range Selector */}
                        <div className="flex items-center justify-between">
                            <h2 className="text-lg font-semibold text-foreground">Performans Metrikleri</h2>
                            <div className="flex items-center gap-4">
                                {/* Account Filter */}
                                {accounts.length > 1 && (
                                    <AccountSelector
                                        accounts={accounts}
                                        selectedAccountId={selectedAccountId}
                                        onSelect={setSelectedAccountId}
                                    />
                                )}
                                {/* Date Range Filter */}
                                <div className="flex items-center gap-2">
                                    <Calendar size={16} className="text-muted-foreground" />
                                    <select
                                        value={dateRange}
                                        onChange={(e) => setDateRange(Number(e.target.value))}
                                        className="bg-white border border-primary-light rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                                    >
                                        {DATE_RANGES.map((range) => (
                                            <option key={range.value} value={range.value}>
                                                {range.label}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                        </div>

                        {/* Metric Cards */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                            <MetricCard
                                title="Toplam Harcama"
                                value={metrics.spend}
                                format="currency"
                                icon={<DollarSign size={20} />}
                            />
                            <MetricCard
                                title="Tıklama"
                                value={metrics.clicks}
                                format="number"
                                icon={<MousePointer size={20} />}
                            />
                            <MetricCard
                                title="Gösterim"
                                value={metrics.impressions}
                                format="number"
                                icon={<Eye size={20} />}
                            />
                            <MetricCard
                                title="ROAS"
                                value={metrics.roas ? `${Number(metrics.roas).toFixed(1)}x` : "N/A"}
                                icon={<TrendingUp size={20} />}
                            />
                        </div>

                        {/* Charts Row */}
                        {chartData.length > 0 && (
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                <div className="lg:col-span-2">
                                    <SpendChart data={chartData} />
                                </div>
                                {platformSummary.length > 0 && (
                                    <div>
                                        <PlatformSummary data={platformSummary} />
                                    </div>
                                )}
                            </div>
                        )}
                    </>
                ) : (
                    /* No metrics yet - prompt to sync */
                    <Card className="bg-white border-primary-light">
                        <CardContent className="py-12 text-center">
                            <AlertCircle size={48} className="mx-auto text-muted-foreground mb-4" />
                            <h3 className="text-lg font-semibold mb-2">Henüz Metrik Verisi Yok</h3>
                            <p className="text-muted-foreground mb-4">
                                Bağlı hesaplarınızdan veri çekmek için "Senkronize Et" butonuna tıklayın.
                            </p>
                            <p className="text-sm text-muted-foreground">
                                İlk senkronizasyon Google Ads API'sinden gerçek verileri çekecektir.
                            </p>
                        </CardContent>
                    </Card>
                )}

                {/* Info Card */}
                <Card className="bg-blue-50 border-blue-200">
                    <CardContent className="py-4">
                        <div className="flex items-start gap-3">
                            <Sparkles size={20} className="text-blue-600 mt-0.5" />
                            <div>
                                <h4 className="font-semibold text-blue-900">Gerçek Veri Modu</h4>
                                <p className="text-sm text-blue-700">
                                    {accounts.length} bağlı hesap bulundu.
                                    {hasMetrics
                                        ? ` Son ${metrics?.campaigns_count || 0} kampanyadan veriler gösteriliyor.`
                                        : " Verileri görmek için hesabınızı senkronize edin."
                                    }
                                </p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
