"use client";

import { Header } from "@/components/layout/header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { User, Bell, Shield, CreditCard, Mail, Smartphone } from "lucide-react";

export default function SettingsPage() {
    return (
        <div className="flex-1">
            <Header
                title="Ayarlar"
                subtitle="Hesap ve uygulama ayarlarınızı yönetin"
            />

            <div className="p-6 space-y-6 max-w-4xl">
                {/* Profile */}
                <Card className="bg-white border-primary-light">
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <User size={20} className="text-primary" />
                            <CardTitle>Profil</CardTitle>
                        </div>
                        <CardDescription>Hesap bilgilerinizi güncelleyin</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid gap-4 md:grid-cols-2">
                            <div className="space-y-2">
                                <Label htmlFor="name">Ad Soyad</Label>
                                <Input id="name" defaultValue="John Doe" />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="email">Email</Label>
                                <Input id="email" type="email" defaultValue="john@example.com" />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="company">Şirket</Label>
                            <Input id="company" defaultValue="Acme Inc." />
                        </div>
                        <Button>Kaydet</Button>
                    </CardContent>
                </Card>

                {/* Notifications */}
                <Card className="bg-white border-primary-light">
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <Bell size={20} className="text-primary" />
                            <CardTitle>Bildirimler</CardTitle>
                        </div>
                        <CardDescription>Bildirim tercihlerinizi ayarlayın</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex items-center justify-between py-2">
                            <div className="flex items-center gap-3">
                                <Mail size={18} className="text-muted-foreground" />
                                <div>
                                    <p className="font-medium">Email Bildirimleri</p>
                                    <p className="text-sm text-muted-foreground">Günlük özet ve önemli uyarılar</p>
                                </div>
                            </div>
                            <Button variant="outline" size="sm">Açık</Button>
                        </div>
                        <div className="flex items-center justify-between py-2 border-t border-primary-light">
                            <div className="flex items-center gap-3">
                                <Smartphone size={18} className="text-muted-foreground" />
                                <div>
                                    <p className="font-medium">WhatsApp Bildirimleri</p>
                                    <p className="text-sm text-muted-foreground">Anlık uyarılar ve günlük özet</p>
                                </div>
                            </div>
                            <Button variant="outline" size="sm">Kapalı</Button>
                        </div>
                    </CardContent>
                </Card>

                {/* Subscription */}
                <Card className="bg-white border-primary-light">
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <CreditCard size={20} className="text-primary" />
                                <CardTitle>Abonelik</CardTitle>
                            </div>
                            <Badge variant="success">Aktif</Badge>
                        </div>
                        <CardDescription>Mevcut plan ve ödeme bilgileri</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="p-4 bg-cream rounded-lg">
                            <div className="flex items-center justify-between mb-2">
                                <h4 className="font-semibold">Pro Plan</h4>
                                <span className="text-lg font-bold text-primary">₺499/ay</span>
                            </div>
                            <ul className="text-sm text-muted-foreground space-y-1">
                                <li>✓ Sınırsız hesap bağlantısı</li>
                                <li>✓ AI-powered öneriler</li>
                                <li>✓ Günlük özet raporları</li>
                                <li>✓ Öncelikli destek</li>
                            </ul>
                        </div>
                        <div className="flex gap-2">
                            <Button variant="outline">Plan Değiştir</Button>
                            <Button variant="outline">Fatura Geçmişi</Button>
                        </div>
                    </CardContent>
                </Card>

                {/* Security */}
                <Card className="bg-white border-primary-light">
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <Shield size={20} className="text-primary" />
                            <CardTitle>Güvenlik</CardTitle>
                        </div>
                        <CardDescription>Şifre ve güvenlik ayarları</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <Button variant="outline">Şifreyi Değiştir</Button>
                        <div className="pt-4 border-t border-primary-light">
                            <Button variant="destructive">Hesabı Sil</Button>
                            <p className="text-xs text-muted-foreground mt-2">
                                Bu işlem geri alınamaz. Tüm verileriniz silinecektir.
                            </p>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
