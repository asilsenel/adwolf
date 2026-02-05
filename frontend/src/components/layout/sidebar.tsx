"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
    LayoutDashboard,
    Users,
    Lightbulb,
    Settings,
    LogOut,
    Menu,
    ChevronLeft,
    ChevronRight,
    Target
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useState, useEffect } from "react";
import { useAuthStore } from "@/store/authStore";

const navItems = [
    { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
    { href: "/accounts", icon: Users, label: "Hesaplar" },
    { href: "/campaigns", icon: Target, label: "Kampanyalar" },
    { href: "/insights", icon: Lightbulb, label: "Öneriler" },
    { href: "/settings", icon: Settings, label: "Ayarlar" },
];

export function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const { user, hydrate } = useAuthStore();
    const [isMobileOpen, setIsMobileOpen] = useState(false);
    const [isCollapsed, setIsCollapsed] = useState(false);

    // Hydrate auth state to get user info
    useEffect(() => {
        hydrate();
    }, [hydrate]);

    const handleLogout = () => {
        // Clear all auth data
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
        localStorage.removeItem("token");
        // Redirect to login
        router.push("/login");
    };

    // Get user initials for avatar
    const getUserInitial = () => {
        if (user?.email) {
            return user.email.charAt(0).toUpperCase();
        }
        return "U";
    };

    // Get display name (email username)
    const getDisplayName = () => {
        if (user?.email) {
            return user.email.split("@")[0];
        }
        return "Kullanıcı";
    };

    return (
        <>
            {/* Mobile toggle */}
            <Button
                variant="ghost"
                size="icon"
                className="fixed top-4 left-4 z-50 lg:hidden"
                onClick={() => setIsMobileOpen(!isMobileOpen)}
            >
                <Menu size={24} />
            </Button>

            {/* Mobile overlay */}
            {isMobileOpen && (
                <div
                    className="fixed inset-0 bg-black/50 z-40 lg:hidden"
                    onClick={() => setIsMobileOpen(false)}
                />
            )}

            {/* Sidebar */}
            <aside
                className={cn(
                    "fixed inset-y-0 left-0 z-40 bg-white border-r border-primary-light transform transition-all duration-200 ease-in-out lg:translate-x-0 lg:static flex flex-col",
                    isMobileOpen ? "translate-x-0" : "-translate-x-full",
                    isCollapsed ? "w-20" : "w-64"
                )}
            >
                {/* Logo & Collapse Toggle */}
                <div className="p-4 border-b border-primary-light flex items-center justify-between">
                    <Link href="/dashboard" className={cn("flex items-center gap-2", isCollapsed && "justify-center")}>
                        <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center flex-shrink-0">
                            <span className="text-white font-bold text-xl">A</span>
                        </div>
                        {!isCollapsed && (
                            <span className="font-bold text-xl text-foreground">AdWolf</span>
                        )}
                    </Link>

                    {/* Collapse button - only on desktop */}
                    <Button
                        variant="ghost"
                        size="icon"
                        className={cn("hidden lg:flex h-8 w-8", isCollapsed && "absolute -right-3 top-6 bg-white border border-primary-light rounded-full shadow-sm")}
                        onClick={() => setIsCollapsed(!isCollapsed)}
                    >
                        {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
                    </Button>
                </div>

                {/* Navigation */}
                <nav className="flex-1 p-4 space-y-2">
                    {navItems.map((item) => {
                        const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                onClick={() => setIsMobileOpen(false)}
                                title={isCollapsed ? item.label : undefined}
                                className={cn(
                                    "flex items-center gap-3 px-4 py-3 rounded-lg transition-colors font-medium",
                                    isCollapsed && "justify-center px-2",
                                    isActive
                                        ? "bg-primary text-white"
                                        : "text-foreground hover:bg-cream"
                                )}
                            >
                                <item.icon size={20} className="flex-shrink-0" />
                                {!isCollapsed && <span>{item.label}</span>}
                            </Link>
                        );
                    })}
                </nav>

                {/* User section */}
                <div className="p-4 border-t border-primary-light">
                    <div className={cn(
                        "flex items-center gap-3 px-2 py-2",
                        isCollapsed && "flex-col gap-2"
                    )}>
                        <div className="w-10 h-10 rounded-full bg-primary-light flex items-center justify-center flex-shrink-0">
                            <span className="text-primary font-semibold">{getUserInitial()}</span>
                        </div>
                        {!isCollapsed && (
                            <>
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium truncate">{getDisplayName()}</p>
                                    <p className="text-xs text-muted-foreground truncate">{user?.email || "user@example.com"}</p>
                                </div>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="text-muted-foreground hover:text-danger flex-shrink-0"
                                    onClick={handleLogout}
                                    title="Çıkış Yap"
                                >
                                    <LogOut size={18} />
                                </Button>
                            </>
                        )}
                        {isCollapsed && (
                            <Button
                                variant="ghost"
                                size="icon"
                                className="text-muted-foreground hover:text-danger"
                                onClick={handleLogout}
                                title="Çıkış Yap"
                            >
                                <LogOut size={18} />
                            </Button>
                        )}
                    </div>
                </div>
            </aside>
        </>
    );
}
