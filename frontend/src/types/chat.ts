/**
 * TypeScript types for AI Chat Assistant
 */

export interface ChatThread {
    id: string;
    org_id: string;
    openai_thread_id?: string;
    title: string;
    message_count: number;
    last_message_at?: string;
    is_active: boolean;
    created_at: string;
}

export interface ChatMessage {
    id: string;
    thread_id: string;
    role: "user" | "assistant" | "system";
    content: string;
    tool_calls?: ToolCall[];
    tool_results?: ToolResult[];
    created_at: string;
}

export interface ToolCall {
    name: string;
    args: Record<string, unknown>;
    result_preview?: string;
}

export interface ToolResult {
    name: string;
    success: boolean;
}

export interface ChatThreadList {
    threads: ChatThread[];
    total: number;
}

export interface ChatHistoryResponse {
    thread: ChatThread;
    messages: ChatMessage[];
}

export interface StreamChunk {
    type: "text_delta" | "tool_call" | "tool_result" | "done" | "error" | "thread_created";
    content?: string;
    tool_name?: string;
    tool_args?: Record<string, unknown>;
    thread_id?: string;
    message_id?: string;
}
