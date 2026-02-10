"""
Ad Platform MVP - Chat API Endpoints

REST + SSE streaming endpoints for AI Chat Assistant.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, CurrentOrgId, CurrentUserId
from app.models.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatThreadResponse,
    ChatThreadList,
    ChatHistoryResponse,
)
from app.services.chat_service import ChatService
from app.core.supabase import get_supabase_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/message")
async def send_message(
    request: ChatMessageRequest,
    current_user: CurrentUser,
    org_id: CurrentOrgId,
    user_id: CurrentUserId,
):
    """
    Send a message to the AI assistant and receive a streaming response.

    Returns: Server-Sent Events (SSE) stream with:
    - text_delta: Incremental text chunks
    - tool_call: Tool execution started
    - tool_result: Tool execution completed
    - thread_created: New thread was created (includes thread_id)
    - done: Stream completed
    - error: An error occurred
    """
    from app.core.config import settings

    if not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI API key not configured",
        )

    chat_service = ChatService()

    async def event_generator():
        try:
            async for event in chat_service.send_message_stream(
                message=request.message,
                org_id=org_id,
                user_id=user_id,
                thread_id=request.thread_id,
            ):
                yield event
        except Exception as e:
            logger.error(f"SSE stream error: {e}", exc_info=True)
            import json
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/threads", response_model=ChatThreadList)
async def list_threads(
    current_user: CurrentUser,
    org_id: CurrentOrgId,
    user_id: CurrentUserId,
):
    """Get all chat threads for the current user."""
    supabase = get_supabase_service()
    threads = await supabase.get_chat_threads(org_id=org_id, user_id=user_id)

    return ChatThreadList(
        threads=[ChatThreadResponse(**t) for t in threads],
        total=len(threads),
    )


@router.get("/threads/{thread_id}", response_model=ChatHistoryResponse)
async def get_thread_history(
    thread_id: str,
    current_user: CurrentUser,
    org_id: CurrentOrgId,
):
    """Get a chat thread with its full message history."""
    supabase = get_supabase_service()

    # Get thread with ownership check
    thread = await supabase.get_chat_thread(thread_id)
    if not thread or thread.get("org_id") != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Konuşma bulunamadı",
        )

    # Get messages
    messages = await supabase.get_chat_messages(thread_id)

    return ChatHistoryResponse(
        thread=ChatThreadResponse(**thread),
        messages=[ChatMessageResponse(**m) for m in messages],
    )


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(
    thread_id: str,
    current_user: CurrentUser,
    org_id: CurrentOrgId,
):
    """Soft delete a chat thread (mark as inactive)."""
    supabase = get_supabase_service()

    # Get thread with ownership check
    thread = await supabase.get_chat_thread(thread_id)
    if not thread or thread.get("org_id") != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Konuşma bulunamadı",
        )

    await supabase.update_chat_thread(thread_id, {"is_active": False})
