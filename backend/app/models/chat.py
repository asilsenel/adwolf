"""
Ad Platform MVP - Chat Models

Pydantic models for AI Chat Assistant (OpenAI Assistants API).
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ===========================================
# REQUEST MODELS
# ===========================================

class ChatMessageRequest(BaseModel):
    """User sends a message to the AI assistant."""
    message: str = Field(..., min_length=1, max_length=4000, description="User message")
    thread_id: Optional[str] = Field(None, description="Existing thread ID (None = new conversation)")


# ===========================================
# RESPONSE MODELS
# ===========================================

class ChatMessageResponse(BaseModel):
    """A single chat message."""
    id: str
    thread_id: str
    role: str  # user, assistant, system
    content: str
    tool_calls: Optional[list[dict]] = None
    tool_results: Optional[list[dict]] = None
    created_at: str


class ChatThreadResponse(BaseModel):
    """A chat thread/conversation."""
    id: str
    org_id: str
    openai_thread_id: Optional[str] = None
    title: str = "Yeni Konuşma"
    message_count: int = 0
    last_message_at: Optional[str] = None
    is_active: bool = True
    created_at: str


class ChatThreadList(BaseModel):
    """List of chat threads."""
    threads: list[ChatThreadResponse]
    total: int


class ChatHistoryResponse(BaseModel):
    """Thread with its message history."""
    thread: ChatThreadResponse
    messages: list[ChatMessageResponse]


# ===========================================
# SSE STREAM MODELS
# ===========================================

class StreamChunk(BaseModel):
    """Server-Sent Event chunk for streaming responses."""
    type: str  # text_delta, tool_call, tool_result, done, error, thread_created
    content: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[dict] = None
    thread_id: Optional[str] = None
    message_id: Optional[str] = None
