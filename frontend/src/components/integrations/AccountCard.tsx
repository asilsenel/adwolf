"use client";

import { Account } from "@/types/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PlatformIcon, getPlatformLabel } from "@/components/accounts/platform-icon";
import { RefreshCw, MoreVertical, CheckCircle, AlertCircle, Clock } from "lucide-react";

interface AccountCardProps {
    account: Account;
    onSync?: (accountId: string) => void;
}

export function AccountCard({ account, onSync }: AccountCardProps) {
    const statusConfig = {
        active: { icon: CheckCircle, color: "text-success", label: "Aktif", badge: "success" as const },
        paused: { icon: Clock, color: "text-warning", label: "Duraklatıldı", badge: "warning" as const },
        disconnected: { icon: AlertCircle, color: "text-muted-foreground", label: "Bağlantı Kesildi", badge: "secondary" as const },
        error: { icon: AlertCircle, color: "text-danger", label: "Hata", badge: "destructive" as const },
    };

    const status = statusConfig[account.status] || statusConfig.active;
    const StatusIcon = status.icon;

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return "Henüz senkronize edilmedi";
        const date = new Date(dateStr);
        return date.toLocaleString("tr-TR", {
            day: "numeric",
            month: "short",
            hour: "2-digit",
            minute: "2-digit",
        });
    };

    return (
        <Card className="bg-white  border-primary-light  hover:shadow-md transition-shadow">
            <CardContent className="p-4">
                <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                        <PlatformIcon platform={account.platform} size={40} />
                        <div>
                            <h3 className="font-semibold">
                                {account.account_name || account.platform_account_name || account.platform_account_id}
                            </h3>
                            <p className="text-sm text-muted-foreground">
                                {getPlatformLabel(account.platform)} • {account.platform_account_id}
                            </p>
                        </div>
                    </div>

                    <Badge variant={status.badge} className="flex items-center gap-1">
                        <StatusIcon size={12} />
                        {status.label}
                    </Badge>
                </div>

                <div className="flex items-center justify-between mt-4 pt-4 border-t border-primary-light ">
                    <span className="text-xs text-muted-foreground">
                        Son sync: {formatDate(account.last_sync_at)}
                    </span>

                    <div className="flex gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => onSync?.(account.id)}
                        >
                            <RefreshCw size={14} className="mr-1" />
                            Senkronize Et
                        </Button>
                        <Button variant="ghost" size="sm">
                            <MoreVertical size={14} />
                        </Button>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
