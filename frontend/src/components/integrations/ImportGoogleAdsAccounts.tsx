"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/services/api";
import {
    Download,
    X,
    Loader2,
    CheckCircle,
    AlertCircle,
    Check,
    RefreshCw
} from "lucide-react";

interface AvailableAccount {
    id: string;
    name: string;
    currency: string | null;
    timezone: string | null;
    is_manager: boolean;
    already_connected: boolean;
}

interface ImportGoogleAdsAccountsProps {
    onSuccess?: () => void;
}

export function ImportGoogleAdsAccounts({ onSuccess }: ImportGoogleAdsAccountsProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [isImporting, setIsImporting] = useState(false);
    const [accounts, setAccounts] = useState<AvailableAccount[]>([]);
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    const [error, setError] = useState<string | null>(null);
    const [importResults, setImportResults] = useState<{
        success: boolean;
        imported_count: number;
        failed_count: number;
    } | null>(null);
    const abortControllerRef = useRef<AbortController | null>(null);

    const fetchAvailableAccounts = async () => {
        // Cancel previous request if exists
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
        abortControllerRef.current = new AbortController();

        setIsLoading(true);
        setError(null);
        try {
            const response = await api.get<{
                success: boolean;
                accounts: AvailableAccount[];
                message?: string;
            }>("/api/v1/accounts/available/google-ads", {
                signal: abortControllerRef.current.signal,
            });

            if (response.data.success) {
                setAccounts(response.data.accounts);
                // Pre-select accounts that are not already connected
                const notConnected = response.data.accounts
                    .filter(a => !a.already_connected && !a.is_manager)
                    .map(a => a.id);
                setSelectedIds(new Set(notConnected));
            } else {
                setError(response.data.message || "Hesaplar yüklenemedi");
            }
        } catch (err: unknown) {
            // Ignore abort errors
            if (err instanceof Error && err.name === 'CanceledError') {
                return;
            }
            const error = err as { response?: { data?: { detail?: string } } };
            setError(error.response?.data?.detail || "Hesaplar yüklenirken bir hata oluştu");
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        if (isOpen) {
            fetchAvailableAccounts();
        }
        return () => {
            // Cleanup: cancel pending request when modal closes
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, [isOpen]);

    const handleToggleSelect = (accountId: string) => {
        const newSelected = new Set(selectedIds);
        if (newSelected.has(accountId)) {
            newSelected.delete(accountId);
        } else {
            newSelected.add(accountId);
        }
        setSelectedIds(newSelected);
    };

    const handleSelectAll = () => {
        const importable = accounts.filter(a => !a.already_connected && !a.is_manager);
        if (selectedIds.size === importable.length) {
            setSelectedIds(new Set());
        } else {
            setSelectedIds(new Set(importable.map(a => a.id)));
        }
    };

    const handleImportAll = async () => {
        const importable = accounts.filter(a => !a.already_connected && !a.is_manager);
        if (importable.length === 0) return;

        const allIds = importable.map(a => a.id);

        setIsImporting(true);
        setError(null);
        setImportResults(null);

        try {
            const response = await api.post<{
                success: boolean;
                imported_count: number;
                failed_count: number;
            }>("/api/v1/accounts/import/google-ads", {
                account_ids: allIds,
            });

            setImportResults(response.data);

            if (response.data.imported_count > 0) {
                await fetchAvailableAccounts();
                setSelectedIds(new Set());

                setTimeout(() => {
                    setIsOpen(false);
                    setImportResults(null);
                    onSuccess?.();
                }, 2000);
            }
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string } } };
            setError(error.response?.data?.detail || "İçe aktarma sırasında bir hata oluştu");
        } finally {
            setIsImporting(false);
        }
    };

    const handleImport = async () => {
        if (selectedIds.size === 0) return;

        setIsImporting(true);
        setError(null);
        setImportResults(null);

        try {
            const response = await api.post<{
                success: boolean;
                imported_count: number;
                failed_count: number;
            }>("/api/v1/accounts/import/google-ads", {
                account_ids: Array.from(selectedIds),
            });

            setImportResults(response.data);

            if (response.data.imported_count > 0) {
                // Refresh the list to show updated connection status
                await fetchAvailableAccounts();
                setSelectedIds(new Set());

                // Close after a delay and trigger success callback
                setTimeout(() => {
                    setIsOpen(false);
                    setImportResults(null);
                    onSuccess?.();
                }, 2000);
            }
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string } } };
            setError(error.response?.data?.detail || "İçe aktarma sırasında bir hata oluştu");
        } finally {
            setIsImporting(false);
        }
    };

    const importableAccounts = accounts.filter(a => !a.already_connected && !a.is_manager);
    const connectedAccounts = accounts.filter(a => a.already_connected);
    const managerAccounts = accounts.filter(a => a.is_manager && !a.already_connected);

    if (!isOpen) {
        return (
            <Button
                variant="outline"
                onClick={() => setIsOpen(true)}
                className="gap-2"
            >
                <Download size={16} />
                Google Ads'ten Aktar
            </Button>
        );
    }

    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
            <Card className="w-full max-w-2xl bg-white max-h-[80vh] flex flex-col">
                <CardHeader className="flex flex-row items-center justify-between border-b">
                    <CardTitle className="text-lg">Google Ads Hesaplarını İçe Aktar</CardTitle>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                            setIsOpen(false);
                            setError(null);
                            setImportResults(null);
                        }}
                    >
                        <X size={18} />
                    </Button>
                </CardHeader>
                <CardContent className="flex-1 overflow-auto p-4">
                    {isLoading ? (
                        <div className="flex items-center justify-center py-12">
                            <Loader2 className="animate-spin text-primary mr-2" size={24} />
                            <span>Hesaplar yükleniyor...</span>
                        </div>
                    ) : error ? (
                        <div className="text-center py-8">
                            <AlertCircle className="mx-auto text-red-500 mb-3" size={48} />
                            <p className="text-red-600 mb-4">{error}</p>
                            <Button variant="outline" onClick={fetchAvailableAccounts}>
                                <RefreshCw size={14} className="mr-1" />
                                Tekrar Dene
                            </Button>
                        </div>
                    ) : accounts.length === 0 ? (
                        <div className="text-center py-8">
                            <p className="text-muted-foreground">
                                Erişilebilir Google Ads hesabı bulunamadı.
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {/* Import Results */}
                            {importResults && (
                                <div className={`p-3 rounded-lg text-sm flex items-center gap-2 ${
                                    importResults.imported_count > 0
                                        ? "bg-green-50 text-green-700"
                                        : "bg-red-50 text-red-700"
                                }`}>
                                    {importResults.imported_count > 0 ? (
                                        <CheckCircle size={16} />
                                    ) : (
                                        <AlertCircle size={16} />
                                    )}
                                    <span>
                                        {importResults.imported_count} hesap başarıyla eklendi
                                        {importResults.failed_count > 0 &&
                                            `, ${importResults.failed_count} hesap eklenemedi`
                                        }
                                    </span>
                                </div>
                            )}

                            {/* Select All */}
                            {importableAccounts.length > 0 && (
                                <div className="flex items-center justify-between pb-2 border-b">
                                    <button
                                        type="button"
                                        onClick={handleSelectAll}
                                        className="text-sm text-primary hover:underline"
                                    >
                                        {selectedIds.size === importableAccounts.length
                                            ? "Seçimi Kaldır"
                                            : "Tümünü Seç"
                                        }
                                    </button>
                                    <span className="text-sm text-muted-foreground">
                                        {selectedIds.size} / {importableAccounts.length} seçili
                                    </span>
                                </div>
                            )}

                            {/* Importable Accounts */}
                            {importableAccounts.length > 0 && (
                                <div className="space-y-2">
                                    <h4 className="text-sm font-medium text-muted-foreground">
                                        İçe Aktarılabilir Hesaplar
                                    </h4>
                                    {importableAccounts.map((account) => (
                                        <div
                                            key={account.id}
                                            onClick={() => handleToggleSelect(account.id)}
                                            className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                                                selectedIds.has(account.id)
                                                    ? "border-primary bg-primary/5"
                                                    : "border-gray-200 hover:border-gray-300"
                                            }`}
                                        >
                                            <div className="flex items-center gap-3">
                                                <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                                                    selectedIds.has(account.id)
                                                        ? "bg-green-500 border-green-500"
                                                        : "border-gray-300 bg-white"
                                                }`}>
                                                    <Check
                                                        size={14}
                                                        strokeWidth={3}
                                                        className={selectedIds.has(account.id) ? "text-white" : "text-green-500"}
                                                    />
                                                </div>
                                                <div className="flex-1">
                                                    <p className="font-medium">{account.name}</p>
                                                    <p className="text-sm text-muted-foreground">
                                                        ID: {account.id}
                                                        {account.currency && ` • ${account.currency}`}
                                                    </p>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Manager Accounts (not selectable) */}
                            {managerAccounts.length > 0 && (
                                <div className="space-y-2 opacity-60">
                                    <h4 className="text-sm font-medium text-muted-foreground">
                                        MCC Hesapları (İçe aktarılamaz)
                                    </h4>
                                    {managerAccounts.map((account) => (
                                        <div
                                            key={account.id}
                                            className="p-3 rounded-lg border border-gray-200 bg-gray-50"
                                        >
                                            <p className="font-medium">{account.name}</p>
                                            <p className="text-sm text-muted-foreground">
                                                ID: {account.id} • Manager Account
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Already Connected */}
                            {connectedAccounts.length > 0 && (
                                <div className="space-y-2 opacity-60">
                                    <h4 className="text-sm font-medium text-muted-foreground">
                                        Zaten Bağlı
                                    </h4>
                                    {connectedAccounts.map((account) => (
                                        <div
                                            key={account.id}
                                            className="p-3 rounded-lg border border-gray-200 bg-gray-50"
                                        >
                                            <div className="flex items-center gap-2">
                                                <CheckCircle size={16} className="text-green-500" />
                                                <div>
                                                    <p className="font-medium">{account.name}</p>
                                                    <p className="text-sm text-muted-foreground">
                                                        ID: {account.id}
                                                    </p>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </CardContent>

                {/* Footer Actions */}
                {!isLoading && !error && importableAccounts.length > 0 && (
                    <div className="p-4 border-t flex gap-2">
                        <Button
                            variant="outline"
                            onClick={() => {
                                setIsOpen(false);
                                setError(null);
                                setImportResults(null);
                            }}
                        >
                            İptal
                        </Button>
                        <Button
                            variant="outline"
                            onClick={handleImportAll}
                            disabled={isImporting || importableAccounts.length === 0}
                        >
                            {isImporting ? (
                                <Loader2 size={16} className="animate-spin mr-1" />
                            ) : (
                                <Download size={16} className="mr-1" />
                            )}
                            Tümünü Ekle
                        </Button>
                        <Button
                            onClick={handleImport}
                            disabled={selectedIds.size === 0 || isImporting}
                            className="flex-1 bg-primary hover:bg-primary-dark text-white"
                        >
                            {isImporting ? (
                                <>
                                    <Loader2 size={16} className="animate-spin mr-1" />
                                    İçe Aktarılıyor...
                                </>
                            ) : (
                                <>
                                    <Download size={16} className="mr-1" />
                                    {selectedIds.size} Hesabı İçe Aktar
                                </>
                            )}
                        </Button>
                    </div>
                )}
            </Card>
        </div>
    );
}
