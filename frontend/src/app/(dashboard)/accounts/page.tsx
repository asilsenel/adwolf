"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PlatformIcon, getPlatformLabel } from "@/components/accounts/platform-icon";
import { ImportGoogleAdsAccounts } from "@/components/integrations/ImportGoogleAdsAccounts";
import { Plus, RefreshCw, Settings, Trash2, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import Link from "next/link";
import { api } from "@/services/api";
import { useAuthStore } from "@/store/authStore";

interface Account {
    id: string;
    platform: "google_ads" | "meta_ads";
    account_name: string;
    platform_account_id: string;
    status: string;
    last_sync_at: string | null;
    last_sync_status: string | null;
    is_active: boolean;
}

interface AccountsResponse {
    accounts: Account[];
}

export default function AccountsPage() {
    const { isAuthenticated, hydrate } = useAuthStore();
    const [accounts, setAccounts] = useState<Account[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSyncing, setIsSyncing] = useState<string | null>(null);

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
            const response = await api.get<AccountsResponse>("/api/v1/accounts");
            if (response.data.accounts) {
                setAccounts(response.data.accounts);
            } else if (Array.isArray(response.data)) {
                setAccounts(response.data as unknown as Account[]);
            }
        } catch (error) {
            console.log("Failed to fetch accounts:", error);
            setAccounts([]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSync = async (accountId: string) => {
        try {
            setIsSyncing(accountId);
            await api.post(`/api/v1/accounts/${accountId}/sync`);
            // Refresh accounts after a short delay
            setTimeout(() => fetchAccounts(), 2000);
        } catch (error) {
            console.error("Sync failed:", error);
        } finally {
            setIsSyncing(null);
        }
    };

    const formatLastSync = (lastSync: string | null) => {
        if (!lastSync) return "Hiç";
        try {
            const date = new Date(lastSync);
            const now = new Date();
            const diffMs = now.getTime() - date.getTime();
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMs / 3600000);
            const diffDays = Math.floor(diffMs / 86400000);

            if (diffMins < 1) return "Az önce";
            if (diffMins < 60) return `${diffMins} dakika önce`;
            if (diffHours < 24) return `${diffHours} saat önce`;
            return `${diffDays} gün önce`;
        } catch {
            return lastSync;
        }
    };

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
                title="Hesaplar"
                subtitle="Bağlı reklam hesaplarınızı yönetin"
            />

            <div className="p-6 space-y-6">
                {/* Account Actions */}
                <div className="flex justify-end gap-2">
                    <ImportGoogleAdsAccounts onSuccess={fetchAccounts} />
                    <Link href="/accounts/connect">
                        <Button>
                            <Plus size={18} />
                            Hesap Bağla
                        </Button>
                    </Link>
                </div>

                {/* Account Cards */}
                {accounts.length > 0 && (
                    <div className="grid gap-4 md:grid-cols-2">
                        {accounts.map((account) => (
                            <Card
                                key={account.id}
                                className="bg-white border-primary-light hover:shadow-md transition-shadow"
                            >
                                <CardHeader className="flex flex-row items-start justify-between space-y-0">
                                    <div className="flex items-center gap-3">
                                        <PlatformIcon platform={account.platform} size={40} />
                                        <div>
                                            <CardTitle className="text-lg">{account.account_name || "Reklam Hesabı"}</CardTitle>
                                            <CardDescription className="flex items-center gap-2 mt-1">
                                                <span>{getPlatformLabel(account.platform)}</span>
                                                <span>•</span>
                                                <span>{account.platform_account_id}</span>
                                            </CardDescription>
                                        </div>
                                    </div>
                                    <Badge
                                        variant={account.is_active ? "success" : "destructive"}
                                        className="flex items-center gap-1"
                                    >
                                        {account.is_active ? (
                                            <>
                                                <CheckCircle size={12} />
                                                Aktif
                                            </>
                                        ) : (
                                            <>
                                                <AlertCircle size={12} />
                                                Pasif
                                            </>
                                        )}
                                    </Badge>
                                </CardHeader>
                                <CardContent>
                                    {/* Stats */}
                                    <div className="grid grid-cols-2 gap-4 mb-4">
                                        <div>
                                            <p className="text-sm text-muted-foreground">Son Sync</p>
                                            <p className="text-lg font-semibold">{formatLastSync(account.last_sync_at)}</p>
                                        </div>
                                        <div>
                                            <p className="text-sm text-muted-foreground">Durum</p>
                                            <p className="text-lg font-semibold capitalize">
                                                {account.last_sync_status || "Bekliyor"}
                                            </p>
                                        </div>
                                    </div>

                                    {/* Actions */}
                                    <div className="flex gap-2 pt-4 border-t border-primary-light">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="flex-1"
                                            onClick={() => handleSync(account.id)}
                                            disabled={isSyncing === account.id}
                                        >
                                            <RefreshCw size={14} className={isSyncing === account.id ? "animate-spin" : ""} />
                                            {isSyncing === account.id ? "Senkronize Ediliyor..." : "Senkronize Et"}
                                        </Button>
                                        <Button variant="outline" size="sm">
                                            <Settings size={14} />
                                        </Button>
                                        <Button variant="outline" size="sm" className="text-danger hover:text-danger">
                                            <Trash2 size={14} />
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                )}

                {/* Empty State */}
                {accounts.length === 0 && (
                    <Card className="bg-white border-primary-light">
                        <CardContent className="py-12 text-center">
                            <div className="w-16 h-16 rounded-full bg-cream mx-auto mb-4 flex items-center justify-center">
                                <Plus size={32} className="text-primary" />
                            </div>
                            <h3 className="text-lg font-semibold mb-2">Henüz hesap bağlanmadı</h3>
                            <p className="text-muted-foreground mb-4">
                                Reklam hesaplarınızı bağlayarak başlayın
                            </p>
                            <Link href="/accounts/connect">
                                <Button>
                                    <Plus size={18} />
                                    İlk Hesabı Bağla
                                </Button>
                            </Link>
                        </CardContent>
                    </Card>
                )}
            </div>
        </div>
    );
}
