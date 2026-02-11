"use client";

import { Plus, MessageSquare, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ChatThread } from "@/types/chat";

interface ThreadListProps {
    threads: ChatThread[];
    activeThreadId?: string | null;
    onSelectThread: (threadId: string) => void;
    onNewThread: () => void;
    onDeleteThread: (threadId: string) => void;
    isCollapsed?: boolean;
}

export function ThreadList({
    threads,
    activeThreadId,
    onSelectThread,
    onNewThread,
    onDeleteThread,
    isCollapsed,
}: ThreadListProps) {
    const formatDate = (dateStr?: string) => {
        if (!dateStr) return "";
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return "Az önce";
        if (diffMins < 60) return `${diffMins}dk`;
        if (diffHours < 24) return `${diffHours}sa`;
        if (diffDays < 7) return `${diffDays}g`;
        return date.toLocaleDateString("tr-TR", { day: "numeric", month: "short" });
    };

    return (
        <div className={cn(
            "flex flex-col h-full bg-gray-50  border-r ",
            isCollapsed ? "w-0 overflow-hidden" : "w-72"
        )}>
            {/* Header */}
            <div className="p-3 border-b bg-white  ">
                <Button
                    onClick={onNewThread}
                    className="w-full gap-2"
                    variant="outline"
                    size="sm"
                >
                    <Plus size={16} />
                    Yeni Konuşma
                </Button>
            </div>

            {/* Thread List */}
            <div className="flex-1 overflow-y-auto">
                {threads.length === 0 ? (
                    <div className="p-4 text-center text-sm text-muted-foreground">
                        <MessageSquare size={32} className="mx-auto mb-2 opacity-30" />
                        <p>Henüz konuşma yok</p>
                        <p className="text-xs mt-1">Yeni bir konuşma başlatın</p>
                    </div>
                ) : (
                    <div className="p-2 space-y-1">
                        {threads.map((thread) => (
                            <div
                                key={thread.id}
                                className={cn(
                                    "group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-colors",
                                    activeThreadId === thread.id
                                        ? "bg-primary/10 text-primary"
                                        : "hover:bg-gray-100  text-foreground"
                                )}
                                onClick={() => onSelectThread(thread.id)}
                            >
                                <MessageSquare size={14} className="flex-shrink-0 opacity-50" />
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium truncate">
                                        {thread.title}
                                    </p>
                                    <p className="text-xs text-muted-foreground">
                                        {thread.message_count} mesaj · {formatDate(thread.last_message_at || thread.created_at)}
                                    </p>
                                </div>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onDeleteThread(thread.id);
                                    }}
                                >
                                    <Trash2 size={12} />
                                </Button>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
