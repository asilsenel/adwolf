"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    LayoutDashboard,
    Users,
    Lightbulb,
    Settings,
    LogOut,
    Menu,
    X
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useState } from "react";

const navItems = [
    { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
    { href: "/accounts", icon: Users, label: "Hesaplar" },
    { href: "/insights", icon: Lightbulb, label: "Öneriler" },
    { href: "/settings", icon: Settings, label: "Ayarlar" },
];

export function Sidebar() {
    const pathname = usePathname();
    const [isMobileOpen, setIsMobileOpen] = useState(false);

    return (
        <>
            {/* Mobile toggle */}
            <Button
                variant="ghost"
                size="icon"
                className="fixed top-4 left-4 z-50 lg:hidden"
                onClick={() => setIsMobileOpen(!isMobileOpen)}
            >
                {isMobileOpen ? <X size={24} /> : <Menu size={24} />}
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
                    "fixed inset-y-0 left-0 z-40 w-64 bg-white border-r border-primary-light transform transition-transform duration-200 ease-in-out lg:translate-x-0 lg:static",
                    isMobileOpen ? "translate-x-0" : "-translate-x-full"
                )}
            >
                {/* Logo */}
                <div className="p-6 border-b border-primary-light">
                    <Link href="/dashboard" className="flex items-center gap-2">
                        <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center">
                            <span className="text-white font-bold text-xl">A</span>
                        </div>
                        <span className="font-bold text-xl text-foreground">AdWolf</span>
                    </Link>
                </div>

                {/* Navigation */}
                <nav className="p-4 space-y-2">
                    {navItems.map((item) => {
                        const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                onClick={() => setIsMobileOpen(false)}
                                className={cn(
                                    "flex items-center gap-3 px-4 py-3 rounded-lg transition-colors",
                                    isActive
                                        ? "bg-primary text-white"
                                        : "text-foreground hover:bg-cream"
                                )}
                            >
                                <item.icon size={20} />
                                <span>{item.label}</span>
                            </Link>
                        );
                    })}
                </nav>

                {/* User section */}
                <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-primary-light">
                    <div className="flex items-center gap-3 px-4 py-2">
                        <div className="w-10 h-10 rounded-full bg-primary-light flex items-center justify-center">
                            <span className="text-primary font-semibold">U</span>
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">Kullanıcı</p>
                            <p className="text-xs text-muted-foreground truncate">user@example.com</p>
                        </div>
                        <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-danger">
                            <LogOut size={18} />
                        </Button>
                    </div>
                </div>
            </aside>
        </>
    );
}
