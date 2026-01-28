"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Eye, EyeOff, Loader2, Check } from "lucide-react";

export default function RegisterPage() {
    const [fullName, setFullName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);

        // TODO: Implement Supabase auth
        await new Promise((resolve) => setTimeout(resolve, 1000));

        // Redirect to dashboard
        window.location.href = "/dashboard";
    };

    const passwordRequirements = [
        { text: "En az 8 karakter", met: password.length >= 8 },
        { text: "Bir büyük harf", met: /[A-Z]/.test(password) },
        { text: "Bir rakam", met: /[0-9]/.test(password) },
    ];

    return (
        <Card className="w-full max-w-md bg-white border-primary-light shadow-lg">
            <CardHeader className="space-y-1 text-center">
                <div className="flex justify-center mb-4">
                    <div className="w-12 h-12 rounded-lg bg-primary flex items-center justify-center">
                        <span className="text-white font-bold text-2xl">A</span>
                    </div>
                </div>
                <CardTitle className="text-2xl font-bold">Hesap Oluştur</CardTitle>
                <CardDescription>
                    14 gün ücretsiz deneyin
                </CardDescription>
            </CardHeader>
            <form onSubmit={handleSubmit}>
                <CardContent className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="fullName">Ad Soyad</Label>
                        <Input
                            id="fullName"
                            type="text"
                            placeholder="John Doe"
                            value={fullName}
                            onChange={(e) => setFullName(e.target.value)}
                            required
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="email">Email</Label>
                        <Input
                            id="email"
                            type="email"
                            placeholder="ornek@email.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="password">Şifre</Label>
                        <div className="relative">
                            <Input
                                id="password"
                                type={showPassword ? "text" : "password"}
                                placeholder="••••••••"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                            />
                            <button
                                type="button"
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                onClick={() => setShowPassword(!showPassword)}
                            >
                                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
                        </div>
                        {/* Password requirements */}
                        <div className="mt-2 space-y-1">
                            {passwordRequirements.map((req, i) => (
                                <div
                                    key={i}
                                    className={`flex items-center gap-2 text-xs ${req.met ? "text-success" : "text-muted-foreground"
                                        }`}
                                >
                                    <Check size={14} />
                                    <span>{req.text}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </CardContent>
                <CardFooter className="flex flex-col gap-4">
                    <Button
                        type="submit"
                        className="w-full"
                        disabled={isLoading}
                    >
                        {isLoading && <Loader2 className="animate-spin mr-2" size={18} />}
                        Kayıt Ol
                    </Button>
                    <p className="text-sm text-muted-foreground text-center">
                        Zaten hesabınız var mı?{" "}
                        <Link href="/login" className="text-primary hover:underline font-medium">
                            Giriş Yap
                        </Link>
                    </p>
                </CardFooter>
            </form>
        </Card>
    );
}
