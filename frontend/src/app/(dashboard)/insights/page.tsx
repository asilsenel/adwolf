"use client";

import { useEffect, useState, useCallback } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PlatformIcon } from "@/components/accounts/platform-icon";
import { api } from "@/services/api";
import { useAuthStore } from "@/store/authStore";
import { Insight, InsightList, InsightSeverity } from "@/types/insight";
import {
    Sparkles,
    AlertTriangle,
    TrendingUp,
    Clock,
    ChevronRight,
    X,
    Loader2,
    RefreshCw,
    CheckCircle,
    Eye,
    Lightbulb,
    Zap,
    BarChart3,
    Search as SearchIcon,
} from "lucide-react";

const severityConfig: Record<InsightSeverity, {
    color: string;
    icon: typeof AlertTriangle;
    iconColor: string;
    label: string;
    badge: "destructive" | "warning" | "default" | "secondary";
}> = {
    critical: { color: "border-l-red-500 bg-red-50", icon: AlertTriangle, iconColor: "text-red-500", label: "Kritik", badge: "destructive" },
    high: { color: "border-l-amber-500 bg-amber-50", icon: AlertTriangle, iconColor: "text-amber-500", label: "Yuksek", badge: "warning" },
    medium: { color: "border-l-blue-500 bg-blue-50", icon: TrendingUp, iconColor: "text-blue-500", label: "Orta", badge: "default" },
    low: { color: "border-l-gray-400 bg-gray-50", icon: Clock, iconColor: "text-gray-400", label: "Dusuk", badge: "secondary" },
};

const insightTypeConfig: Record<string, { icon: typeof Lightbulb; label: string }> = {
    performance: { icon: BarChart3, label: "Performans" },
    optimization: { icon: Zap, label: "Optimizasyon" },
    alert: { icon: AlertTriangle, label: "Uyari" },
    opportunity: { icon: Lightbulb, label: "Firsat" },
    anomaly: { icon: SearchIcon, label: "Anomali" },
};

type FilterType = "all" | "unread" | "high_priority" | "has_actions";

export default function InsightsPage() {
    const { hydrate, isAuthenticated } = useAuthStore();
    const [insights, setInsights] = useState<Insight[]>([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [isLoading, setIsLoading] = useState(true);
    const [isGenerating, setIsGenerating] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [filter, setFilter] = useState<FilterType>("all");
    const [expandedId, setExpandedId] = useState<string | null>(null);

    useEffect(() => {
        hydrate();
    }, [hydrate]);

    const fetchInsights = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);
            const response = await api.get<InsightList>("/api/v1/insights");
            const data = response.data;
            setInsights(data.insights || []);
            setUnreadCount(data.unread_count || 0);
        } catch (err: unknown) {
            console.error("Failed to fetch insights:", err);
            setError("Insight'lar yuklenirken bir hata olustu.");
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        if (isAuthenticated) {
            fetchInsights();
        } else {
            setIsLoading(false);
        }
    }, [isAuthenticated, fetchInsights]);

    const handleGenerate = async () => {
        try {
            setIsGenerating(true);
            setError(null);
            const response = await api.post<InsightList>("/api/v1/insights/generate");
            const data = response.data;
            setInsights(data.insights || []);
            setUnreadCount(data.unread_count || 0);
        } catch (err: unknown) {
            const axiosErr = err as { response?: { status?: number; data?: { detail?: string } } };
            if (axiosErr.response?.status === 429) {
                setError(axiosErr.response?.data?.detail || "Cok sik istek gonderdiniz. Lutfen bekleyin.");
            } else if (axiosErr.response?.status === 500) {
                setError(axiosErr.response?.data?.detail || "Insight olusturma basarisiz. OpenAI API anahtarini kontrol edin.");
            } else {
                setError("Insight olusturma sirasinda bir hata olustu.");
            }
        } finally {
            setIsGenerating(false);
        }
    };

    const handleMarkRead = async (insightId: string) => {
        try {
            await api.post(`/api/v1/insights/${insightId}/read`);
            setInsights(prev => prev.map(i =>
                i.id === insightId ? { ...i, is_read: true } : i
            ));
            setUnreadCount(prev => Math.max(0, prev - 1));
        } catch (err) {
            console.error("Failed to mark insight as read:", err);
        }
    };

    const handleDismiss = async (insightId: string) => {
        try {
            await api.post(`/api/v1/insights/${insightId}/dismiss`, {});
            setInsights(prev => prev.filter(i => i.id !== insightId));
        } catch (err) {
            console.error("Failed to dismiss insight:", err);
        }
    };

    // Format relative time
    const formatRelativeTime = (dateStr: string) => {
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMins < 1) return "Az once";
        if (diffMins < 60) return `${diffMins} dk once`;
        if (diffHours < 24) return `${diffHours} saat once`;
        if (diffDays < 7) return `${diffDays} gun once`;
        return date.toLocaleDateString("tr-TR");
    };

    // Apply filters
    const filteredInsights = insights.filter(insight => {
        switch (filter) {
            case "unread":
                return !insight.is_read;
            case "high_priority":
                return insight.severity === "critical" || insight.severity === "high";
            case "has_actions":
                return insight.recommended_actions && insight.recommended_actions.length > 0;
            default:
                return true;
        }
    });

    return (
        <div className="flex-1">
            <Header
                title="Oneriler"
                subtitle="AI destekli analiz ve optimizasyon onerileri"
            />

            <div className="p-6 space-y-6">
                {/* Top Bar: Generate + Stats */}
                <div className="flex items-center justify-between flex-wrap gap-4">
                    <div className="flex items-center gap-4">
                        <Button
                            onClick={handleGenerate}
                            disabled={isGenerating}
                            className="gap-2"
                        >
                            {isGenerating ? (
                                <Loader2 size={16} className="animate-spin" />
                            ) : (
                                <Sparkles size={16} />
                            )}
                            {isGenerating ? "Olusturuluyor..." : "Insight Olustur"}
                        </Button>

                        <Button
                            variant="outline"
                            size="sm"
                            onClick={fetchInsights}
                            disabled={isLoading}
                        >
                            <RefreshCw size={14} className={isLoading ? "animate-spin" : ""} />
                        </Button>
                    </div>

                    {unreadCount > 0 && (
                        <Badge variant="default" className="gap-1">
                            <Eye size={12} />
                            {unreadCount} okunmamis
                        </Badge>
                    )}
                </div>

                {/* Error Banner */}
                {error && (
                    <Card className="border-red-200 bg-red-50">
                        <CardContent className="py-3">
                            <div className="flex items-center justify-between">
                                <p className="text-sm text-red-700">{error}</p>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setError(null)}
                                >
                                    <X size={14} />
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Filter Tabs */}
                <div className="flex gap-2 overflow-x-auto pb-2">
                    {[
                        { key: "all" as FilterType, label: "Tumu" },
                        { key: "unread" as FilterType, label: "Okunmamis" },
                        { key: "high_priority" as FilterType, label: "Yuksek Oncelik" },
                        { key: "has_actions" as FilterType, label: "Aksiyon Bekleyen" },
                    ].map((f) => (
                        <Button
                            key={f.key}
                            variant={filter === f.key ? "default" : "outline"}
                            size="sm"
                            onClick={() => setFilter(f.key)}
                        >
                            {f.label}
                            {f.key === "unread" && unreadCount > 0 && (
                                <span className="ml-1 text-xs">({unreadCount})</span>
                            )}
                        </Button>
                    ))}
                </div>

                {/* Loading State */}
                {isLoading && (
                    <div className="flex items-center justify-center py-20">
                        <Loader2 size={32} className="animate-spin text-primary" />
                    </div>
                )}

                {/* Empty State */}
                {!isLoading && filteredInsights.length === 0 && (
                    <Card className="border-dashed">
                        <CardContent className="py-16 text-center">
                            <Sparkles size={48} className="mx-auto mb-4 text-muted-foreground/50" />
                            <h3 className="text-lg font-semibold mb-2">
                                {insights.length === 0 ? "Henuz insight yok" : "Filtreye uygun insight yok"}
                            </h3>
                            <p className="text-muted-foreground mb-6 max-w-md mx-auto">
                                {insights.length === 0
                                    ? "AI destekli insight'lar olusturmak icin asagidaki butona tiklayin. Reklam verileriniz analiz edilecek."
                                    : "Farkli bir filtre secmeyi deneyin."}
                            </p>
                            {insights.length === 0 && (
                                <Button onClick={handleGenerate} disabled={isGenerating} className="gap-2">
                                    {isGenerating ? (
                                        <Loader2 size={16} className="animate-spin" />
                                    ) : (
                                        <Sparkles size={16} />
                                    )}
                                    Insight Olustur
                                </Button>
                            )}
                        </CardContent>
                    </Card>
                )}

                {/* Insights List */}
                {!isLoading && filteredInsights.length > 0 && (
                    <div className="space-y-4">
                        {filteredInsights.map((insight) => {
                            const sConfig = severityConfig[insight.severity] || severityConfig.medium;
                            const tConfig = insightTypeConfig[insight.insight_type] || insightTypeConfig.performance;
                            const IconComponent = sConfig.icon;
                            const TypeIcon = tConfig.icon;
                            const isExpanded = expandedId === insight.id;

                            return (
                                <Card
                                    key={insight.id}
                                    className={`bg-white border-l-4 ${sConfig.color} hover:shadow-md transition-shadow cursor-pointer`}
                                    onClick={() => {
                                        setExpandedId(isExpanded ? null : insight.id);
                                        if (!insight.is_read) {
                                            handleMarkRead(insight.id);
                                        }
                                    }}
                                >
                                    <CardContent className="py-4">
                                        <div className="flex items-start gap-4">
                                            {/* Icon */}
                                            <div className={`mt-1 ${sConfig.iconColor}`}>
                                                <IconComponent size={20} />
                                            </div>

                                            {/* Content */}
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 mb-1 flex-wrap">
                                                    {insight.platform && (
                                                        <PlatformIcon platform={insight.platform} size={18} />
                                                    )}
                                                    <h4 className="font-semibold">{insight.title}</h4>
                                                    <Badge variant={sConfig.badge}>
                                                        {sConfig.label}
                                                    </Badge>
                                                    <Badge variant="outline" className="gap-1 text-xs">
                                                        <TypeIcon size={10} />
                                                        {tConfig.label}
                                                    </Badge>
                                                    {!insight.is_read && (
                                                        <span className="w-2 h-2 rounded-full bg-primary flex-shrink-0" />
                                                    )}
                                                </div>
                                                <p className="text-sm text-muted-foreground mb-2">
                                                    {insight.summary}
                                                </p>

                                                {/* Expanded: Detailed Analysis */}
                                                {isExpanded && insight.detailed_analysis && (
                                                    <div className="mt-3 p-3 bg-white/80 rounded-lg border text-sm text-foreground">
                                                        <p className="whitespace-pre-wrap">{insight.detailed_analysis}</p>
                                                    </div>
                                                )}

                                                {/* Actions */}
                                                {insight.recommended_actions && insight.recommended_actions.length > 0 && (
                                                    <div className="flex gap-2 flex-wrap mt-3">
                                                        {insight.recommended_actions.map((action) => (
                                                            <Button
                                                                key={action.id}
                                                                size="sm"
                                                                variant="outline"
                                                                className="gap-1"
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    // Show action detail in expanded view
                                                                    setExpandedId(insight.id);
                                                                }}
                                                            >
                                                                <CheckCircle size={12} />
                                                                {action.title}
                                                            </Button>
                                                        ))}
                                                        <Button
                                                            size="sm"
                                                            variant="ghost"
                                                            className="text-muted-foreground gap-1"
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                handleDismiss(insight.id);
                                                            }}
                                                        >
                                                            <X size={14} />
                                                            Kapat
                                                        </Button>
                                                    </div>
                                                )}

                                                {/* Expanded: Action Details */}
                                                {isExpanded && insight.recommended_actions && insight.recommended_actions.length > 0 && (
                                                    <div className="mt-3 space-y-2">
                                                        {insight.recommended_actions.map((action) => (
                                                            <div key={action.id} className="p-3 bg-white/80 rounded-lg border text-sm">
                                                                <div className="flex items-center gap-2 mb-1">
                                                                    <Zap size={14} className="text-amber-500" />
                                                                    <span className="font-medium">{action.title}</span>
                                                                    {action.platform && (
                                                                        <PlatformIcon platform={action.platform} size={14} />
                                                                    )}
                                                                </div>
                                                                <p className="text-muted-foreground">{action.description}</p>
                                                                {action.rationale && (
                                                                    <p className="text-xs text-muted-foreground mt-1">
                                                                        <span className="font-medium">Neden:</span> {action.rationale}
                                                                    </p>
                                                                )}
                                                                {action.expected_impact && (
                                                                    <p className="text-xs text-green-600 mt-1">
                                                                        <span className="font-medium">Beklenen Etki:</span> {action.expected_impact}
                                                                    </p>
                                                                )}
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>

                                            {/* Time + Expand */}
                                            <div className="flex flex-col items-end gap-2">
                                                <span className="text-xs text-muted-foreground whitespace-nowrap">
                                                    {formatRelativeTime(insight.created_at)}
                                                </span>
                                                <ChevronRight
                                                    size={16}
                                                    className={`text-muted-foreground transition-transform ${isExpanded ? "rotate-90" : ""}`}
                                                />
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            );
                        })}
                    </div>
                )}

                {/* AI Info */}
                {!isLoading && insights.length > 0 && (
                    <div className="text-center text-xs text-muted-foreground pt-4">
                        <Sparkles size={12} className="inline mr-1" />
                        Insight&apos;lar GPT-4o ile olusturulmustur. Son 7 gunluk reklam verileri analiz edilmistir.
                    </div>
                )}
            </div>
        </div>
    );
}
