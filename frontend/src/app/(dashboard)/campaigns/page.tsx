"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/services/api";
import { Account, AccountsListResponse } from "@/types/api";
import { useAuthStore } from "@/store/authStore";
import {
    Target,
    ChevronDown,
    ChevronRight,
    Loader2,
    RefreshCw,
    TrendingUp,
    Pause,
    Trash2,
    Building2,
    Search,
    DollarSign,
    Calendar,
    Tag,
    Info,
    X,
} from "lucide-react";
import { PlatformIcon, getPlatformLabel } from "@/components/accounts/platform-icon";

interface Campaign {
    id: string;
    platform_campaign_id: string;
    name: string;
    status: string;
    campaign_type?: string;
    daily_budget?: number;
    budget_currency?: string;
    start_date?: string;
    end_date?: string;
    created_at?: string;
    updated_at?: string;
}

interface AccountWithCampaigns extends Account {
    campaigns: Campaign[];
    isExpanded: boolean;
    isLoading: boolean;
}

export default function CampaignsPage() {
    const { hydrate, isAuthenticated } = useAuthStore();
    const [accountsWithCampaigns, setAccountsWithCampaigns] = useState<AccountWithCampaigns[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");
    const [accountSearchQuery, setAccountSearchQuery] = useState("");
    const [statusFilter, setStatusFilter] = useState<string>("all");
    const [isSyncingAll, setIsSyncingAll] = useState(false);
    const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null);
    const [selectedAccountName, setSelectedAccountName] = useState<string>("");

    useEffect(() => {
        hydrate();
    }, [hydrate]);

    useEffect(() => {
        if (isAuthenticated) {
            fetchAccounts();
        } else {
            setIsLoading(false);
        }
    }, [isAuthenticated]);

    const fetchAccounts = async () => {
        try {
            setIsLoading(true);
            const response = await api.get<AccountsListResponse>("/api/v1/accounts");
            const accounts = response.data.accounts || (Array.isArray(response.data) ? response.data : []);

            // Initialize accounts with empty campaigns
            const accountsData: AccountWithCampaigns[] = accounts.map((acc: Account) => ({
                ...acc,
                campaigns: [],
                isExpanded: true, // Start expanded
                isLoading: false,
            }));

            setAccountsWithCampaigns(accountsData);

            // Fetch campaigns for all accounts in parallel
            const updatedAccounts = await Promise.all(
                accountsData.map(async (acc) => {
                    try {
                        const campaignsRes = await api.get<{ campaigns: Campaign[] }>(
                            `/api/v1/accounts/${acc.id}/campaigns`
                        );
                        return {
                            ...acc,
                            campaigns: campaignsRes.data.campaigns || [],
                            isLoading: false,
                        };
                    } catch (error) {
                        console.error(`Failed to fetch campaigns for ${acc.id}:`, error);
                        return { ...acc, campaigns: [], isLoading: false };
                    }
                })
            );

            setAccountsWithCampaigns(updatedAccounts);
        } catch (error) {
            console.error("Failed to fetch accounts:", error);
        } finally {
            setIsLoading(false);
        }
    };

    const toggleAccount = (accountId: string) => {
        setAccountsWithCampaigns((prev) =>
            prev.map((acc) =>
                acc.id === accountId ? { ...acc, isExpanded: !acc.isExpanded } : acc
            )
        );
    };

    const handleSyncAccount = async (accountId: string) => {
        setAccountsWithCampaigns((prev) =>
            prev.map((acc) =>
                acc.id === accountId ? { ...acc, isLoading: true } : acc
            )
        );

        try {
            await api.post(`/api/v1/accounts/${accountId}/sync`);
            // Refresh campaigns for this account
            const campaignsRes = await api.get<{ campaigns: Campaign[] }>(
                `/api/v1/accounts/${accountId}/campaigns`
            );
            setAccountsWithCampaigns((prev) =>
                prev.map((acc) =>
                    acc.id === accountId
                        ? { ...acc, campaigns: campaignsRes.data.campaigns || [], isLoading: false }
                        : acc
                )
            );
        } catch (error) {
            console.error("Sync failed:", error);
            setAccountsWithCampaigns((prev) =>
                prev.map((acc) =>
                    acc.id === accountId ? { ...acc, isLoading: false } : acc
                )
            );
        }
    };

    const handleSyncAll = async () => {
        setIsSyncingAll(true);
        try {
            for (const account of accountsWithCampaigns) {
                try {
                    await api.post(`/api/v1/accounts/${account.id}/sync`);
                } catch (err) {
                    console.error(`Sync failed for ${account.id}:`, err);
                }
            }
            // Refresh all
            await fetchAccounts();
        } finally {
            setIsSyncingAll(false);
        }
    };

    const openCampaignDetails = (campaign: Campaign, accountName: string) => {
        setSelectedCampaign(campaign);
        setSelectedAccountName(accountName);
    };

    const closeCampaignDetails = () => {
        setSelectedCampaign(null);
        setSelectedAccountName("");
    };

    const getStatusBadge = (status: string, size: "sm" | "md" = "sm") => {
        const sizeClass = size === "md" ? "text-sm px-3 py-1" : "text-xs";
        switch (status) {
            case "enabled":
                return <Badge variant="success" className={sizeClass}><TrendingUp size={size === "md" ? 14 : 10} className="mr-1" />Aktif</Badge>;
            case "paused":
                return <Badge variant="warning" className={sizeClass}><Pause size={size === "md" ? 14 : 10} className="mr-1" />Durduruldu</Badge>;
            case "removed":
                return <Badge variant="secondary" className={sizeClass}><Trash2 size={size === "md" ? 14 : 10} className="mr-1" />Silindi</Badge>;
            default:
                return <Badge variant="secondary" className={sizeClass}>{status}</Badge>;
        }
    };

    const formatCampaignType = (type?: string) => {
        if (!type) return "Bilinmiyor";
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

    const formatBudget = (budget?: number, currency?: string) => {
        if (!budget) return "Belirtilmemiş";
        return new Intl.NumberFormat("tr-TR", {
            style: "currency",
            currency: currency || "TRY",
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(budget);
    };

    const formatDate = (dateStr?: string) => {
        if (!dateStr) return "Belirtilmemiş";
        return new Date(dateStr).toLocaleDateString("tr-TR", {
            day: "numeric",
            month: "long",
            year: "numeric",
        });
    };

    // Filter accounts by search
    const filterAccounts = (accounts: AccountWithCampaigns[]) => {
        if (!accountSearchQuery) return accounts;
        return accounts.filter((acc) => {
            const name = acc.account_name || acc.platform_account_name || acc.platform_account_id;
            return name.toLowerCase().includes(accountSearchQuery.toLowerCase());
        });
    };

    // Filter campaigns based on search and status
    const filterCampaigns = (campaigns: Campaign[]) => {
        return campaigns.filter((campaign) => {
            const matchesSearch = searchQuery === "" ||
                campaign.name.toLowerCase().includes(searchQuery.toLowerCase());
            const matchesStatus = statusFilter === "all" || campaign.status === statusFilter;
            return matchesSearch && matchesStatus;
        });
    };

    // Get total counts
    const filteredAccounts = filterAccounts(accountsWithCampaigns);
    const totalCampaigns = accountsWithCampaigns.reduce((sum, acc) => sum + acc.campaigns.length, 0);
    const activeCampaigns = accountsWithCampaigns.reduce(
        (sum, acc) => sum + acc.campaigns.filter((c) => c.status === "enabled").length,
        0
    );

    if (isLoading) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <Loader2 className="animate-spin text-primary" size={40} />
            </div>
        );
    }

    return (
        <div className="flex-1">
            <Header
                title="Kampanyalar"
                subtitle="Tüm hesaplarınızdaki kampanyaları görüntüleyin"
            />

            <div className="p-6 space-y-6">
                {/* Stats */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Card className="bg-white border-primary-light  ">
                        <CardContent className="p-4">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-lg bg-blue-100  flex items-center justify-center">
                                    <Building2 size={20} className="text-blue-600" />
                                </div>
                                <div>
                                    <p className="text-2xl font-bold">{accountsWithCampaigns.length}</p>
                                    <p className="text-sm text-muted-foreground">Hesap</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                    <Card className="bg-white border-primary-light  ">
                        <CardContent className="p-4">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-lg bg-purple-100  flex items-center justify-center">
                                    <Target size={20} className="text-purple-600" />
                                </div>
                                <div>
                                    <p className="text-2xl font-bold">{totalCampaigns}</p>
                                    <p className="text-sm text-muted-foreground">Toplam Kampanya</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                    <Card className="bg-white border-primary-light  ">
                        <CardContent className="p-4">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-lg bg-green-100  flex items-center justify-center">
                                    <TrendingUp size={20} className="text-green-600" />
                                </div>
                                <div>
                                    <p className="text-2xl font-bold">{activeCampaigns}</p>
                                    <p className="text-sm text-muted-foreground">Aktif Kampanya</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Filters */}
                <div className="flex items-center justify-between flex-wrap gap-4">
                    <div className="flex items-center gap-3 flex-wrap">
                        {/* Account Search */}
                        <div className="relative">
                            <Building2 size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                            <input
                                type="text"
                                placeholder="Hesap ara..."
                                value={accountSearchQuery}
                                onChange={(e) => setAccountSearchQuery(e.target.value)}
                                className="pl-9 pr-4 py-2 border border-primary-light rounded-lg text-sm w-48 focus:outline-none focus:ring-2 focus:ring-primary   "
                            />
                        </div>
                        {/* Campaign Search */}
                        <div className="relative">
                            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                            <input
                                type="text"
                                placeholder="Kampanya ara..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="pl-9 pr-4 py-2 border border-primary-light rounded-lg text-sm w-56 focus:outline-none focus:ring-2 focus:ring-primary   "
                            />
                        </div>
                        {/* Status filter */}
                        <select
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                            className="px-4 py-2 border border-primary-light rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary   "
                        >
                            <option value="all">Tüm Durumlar</option>
                            <option value="enabled">Aktif</option>
                            <option value="paused">Durduruldu</option>
                            <option value="removed">Silindi</option>
                        </select>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button
                            variant="outline"
                            onClick={() => {
                                const allExpanded = accountsWithCampaigns.every(a => a.isExpanded);
                                setAccountsWithCampaigns(prev =>
                                    prev.map(acc => ({ ...acc, isExpanded: !allExpanded }))
                                );
                            }}
                            className="border-primary-light"
                        >
                            {accountsWithCampaigns.every(a => a.isExpanded) ? (
                                <>
                                    <ChevronRight size={16} className="mr-2" />
                                    Tümünü Gizle
                                </>
                            ) : (
                                <>
                                    <ChevronDown size={16} className="mr-2" />
                                    Tümünü Göster
                                </>
                            )}
                        </Button>
                        <Button
                            variant="outline"
                            onClick={handleSyncAll}
                            disabled={isSyncingAll}
                            className="border-primary-light"
                        >
                            {isSyncingAll ? (
                                <>
                                    <Loader2 size={16} className="animate-spin mr-2" />
                                    Senkronize Ediliyor...
                                </>
                            ) : (
                                <>
                                    <RefreshCw size={16} className="mr-2" />
                                    Tümünü Senkronize Et
                                </>
                            )}
                        </Button>
                    </div>
                </div>

                {/* Accounts with Campaigns Tree */}
                <div className="space-y-3">
                    {filteredAccounts.map((account) => {
                        const filteredCampaigns = filterCampaigns(account.campaigns);
                        const accountName = account.account_name || account.platform_account_name || account.platform_account_id;

                        // Hide accounts with no matching campaigns if filtering
                        if ((searchQuery || statusFilter !== "all") && filteredCampaigns.length === 0) {
                            return null;
                        }

                        return (
                            <Card key={account.id} className="bg-white border-primary-light   overflow-hidden">
                                {/* Account Header */}
                                <div
                                    className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50  transition-colors"
                                    onClick={() => toggleAccount(account.id)}
                                >
                                    <div className="flex items-center gap-3">
                                        <button className="p-1 hover:bg-gray-200  rounded transition-colors">
                                            {account.isExpanded ? (
                                                <ChevronDown size={20} className="text-muted-foreground" />
                                            ) : (
                                                <ChevronRight size={20} className="text-muted-foreground" />
                                            )}
                                        </button>
                                        <PlatformIcon platform={account.platform} size={32} />
                                        <div>
                                            <h3 className="font-semibold">{accountName}</h3>
                                            <p className="text-sm text-muted-foreground">
                                                {getPlatformLabel(account.platform)} • {account.platform_account_id}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3" onClick={(e) => e.stopPropagation()}>
                                        <Badge variant="secondary" className="text-xs">
                                            {account.campaigns.length} kampanya
                                        </Badge>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => handleSyncAccount(account.id)}
                                            disabled={account.isLoading}
                                        >
                                            <RefreshCw size={14} className={account.isLoading ? "animate-spin mr-1" : "mr-1"} />
                                            Senkronize Et
                                        </Button>
                                    </div>
                                </div>

                                {/* Campaigns List */}
                                {account.isExpanded && (
                                    <div className="border-t border-primary-light  bg-gray-50 ">
                                        {account.isLoading ? (
                                            <div className="flex items-center justify-center py-8">
                                                <Loader2 size={24} className="animate-spin text-muted-foreground" />
                                                <span className="ml-2 text-sm text-muted-foreground">Kampanyalar yükleniyor...</span>
                                            </div>
                                        ) : filteredCampaigns.length === 0 ? (
                                            <div className="text-center py-8 text-muted-foreground">
                                                <Target size={32} className="mx-auto mb-2 opacity-50" />
                                                <p className="text-sm">
                                                    {searchQuery || statusFilter !== "all"
                                                        ? "Filtreye uyan kampanya bulunamadı."
                                                        : "Bu hesapta kampanya bulunamadı."}
                                                </p>
                                                {!searchQuery && statusFilter === "all" && (
                                                    <p className="text-xs mt-1">Hesabı senkronize ederek kampanya verilerini çekebilirsiniz.</p>
                                                )}
                                            </div>
                                        ) : (
                                            <div className="divide-y divide-primary-light ">
                                                {filteredCampaigns.map((campaign) => (
                                                    <div
                                                        key={campaign.id}
                                                        className="flex items-center justify-between px-4 py-3 pl-14 hover:bg-gray-100  transition-colors cursor-pointer"
                                                        onClick={() => openCampaignDetails(campaign, accountName)}
                                                    >
                                                        <div className="flex items-center gap-3 flex-1 min-w-0">
                                                            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                                                                <Target size={14} className="text-primary" />
                                                            </div>
                                                            <div className="flex-1 min-w-0">
                                                                <p className="font-medium text-sm truncate">{campaign.name}</p>
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
                                                        <div className="flex items-center gap-2 ml-4">
                                                            {getStatusBadge(campaign.status)}
                                                            <Info size={16} className="text-muted-foreground" />
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </Card>
                        );
                    })}
                </div>

                {/* Empty state */}
                {accountsWithCampaigns.length === 0 && (
                    <Card className="bg-white border-primary-light  ">
                        <CardContent className="py-12 text-center">
                            <Target size={48} className="mx-auto text-muted-foreground mb-4" />
                            <h3 className="text-lg font-semibold mb-2">Henüz Hesap Yok</h3>
                            <p className="text-muted-foreground">
                                Kampanyaları görüntülemek için önce bir reklam hesabı bağlayın.
                            </p>
                        </CardContent>
                    </Card>
                )}
            </div>

            {/* Campaign Details Sidebar */}
            {selectedCampaign && (
                <>
                    {/* Overlay */}
                    <div
                        className="fixed inset-0 bg-black/30 z-40"
                        onClick={closeCampaignDetails}
                    />
                    {/* Sidebar */}
                    <div className="fixed right-0 top-0 h-full w-96 bg-white  shadow-xl z-50 overflow-y-auto">
                        {/* Header */}
                        <div className="sticky top-0 bg-white  border-b border-gray-200  p-4 flex items-center justify-between">
                            <h2 className="text-lg font-semibold">Kampanya Detayları</h2>
                            <button
                                onClick={closeCampaignDetails}
                                className="p-2 hover:bg-gray-100  rounded-lg transition-colors"
                            >
                                <X size={20} />
                            </button>
                        </div>

                        {/* Content */}
                        <div className="p-4 space-y-6">
                            {/* Campaign Name & Status */}
                            <div>
                                <div className="flex items-start justify-between gap-3">
                                    <div className="flex items-center gap-3">
                                        <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                                            <Target size={24} className="text-primary" />
                                        </div>
                                        <div>
                                            <h3 className="font-semibold text-lg">{selectedCampaign.name}</h3>
                                            <p className="text-sm text-muted-foreground">{selectedAccountName}</p>
                                        </div>
                                    </div>
                                </div>
                                <div className="mt-3">
                                    {getStatusBadge(selectedCampaign.status, "md")}
                                </div>
                            </div>

                            {/* Details Grid */}
                            <div className="space-y-4">
                                {/* Campaign Type */}
                                <div className="flex items-center gap-3 p-3 bg-gray-50  rounded-lg">
                                    <Tag size={18} className="text-muted-foreground" />
                                    <div>
                                        <p className="text-xs text-muted-foreground">Kampanya Türü</p>
                                        <p className="font-medium">{formatCampaignType(selectedCampaign.campaign_type)}</p>
                                    </div>
                                </div>

                                {/* Daily Budget */}
                                <div className="flex items-center gap-3 p-3 bg-gray-50  rounded-lg">
                                    <DollarSign size={18} className="text-muted-foreground" />
                                    <div>
                                        <p className="text-xs text-muted-foreground">Günlük Bütçe</p>
                                        <p className="font-medium">{formatBudget(selectedCampaign.daily_budget, selectedCampaign.budget_currency)}</p>
                                    </div>
                                </div>

                                {/* Platform Campaign ID */}
                                <div className="flex items-center gap-3 p-3 bg-gray-50  rounded-lg">
                                    <Info size={18} className="text-muted-foreground" />
                                    <div>
                                        <p className="text-xs text-muted-foreground">Platform Kampanya ID</p>
                                        <p className="font-medium font-mono text-sm">{selectedCampaign.platform_campaign_id}</p>
                                    </div>
                                </div>

                                {/* Start Date */}
                                {selectedCampaign.start_date && (
                                    <div className="flex items-center gap-3 p-3 bg-gray-50  rounded-lg">
                                        <Calendar size={18} className="text-muted-foreground" />
                                        <div>
                                            <p className="text-xs text-muted-foreground">Başlangıç Tarihi</p>
                                            <p className="font-medium">{formatDate(selectedCampaign.start_date)}</p>
                                        </div>
                                    </div>
                                )}

                                {/* End Date */}
                                {selectedCampaign.end_date && (
                                    <div className="flex items-center gap-3 p-3 bg-gray-50  rounded-lg">
                                        <Calendar size={18} className="text-muted-foreground" />
                                        <div>
                                            <p className="text-xs text-muted-foreground">Bitiş Tarihi</p>
                                            <p className="font-medium">{formatDate(selectedCampaign.end_date)}</p>
                                        </div>
                                    </div>
                                )}

                                {/* Created At */}
                                {selectedCampaign.created_at && (
                                    <div className="flex items-center gap-3 p-3 bg-gray-50  rounded-lg">
                                        <Calendar size={18} className="text-muted-foreground" />
                                        <div>
                                            <p className="text-xs text-muted-foreground">Oluşturulma Tarihi</p>
                                            <p className="font-medium">{formatDate(selectedCampaign.created_at)}</p>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Note */}
                            <div className="p-4 bg-blue-50  rounded-lg">
                                <p className="text-sm text-blue-700 ">
                                    <strong>Not:</strong> Bu kampanya Google Ads hesabınızdan senkronize edilmiştir.
                                    Kampanya ayarlarını değiştirmek için Google Ads panelini kullanın.
                                </p>
                            </div>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
