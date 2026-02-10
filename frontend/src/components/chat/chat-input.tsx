"use client";

import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface ChatInputProps {
    onSend: (message: string) => void;
    isLoading: boolean;
    disabled?: boolean;
    placeholder?: string;
}

export function ChatInput({
    onSend,
    isLoading,
    disabled,
    placeholder = "Bir soru sorun... (Shift+Enter yeni satır)",
}: ChatInputProps) {
    const [message, setMessage] = useState("");
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Auto-resize textarea
    useEffect(() => {
        const textarea = textareaRef.current;
        if (textarea) {
            textarea.style.height = "auto";
            const newHeight = Math.min(textarea.scrollHeight, 200);
            textarea.style.height = `${newHeight}px`;
        }
    }, [message]);

    const handleSend = () => {
        const trimmed = message.trim();
        if (!trimmed || isLoading || disabled) return;

        onSend(trimmed);
        setMessage("");

        // Reset textarea height
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
        }
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="border-t bg-white p-4">
            <div className="flex items-end gap-2 max-w-4xl mx-auto">
                <Textarea
                    ref={textareaRef}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={placeholder}
                    disabled={isLoading || disabled}
                    className="min-h-[44px] max-h-[200px] py-3 pr-4 resize-none rounded-xl border-gray-200 focus:border-primary"
                    rows={1}
                />
                <Button
                    onClick={handleSend}
                    disabled={!message.trim() || isLoading || disabled}
                    size="icon"
                    className="h-11 w-11 rounded-xl flex-shrink-0"
                >
                    {isLoading ? (
                        <Loader2 size={18} className="animate-spin" />
                    ) : (
                        <Send size={18} />
                    )}
                </Button>
            </div>
        </div>
    );
}
