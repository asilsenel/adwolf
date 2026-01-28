"use client";

import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PlatformIcon, getPlatformLabel } from "@/components/accounts/platform-icon";
import { Plus, RefreshCw, Settings, Trash2, CheckCircle, AlertCircle } from "lucide-react";
import Link from "next/link";

// Mock data
const mockAccounts = [
    {
        id: "1",
        platform: "google_ads" as const,
        name: "Ana Google Hesabı",
        platformAccountId: "123-456-7890",
        status: "active",
        lastSync: "2 saat önce",
        spend30d: 7470,
        campaigns: 5,
    },
    {
        id: "2",
        platform: "meta_ads" as const,
        name: "Meta Business",
        platformAccountId: "act_987654321",
        status: "active",
        lastSync: "3 saat önce",
        spend30d: 4980,
        campaigns: 3,
    },
];

export default function AccountsPage() {
    return (
        <div className="flex-1">
            <Header
                title="Hesaplar"
                subtitle="Bağlı reklam hesaplarınızı yönetin"
            />

            <div className="p-6 space-y-6">
                {/* Add Account Button */}
                <div className="flex justify-end">
                    <Link href="/accounts/connect">
                        <Button>
                            <Plus size={18} />
                            Hesap Bağla
                        </Button>
                    </Link>
                </div>

                {/* Account Cards */}
                <div className="grid gap-4 md:grid-cols-2">
                    {mockAccounts.map((account) => (
                        <Card
                            key={account.id}
                            className="bg-white border-primary-light hover:shadow-md transition-shadow"
                        >
                            <CardHeader className="flex flex-row items-start justify-between space-y-0">
                                <div className="flex items-center gap-3">
                                    <PlatformIcon platform={account.platform} size={40} />
                                    <div>
                                        <CardTitle className="text-lg">{account.name}</CardTitle>
                                        <CardDescription className="flex items-center gap-2 mt-1">
                                            <span>{getPlatformLabel(account.platform)}</span>
                                            <span>•</span>
                                            <span>{account.platformAccountId}</span>
                                        </CardDescription>
                                    </div>
                                </div>
                                <Badge
                                    variant={account.status === "active" ? "success" : "destructive"}
                                    className="flex items-center gap-1"
                                >
                                    {account.status === "active" ? (
                                        <>
                                            <CheckCircle size={12} />
                                            Aktif
                                        </>
                                    ) : (
                                        <>
                                            <AlertCircle size={12} />
                                            Hata
                                        </>
                                    )}
                                </Badge>
                            </CardHeader>
                            <CardContent>
                                {/* Stats */}
                                <div className="grid grid-cols-3 gap-4 mb-4">
                                    <div>
                                        <p className="text-sm text-muted-foreground">30 Günlük Harcama</p>
                                        <p className="text-lg font-semibold">
                                            ₺{account.spend30d.toLocaleString("tr-TR")}
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-muted-foreground">Kampanyalar</p>
                                        <p className="text-lg font-semibold">{account.campaigns}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-muted-foreground">Son Sync</p>
                                        <p className="text-lg font-semibold">{account.lastSync}</p>
                                    </div>
                                </div>

                                {/* Actions */}
                                <div className="flex gap-2 pt-4 border-t border-primary-light">
                                    <Button variant="outline" size="sm" className="flex-1">
                                        <RefreshCw size={14} />
                                        Senkronize Et
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

                {/* Empty State */}
                {mockAccounts.length === 0 && (
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
