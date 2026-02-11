"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { MetricCard } from "@/components/dashboard/metric-card";
import { SpendChart } from "@/components/dashboard/spend-chart";
import { PlatformSummary } from "@/components/dashboard/platform-summary";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConnectGoogleAds } from "@/components/integrations/ConnectGoogleAds";
import { ConnectMeta } from "@/components/integrations/ConnectMeta";
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
    ChevronDown,
    ChevronUp,
} from "lucide-react";
import { DateRangePicker } from "@/components/ui/date-range-picker";
import { subDays } from "date-fns";
import { Button } from "@/components/ui/button";


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
    const { hydrate, isAuthenticated } = useAuthStore();
    const [accounts, setAccounts] = useState<Account[]>([]);
    const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
    const [dailyData, setDailyData] = useState<DailyMetric[]>([]);
    const [platformData, setPlatformData] = useState<PlatformMetric[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [dateFrom, setDateFrom] = useState<Date>(() => subDays(new Date(), 30));
    const [dateTo, setDateTo] = useState<Date>(() => new Date());
    const [selectedAccountId, setSelectedAccountId] = useState<string>("all");
    const [isAccountsExpanded, setIsAccountsExpanded] = useState(true);
    const [isSyncingAll, setIsSyncingAll] = useState(false);

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
    }, [isAuthenticated, dateFrom, dateTo, selectedAccountId]);

    const fetchAllData = async () => {
        try {
            setIsLoading(true);

            // Format date range
            const dateFromStr = dateFrom.toISOString().split('T')[0];
            const dateToStr = dateTo.toISOString().split('T')[0];

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
            await fetchAllData();
        } catch (error: unknown) {
            console.error("Sync failed:", error);
        }
    };

    const handleSyncAll = async () => {
        if (accounts.length === 0) return;

        setIsSyncingAll(true);
        try {
            for (const account of accounts) {
                const isMcc = account.platform_account_id === (account as unknown as { platform_metadata?: { mcc_id?: string } }).platform_metadata?.mcc_id;
                if (isMcc) continue;

                try {
                    await api.post(`/api/v1/accounts/${account.id}/sync`);
                } catch (err) {
                    console.error(`Sync failed for account ${account.id}:`, err);
                }
            }
            await fetchAllData();
        } finally {
            setIsSyncingAll(false);
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
                {/* Connected Accounts Section - Collapsible */}
                <Card className="bg-white  border-primary-light ">
                    <CardHeader
                        className="flex flex-row items-center justify-between cursor-pointer"
                        onClick={() => setIsAccountsExpanded(!isAccountsExpanded)}
                    >
                        <div className="flex items-center gap-2">
                            <CardTitle className="text-lg">Bağlı Hesaplar ({accounts.length})</CardTitle>
                            {isAccountsExpanded ? (
                                <ChevronUp size={18} className="text-muted-foreground" />
                            ) : (
                                <ChevronDown size={18} className="text-muted-foreground" />
                            )}
                        </div>
                        <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
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
                            <ConnectMeta variant="small" />
                        </div>
                    </CardHeader>
                    {isAccountsExpanded && (
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
                    )}
                </Card>

                {/* Filters - Always visible */}
                <div className="flex items-center justify-between flex-wrap gap-4">
                    <h2 className="text-lg font-semibold text-foreground">Performans Metrikleri</h2>
                    <div className="flex items-center gap-3 flex-wrap">
                        {/* Account Filter */}
                        {accounts.length > 0 && (
                            <AccountSelector
                                accounts={accounts}
                                selectedAccountId={selectedAccountId}
                                onSelect={setSelectedAccountId}
                            />
                        )}
                        {/* Date Range Filter */}
                        <DateRangePicker
                            startDate={dateFrom}
                            endDate={dateTo}
                            onChange={(start, end) => {
                                setDateFrom(start);
                                setDateTo(end);
                            }}
                        />
                    </div>
                </div>

                {/* Metrics Section - Only show if we have real data */}
                {hasMetrics ? (
                    <>
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
                    <Card className="bg-white  border-primary-light ">
                        <CardContent className="py-12 text-center">
                            <AlertCircle size={48} className="mx-auto text-muted-foreground mb-4" />
                            <h3 className="text-lg font-semibold mb-2">Henüz Metrik Verisi Yok</h3>
                            <p className="text-muted-foreground mb-4">
                                Bağlı hesaplarınızdan veri çekmek için aşağıdaki butona tıklayın.
                            </p>
                            <Button
                                onClick={handleSyncAll}
                                disabled={isSyncingAll || accounts.length === 0}
                                className="bg-primary hover:bg-primary-dark text-white"
                            >
                                {isSyncingAll ? (
                                    <>
                                        <Loader2 size={16} className="animate-spin mr-2" />
                                        Senkronize Ediliyor...
                                    </>
                                ) : (
                                    <>
                                        <RefreshCw size={16} className="mr-2" />
                                        Tüm Hesapları Senkronize Et
                                    </>
                                )}
                            </Button>
                            <p className="text-sm text-muted-foreground mt-4">
                                İlk senkronizasyon Google Ads API'sinden gerçek verileri çekecektir.
                            </p>
                        </CardContent>
                    </Card>
                )}

                {/* Info Card */}
                <Card className="bg-blue-50  border-blue-200 ">
                    <CardContent className="py-4">
                        <div className="flex items-start gap-3">
                            <Sparkles size={20} className="text-blue-600 mt-0.5" />
                            <div>
                                <h4 className="font-semibold text-blue-900 ">Gerçek Veri Modu</h4>
                                <p className="text-sm text-blue-700 ">
                                    {accounts.length} bağlı hesap bulundu.
                                    {hasMetrics
                                        ? ` ${metrics?.campaigns_count || 0} kampanyadan veriler gösteriliyor.`
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
