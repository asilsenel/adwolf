"use client";

import { Bot, User, Wrench } from "lucide-react";
import { cn } from "@/lib/utils";
import { ChatMessage as ChatMessageType } from "@/types/chat";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

interface ChatMessageProps {
    message: ChatMessageType;
    isStreaming?: boolean;
}

/**
 * Custom markdown components for styled rendering.
 * Tables get a scrollable wrapper with clean borders and striped rows.
 */
const markdownComponents: Components = {
    table: ({ children, ...props }) => (
        <div className="my-2 overflow-x-auto rounded-lg border border-gray-200 ">
            <table
                className="w-full text-xs border-collapse"
                {...props}
            >
                {children}
            </table>
        </div>
    ),
    thead: ({ children, ...props }) => (
        <thead className="bg-gray-50  border-b border-gray-200 " {...props}>
            {children}
        </thead>
    ),
    tbody: ({ children, ...props }) => (
        <tbody className="divide-y divide-gray-100 " {...props}>
            {children}
        </tbody>
    ),
    tr: ({ children, ...props }) => (
        <tr className="hover:bg-gray-50/50  transition-colors" {...props}>
            {children}
        </tr>
    ),
    th: ({ children, ...props }) => (
        <th
            className="px-3 py-2 text-left text-xs font-semibold text-gray-600  whitespace-nowrap"
            {...props}
        >
            {children}
        </th>
    ),
    td: ({ children, ...props }) => (
        <td
            className="px-3 py-1.5 text-xs text-gray-700  whitespace-nowrap"
            {...props}
        >
            {children}
        </td>
    ),
    // Headings
    h1: ({ children, ...props }) => (
        <h1 className="text-base font-bold mt-3 mb-1" {...props}>{children}</h1>
    ),
    h2: ({ children, ...props }) => (
        <h2 className="text-sm font-bold mt-2.5 mb-1" {...props}>{children}</h2>
    ),
    h3: ({ children, ...props }) => (
        <h3 className="text-sm font-semibold mt-2 mb-1" {...props}>{children}</h3>
    ),
    // Paragraph
    p: ({ children, ...props }) => (
        <p className="my-1 leading-relaxed" {...props}>{children}</p>
    ),
    // Lists
    ul: ({ children, ...props }) => (
        <ul className="my-1 ml-4 list-disc space-y-0.5" {...props}>{children}</ul>
    ),
    ol: ({ children, ...props }) => (
        <ol className="my-1 ml-4 list-decimal space-y-0.5" {...props}>{children}</ol>
    ),
    li: ({ children, ...props }) => (
        <li className="leading-relaxed" {...props}>{children}</li>
    ),
    // Inline code
    code: ({ children, className, ...props }) => {
        const isBlock = className?.includes("language-");
        if (isBlock) {
            return (
                <code
                    className="block my-2 p-2.5 bg-gray-800 text-gray-100 rounded-lg text-xs overflow-x-auto font-mono"
                    {...props}
                >
                    {children}
                </code>
            );
        }
        return (
            <code
                className="px-1 py-0.5 bg-gray-200  text-gray-800  rounded text-xs font-mono"
                {...props}
            >
                {children}
            </code>
        );
    },
    // Code block wrapper
    pre: ({ children, ...props }) => (
        <pre className="my-2" {...props}>{children}</pre>
    ),
    // Bold
    strong: ({ children, ...props }) => (
        <strong className="font-semibold" {...props}>{children}</strong>
    ),
    // Blockquote
    blockquote: ({ children, ...props }) => (
        <blockquote
            className="my-2 pl-3 border-l-2 border-gray-300  text-gray-600  italic"
            {...props}
        >
            {children}
        </blockquote>
    ),
    // Horizontal rule
    hr: ({ ...props }) => (
        <hr className="my-2 border-gray-200 " {...props} />
    ),
    // Links
    a: ({ children, ...props }) => (
        <a className="text-primary-dark underline hover:text-primary" {...props}>
            {children}
        </a>
    ),
};

export function ChatMessage({ message, isStreaming }: ChatMessageProps) {
    const isUser = message.role === "user";

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
                        ? "bg-primary-light/40 text-foreground rounded-tr-sm"
                        : "bg-gray-100  text-foreground rounded-tl-sm"
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
                                        ? "bg-primary/20 text-primary-dark"
                                        : "bg-emerald-100 text-emerald-700"
                                )}
                            >
                                <Wrench size={10} />
                                {tool.name}
                            </span>
                        ))}
                    </div>
                )}

                {/* Text content with markdown rendering */}
                <div className="text-sm break-words leading-relaxed">
                    {isUser ? (
                        // User messages: plain text, no markdown
                        <span className="whitespace-pre-wrap">{message.content}</span>
                    ) : (
                        // Assistant messages: full markdown with tables
                        <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={markdownComponents}
                        >
                            {message.content}
                        </ReactMarkdown>
                    )}
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
        execute_gaql_query: "Google Ads sorgusu çalıştırılıyor",
    };

    return (
        <div className="flex items-center gap-2 px-4 py-2">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50  border border-amber-200  rounded-full text-xs text-amber-700 ">
                <Wrench size={12} className="animate-spin" />
                <span>{toolLabels[toolName] || toolName}</span>
            </div>
        </div>
    );
}
