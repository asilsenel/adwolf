"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Eye, EyeOff, Loader2, AlertCircle } from "lucide-react";
import { useAuthStore } from "@/store/authStore";

export default function LoginPage() {
    const router = useRouter();
    const { login, isLoading, error, clearError, isAuthenticated, hydrate } = useAuthStore();

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);

    // Hydrate on mount (restore from localStorage)
    useEffect(() => {
        hydrate();
    }, [hydrate]);

    // Redirect if already authenticated
    useEffect(() => {
        if (isAuthenticated) {
            router.push("/dashboard");
        }
    }, [isAuthenticated, router]);

    // Clear error when inputs change
    useEffect(() => {
        if (error) {
            clearError();
        }
    }, [email, password]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        const success = await login(email, password);

        if (success) {
            router.push("/dashboard");
        }
    };

    return (
        <Card className="w-full max-w-md bg-white border-primary-light shadow-lg">
            <CardHeader className="space-y-1 text-center">
                <div className="flex justify-center mb-4">
                    <div className="w-12 h-12 rounded-lg bg-primary flex items-center justify-center">
                        <span className="text-white font-bold text-2xl">A</span>
                    </div>
                </div>
                <CardTitle className="text-2xl font-bold">Hoş Geldiniz</CardTitle>
                <CardDescription>
                    Hesabınıza giriş yapın
                </CardDescription>
            </CardHeader>
            <form onSubmit={handleSubmit}>
                <CardContent className="space-y-4">
                    {/* Error Message */}
                    {error && (
                        <div className="flex items-center gap-2 p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg">
                            <AlertCircle size={16} />
                            <span>{error}</span>
                        </div>
                    )}

                    <div className="space-y-2">
                        <Label htmlFor="email">Email</Label>
                        <Input
                            id="email"
                            type="email"
                            placeholder="ornek@email.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            disabled={isLoading}
                        />
                    </div>
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <Label htmlFor="password">Şifre</Label>
                            <Link
                                href="/forgot-password"
                                className="text-sm text-primary hover:underline"
                            >
                                Şifremi unuttum
                            </Link>
                        </div>
                        <div className="relative">
                            <Input
                                id="password"
                                type={showPassword ? "text" : "password"}
                                placeholder="••••••••"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                disabled={isLoading}
                            />
                            <button
                                type="button"
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                onClick={() => setShowPassword(!showPassword)}
                            >
                                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
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
                        Giriş Yap
                    </Button>
                    <p className="text-sm text-muted-foreground text-center">
                        Hesabınız yok mu?{" "}
                        <Link href="/register" className="text-primary hover:underline font-medium">
                            Kayıt Ol
                        </Link>
                    </p>
                </CardFooter>
            </form>
        </Card>
    );
}
