"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/services/api";
import { Plus, X, Loader2, CheckCircle, AlertCircle } from "lucide-react";

interface AddAccountByIdProps {
    onSuccess?: () => void;
}

export function AddAccountById({ onSuccess }: AddAccountByIdProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [accountId, setAccountId] = useState("");
    const [accountName, setAccountName] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    const formatAccountId = (value: string): string => {
        // Remove all non-digits
        const digits = value.replace(/\D/g, "");
        // Format as XXX-XXX-XXXX if long enough
        if (digits.length >= 10) {
            return `${digits.slice(0, 3)}-${digits.slice(3, 6)}-${digits.slice(6, 10)}`;
        }
        return digits;
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const formatted = formatAccountId(e.target.value);
        setAccountId(formatted);
        setError(null);
        setSuccess(null);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        // Validate
        const digits = accountId.replace(/\D/g, "");
        if (digits.length < 8) {
            setError("Hesap ID'si en az 8 rakam olmalı");
            return;
        }

        setIsLoading(true);
        setError(null);
        setSuccess(null);

        try {
            const response = await api.post("/api/v1/accounts/add-by-id", {
                account_id: digits,
                account_name: accountName || undefined,
            });

            if (response.data.success) {
                setSuccess(response.data.message);
                setAccountId("");
                setAccountName("");

                // Call success callback after short delay
                setTimeout(() => {
                    setIsOpen(false);
                    setSuccess(null);
                    onSuccess?.();
                }, 2000);
            }
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string } } };
            setError(error.response?.data?.detail || "Hesap eklenirken bir hata oluştu");
        } finally {
            setIsLoading(false);
        }
    };

    if (!isOpen) {
        return (
            <Button
                variant="outline"
                size="sm"
                onClick={() => setIsOpen(true)}
                className="gap-1"
            >
                <Plus size={14} />
                ID ile Ekle
            </Button>
        );
    }

    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
            <Card className="w-full max-w-md bg-white">
                <CardHeader className="flex flex-row items-center justify-between">
                    <CardTitle className="text-lg">Google Ads Hesabı Ekle</CardTitle>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                            setIsOpen(false);
                            setError(null);
                            setSuccess(null);
                        }}
                    >
                        <X size={18} />
                    </Button>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium mb-1.5">
                                Hesap ID <span className="text-muted-foreground">(zorunlu)</span>
                            </label>
                            <input
                                type="text"
                                value={accountId}
                                onChange={handleInputChange}
                                placeholder="813-075-0937 veya 8130750937"
                                className="w-full px-3 py-2 border border-primary-light rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                disabled={isLoading}
                            />
                            <p className="text-xs text-muted-foreground mt-1">
                                Google Ads hesap numarası (MCC altında olmalı)
                            </p>
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-1.5">
                                Hesap Adı <span className="text-muted-foreground">(opsiyonel)</span>
                            </label>
                            <input
                                type="text"
                                value={accountName}
                                onChange={(e) => setAccountName(e.target.value)}
                                placeholder="Örn: Ana Marka Hesabı"
                                className="w-full px-3 py-2 border border-primary-light rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                disabled={isLoading}
                            />
                            <p className="text-xs text-muted-foreground mt-1">
                                Boş bırakırsanız Google Ads'ten otomatik alınır
                            </p>
                        </div>

                        {error && (
                            <div className="flex items-center gap-2 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
                                <AlertCircle size={16} />
                                {error}
                            </div>
                        )}

                        {success && (
                            <div className="flex items-center gap-2 p-3 bg-green-50 text-green-700 rounded-lg text-sm">
                                <CheckCircle size={16} />
                                {success}
                            </div>
                        )}

                        <div className="flex gap-2 pt-2">
                            <Button
                                type="button"
                                variant="outline"
                                onClick={() => {
                                    setIsOpen(false);
                                    setError(null);
                                    setSuccess(null);
                                }}
                                disabled={isLoading}
                                className="flex-1"
                            >
                                İptal
                            </Button>
                            <Button
                                type="submit"
                                disabled={isLoading || !accountId}
                                className="flex-1 bg-primary hover:bg-primary-dark text-white"
                            >
                                {isLoading ? (
                                    <>
                                        <Loader2 size={16} className="animate-spin mr-1" />
                                        Ekleniyor...
                                    </>
                                ) : (
                                    "Hesap Ekle"
                                )}
                            </Button>
                        </div>
                    </form>
                </CardContent>
            </Card>
        </div>
    );
}
