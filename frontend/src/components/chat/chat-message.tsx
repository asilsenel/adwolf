"use client";

import { Bot, User, Wrench } from "lucide-react";
import { cn } from "@/lib/utils";
import { ChatMessage as ChatMessageType } from "@/types/chat";

interface ChatMessageProps {
    message: ChatMessageType;
    isStreaming?: boolean;
}

export function ChatMessage({ message, isStreaming }: ChatMessageProps) {
    const isUser = message.role === "user";
    const isAssistant = message.role === "assistant";

    return (
        <div
            className={cn(
                "flex gap-3 px-4 py-3",
                isUser ? "flex-row-reverse" : "flex-row"
            )}
        >
            {/* Avatar */}
            <div
                className={cn(
                    "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center",
                    isUser
                        ? "bg-primary text-white"
                        : "bg-emerald-100 text-emerald-700"
                )}
            >
                {isUser ? <User size={16} /> : <Bot size={16} />}
            </div>

            {/* Message Content */}
            <div
                className={cn(
                    "max-w-[80%] rounded-2xl px-4 py-2.5",
                    isUser
                        ? "bg-primary text-white rounded-tr-sm"
                        : "bg-gray-100 text-foreground rounded-tl-sm"
                )}
            >
                {/* Tool calls indicator */}
                {message.tool_calls && message.tool_calls.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-2">
                        {message.tool_calls.map((tool, idx) => (
                            <span
                                key={idx}
                                className={cn(
                                    "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs",
                                    isUser
                                        ? "bg-white/20 text-white"
                                        : "bg-emerald-100 text-emerald-700"
                                )}
                            >
                                <Wrench size={10} />
                                {tool.name}
                            </span>
                        ))}
                    </div>
                )}

                {/* Text content with markdown-like formatting */}
                <div className={cn(
                    "text-sm whitespace-pre-wrap break-words leading-relaxed",
                    isAssistant && "prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-headings:my-2 prose-strong:font-semibold"
                )}>
                    {message.content}
                    {isStreaming && (
                        <span className="inline-block w-1.5 h-4 bg-current animate-pulse ml-0.5 align-text-bottom" />
                    )}
                </div>
            </div>
        </div>
    );
}

interface ToolCallIndicatorProps {
    toolName: string;
}

export function ToolCallIndicator({ toolName }: ToolCallIndicatorProps) {
    const toolLabels: Record<string, string> = {
        get_account_summary: "Hesap bilgileri alınıyor",
        get_campaign_list: "Kampanyalar listeleniyor",
        get_performance_metrics: "Metrikler getiriliyor",
        get_performance_comparison: "Karşılaştırma yapılıyor",
        get_recent_insights: "Insight'lar getiriliyor",
        execute_gaql_query: "GAQL sorgusu çalıştırılıyor",
    };

    return (
        <div className="flex items-center gap-2 px-4 py-2">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 border border-amber-200 rounded-full text-xs text-amber-700">
                <Wrench size={12} className="animate-spin" />
                <span>{toolLabels[toolName] || toolName}</span>
            </div>
        </div>
    );
}
