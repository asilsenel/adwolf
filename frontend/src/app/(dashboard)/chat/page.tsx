"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
    Bot,
    MessageSquare,
    BarChart3,
    TrendingUp,
    Zap,
    PanelLeftClose,
    PanelLeftOpen,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useAuthStore } from "@/store/authStore";
import { api } from "@/services/api";
import { ChatMessage as ChatMessageType, ChatThread, StreamChunk } from "@/types/chat";
import { ChatMessage, ToolCallIndicator } from "@/components/chat/chat-message";
import { ChatInput } from "@/components/chat/chat-input";
import { ThreadList } from "@/components/chat/thread-list";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Example questions for empty state
const EXAMPLE_QUESTIONS = [
    {
        icon: BarChart3,
        label: "Performans Özeti",
        question: "Son 7 günün performans metriklerini özetle",
    },
    {
        icon: TrendingUp,
        label: "Karşılaştırma",
        question: "Bu haftanın performansını geçen haftayla karşılaştır",
    },
    {
        icon: Zap,
        label: "Anomaliler",
        question: "Kampanyalarımda dikkat edilmesi gereken anomaliler var mı?",
    },
    {
        icon: MessageSquare,
        label: "Hesaplarım",
        question: "Bağlı reklam hesaplarımı göster",
    },
];

export default function ChatPage() {
    const { hydrate } = useAuthStore();

    // State
    const [threads, setThreads] = useState<ChatThread[]>([]);
    const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
    const [messages, setMessages] = useState<ChatMessageType[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isStreaming, setIsStreaming] = useState(false);
    const [streamingContent, setStreamingContent] = useState("");
    const [activeToolCall, setActiveToolCall] = useState<string | null>(null);
    const [sidebarOpen, setSidebarOpen] = useState(true);

    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Hydrate auth state
    useEffect(() => {
        hydrate();
    }, [hydrate]);

    // Load threads on mount
    useEffect(() => {
        fetchThreads();
    }, []);

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, streamingContent]);

    const fetchThreads = async () => {
        try {
            const res = await api.get("/api/v1/chat/threads");
            setThreads(res.data.threads || []);
        } catch (err) {
            console.error("Failed to load threads:", err);
        }
    };

    const loadThreadHistory = async (threadId: string) => {
        try {
            const res = await api.get(`/api/v1/chat/threads/${threadId}`);
            setMessages(res.data.messages || []);
            setActiveThreadId(threadId);
        } catch (err) {
            console.error("Failed to load thread:", err);
        }
    };

    const handleSelectThread = (threadId: string) => {
        if (threadId === activeThreadId) return;
        setStreamingContent("");
        setActiveToolCall(null);
        loadThreadHistory(threadId);
    };

    const handleNewThread = () => {
        setActiveThreadId(null);
        setMessages([]);
        setStreamingContent("");
        setActiveToolCall(null);
    };

    const handleDeleteThread = async (threadId: string) => {
        try {
            await api.delete(`/api/v1/chat/threads/${threadId}`);
            setThreads((prev) => prev.filter((t) => t.id !== threadId));
            if (activeThreadId === threadId) {
                handleNewThread();
            }
        } catch (err) {
            console.error("Failed to delete thread:", err);
        }
    };

    const handleSendMessage = useCallback(async (messageText: string) => {
        if (isStreaming) return;

        // Add user message optimistically
        const userMessage: ChatMessageType = {
            id: `temp-${Date.now()}`,
            thread_id: activeThreadId || "",
            role: "user",
            content: messageText,
            created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, userMessage]);
        setIsStreaming(true);
        setStreamingContent("");
        setActiveToolCall(null);

        try {
            const token = localStorage.getItem("access_token");

            const response = await fetch(`${API_BASE_URL}/api/v1/chat/message`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    message: messageText,
                    thread_id: activeThreadId,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const reader = response.body?.getReader();
            if (!reader) throw new Error("No response body");

            const decoder = new TextDecoder();
            let buffer = "";
            let fullContent = "";
            let newThreadId = activeThreadId;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                // Parse SSE events from buffer
                const lines = buffer.split("\n");
                buffer = lines.pop() || ""; // Keep incomplete line in buffer

                for (const line of lines) {
                    if (!line.startsWith("data: ")) continue;

                    try {
                        const chunk: StreamChunk = JSON.parse(line.slice(6));

                        switch (chunk.type) {
                            case "text_delta":
                                if (chunk.content) {
                                    fullContent += chunk.content;
                                    setStreamingContent(fullContent);
                                }
                                break;

                            case "tool_call":
                                setActiveToolCall(chunk.tool_name || null);
                                break;

                            case "tool_result":
                                setActiveToolCall(null);
                                break;

                            case "thread_created":
                                if (chunk.thread_id) {
                                    newThreadId = chunk.thread_id;
                                    setActiveThreadId(chunk.thread_id);
                                }
                                break;

                            case "done":
                                // Add the complete assistant message
                                if (fullContent) {
                                    const assistantMessage: ChatMessageType = {
                                        id: chunk.message_id || `msg-${Date.now()}`,
                                        thread_id: newThreadId || "",
                                        role: "assistant",
                                        content: fullContent,
                                        created_at: new Date().toISOString(),
                                    };
                                    setMessages((prev) => [...prev, assistantMessage]);
                                }
                                setStreamingContent("");
                                setActiveToolCall(null);
                                break;

                            case "error":
                                console.error("Stream error:", chunk.content);
                                // Show error as assistant message
                                const errorMessage: ChatMessageType = {
                                    id: `error-${Date.now()}`,
                                    thread_id: newThreadId || "",
                                    role: "assistant",
                                    content: `⚠️ ${chunk.content || "Bir hata oluştu"}`,
                                    created_at: new Date().toISOString(),
                                };
                                setMessages((prev) => [...prev, errorMessage]);
                                setStreamingContent("");
                                break;
                        }
                    } catch {
                        // Skip unparseable lines
                    }
                }
            }

            // Refresh thread list
            await fetchThreads();
        } catch (err: any) {
            console.error("Send message error:", err);
            const errorMessage: ChatMessageType = {
                id: `error-${Date.now()}`,
                thread_id: activeThreadId || "",
                role: "assistant",
                content: `⚠️ Mesaj gönderilemedi: ${err.message || "Bilinmeyen hata"}`,
                created_at: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, errorMessage]);
            setStreamingContent("");
        } finally {
            setIsStreaming(false);
            setActiveToolCall(null);
        }
    }, [activeThreadId, isStreaming]);

    return (
        <div className="flex h-[calc(100vh-2rem)] overflow-hidden rounded-lg border bg-white">
            {/* Thread Sidebar */}
            <ThreadList
                threads={threads}
                activeThreadId={activeThreadId}
                onSelectThread={handleSelectThread}
                onNewThread={handleNewThread}
                onDeleteThread={handleDeleteThread}
                isCollapsed={!sidebarOpen}
            />

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col min-w-0">
                {/* Chat Header */}
                <div className="flex items-center gap-3 px-4 py-3 border-b bg-white">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => setSidebarOpen(!sidebarOpen)}
                    >
                        {sidebarOpen ? (
                            <PanelLeftClose size={18} />
                        ) : (
                            <PanelLeftOpen size={18} />
                        )}
                    </Button>

                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center">
                            <Bot size={16} className="text-emerald-700" />
                        </div>
                        <div>
                            <h2 className="text-sm font-semibold">AI Asistan</h2>
                            <p className="text-xs text-muted-foreground">
                                Performans pazarlama uzmanı
                            </p>
                        </div>
                    </div>
                </div>

                {/* Messages Area */}
                <div className="flex-1 overflow-y-auto">
                    {messages.length === 0 && !streamingContent ? (
                        /* Empty State */
                        <div className="flex flex-col items-center justify-center h-full p-8">
                            <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center mb-4">
                                <Bot size={32} className="text-emerald-700" />
                            </div>
                            <h3 className="text-lg font-semibold mb-2">
                                AdWolf AI Asistan
                            </h3>
                            <p className="text-sm text-muted-foreground mb-6 text-center max-w-md">
                                Reklam kampanyalarınız hakkında sorular sorun, performans analizi
                                yapın, optimizasyon önerileri alın.
                            </p>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full">
                                {EXAMPLE_QUESTIONS.map((q, idx) => (
                                    <Card
                                        key={idx}
                                        className="p-3 cursor-pointer hover:bg-gray-50 transition-colors border-gray-200"
                                        onClick={() => handleSendMessage(q.question)}
                                    >
                                        <div className="flex items-start gap-2">
                                            <q.icon
                                                size={16}
                                                className="text-primary mt-0.5 flex-shrink-0"
                                            />
                                            <div>
                                                <p className="text-xs font-medium text-primary">
                                                    {q.label}
                                                </p>
                                                <p className="text-xs text-muted-foreground mt-0.5">
                                                    {q.question}
                                                </p>
                                            </div>
                                        </div>
                                    </Card>
                                ))}
                            </div>
                        </div>
                    ) : (
                        /* Messages */
                        <div className="py-4">
                            {messages.map((msg) => (
                                <ChatMessage key={msg.id} message={msg} />
                            ))}

                            {/* Active tool call indicator */}
                            {activeToolCall && (
                                <ToolCallIndicator toolName={activeToolCall} />
                            )}

                            {/* Streaming message */}
                            {streamingContent && (
                                <ChatMessage
                                    message={{
                                        id: "streaming",
                                        thread_id: activeThreadId || "",
                                        role: "assistant",
                                        content: streamingContent,
                                        created_at: new Date().toISOString(),
                                    }}
                                    isStreaming
                                />
                            )}

                            <div ref={messagesEndRef} />
                        </div>
                    )}
                </div>

                {/* Input Area */}
                <ChatInput
                    onSend={handleSendMessage}
                    isLoading={isStreaming}
                />
            </div>
        </div>
    );
}
