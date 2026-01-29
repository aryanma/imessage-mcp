# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""iMessage tools for MCP server.

Provides read and send capabilities for iMessage on macOS.
Uses chat.db (SQLite) for reading and AppleScript for sending.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic.dataclasses import dataclass

from dedalus_mcp import tool
from dedalus_mcp.types import ToolAnnotations

from db import IMessageDatabase
from sender import check_messages_app, send_message, send_to_chat


if TYPE_CHECKING:
    pass


# --- Database instance ---

_db: IMessageDatabase | None = None


def get_db() -> IMessageDatabase:
    """Get or create the database instance."""
    global _db
    if _db is None:
        _db = IMessageDatabase()
    return _db


# --- Result Types ---


@dataclass(frozen=True)
class MessagesResult:
    """Result from reading messages."""

    count: int
    messages: list[dict]
    error: str | None = None


@dataclass(frozen=True)
class ChatsResult:
    """Result from listing chats."""

    count: int
    chats: list[dict]
    error: str | None = None


@dataclass(frozen=True)
class SendResult:
    """Result from sending a message."""

    success: bool
    recipient: str | None = None
    chat_id: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class StatusResult:
    """iMessage status check result."""

    platform: str
    messages_app_running: bool
    database_accessible: bool
    ready: bool
    error: str | None = None


# --- Tools ---


@tool(
    description="Check iMessage status - whether Messages.app is running and database is accessible",
    tags=["imessage", "status", "health"],
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def check_status() -> StatusResult:
    """Check if iMessage is ready to use.

    Returns:
        StatusResult with platform info and readiness status

    """
    import platform as plat

    status = check_messages_app()

    try:
        db = get_db()
        db._get_connection()
        db_accessible = True
        db_error = None
    except Exception as e:
        db_accessible = False
        db_error = str(e)

    return StatusResult(
        platform=plat.system(),
        messages_app_running=status["messages_running"],
        database_accessible=db_accessible,
        ready=status["messages_running"] and db_accessible,
        error=db_error,
    )


@tool(
    description="Read recent iMessage/SMS messages with optional filters for chat, date, or search",
    tags=["imessage", "read", "messages"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def read_messages(
    limit: int = 50,
    chat_id: str | None = None,
    since: str | None = None,
    search: str | None = None,
) -> MessagesResult:
    """Read messages from iMessage database.

    Args:
        limit: Maximum number of messages to return (default 50)
        chat_id: Filter by specific chat identifier (phone/email or group chat ID)
        since: ISO date string to filter messages after (e.g., "2024-01-15T00:00:00")
        search: Text to search for in message content

    Returns:
        MessagesResult with messages array and count

    """
    try:
        db = get_db()
        messages = db.get_messages(
            limit=limit,
            chat_id=chat_id,
            since=since,
            search=search,
        )
        return MessagesResult(count=len(messages), messages=messages)
    except Exception as e:
        return MessagesResult(count=0, messages=[], error=str(e))


@tool(
    description="List all iMessage conversations/chats with metadata like message count and last activity",
    tags=["imessage", "read", "chats"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_chats(limit: int = 50) -> ChatsResult:
    """List all conversations.

    Args:
        limit: Maximum number of chats to return (default 50)

    Returns:
        ChatsResult with chats array and count

    """
    try:
        db = get_db()
        chats = db.list_chats(limit=limit)
        return ChatsResult(count=len(chats), chats=chats)
    except Exception as e:
        return ChatsResult(count=0, chats=[], error=str(e))


@tool(
    description="Get participants of a specific chat/conversation by chat identifier",
    tags=["imessage", "read", "chats"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_chat_participants(chat_id: str) -> dict:
    """Get participants of a chat.

    Args:
        chat_id: Chat identifier

    Returns:
        Dict with chat_id and participants array

    """
    try:
        db = get_db()
        participants = db.get_chat_participants(chat_id)
        return {"chat_id": chat_id, "participants": participants}
    except Exception as e:
        return {"chat_id": chat_id, "participants": [], "error": str(e)}


@tool(
    description="Send an iMessage to a phone number (with country code like +14155551234) or email address",
    tags=["imessage", "send"],
    annotations=ToolAnnotations(readOnlyHint=False),
)
async def send_imessage(recipient: str, text: str) -> SendResult:
    """Send an iMessage.

    Args:
        recipient: Phone number (e.g., +14155551234) or email address
        text: Message text to send

    Returns:
        SendResult with success status

    """
    status = check_messages_app()
    if not status["messages_running"]:
        return SendResult(
            success=False,
            recipient=recipient,
            error="Messages.app is not running. Please open it first.",
        )

    result = send_message(recipient, text)

    return SendResult(
        success=result["success"],
        recipient=recipient,
        error=result.get("error"),
    )


@tool(
    description="Send an iMessage to a group chat using the chat ID (get chat IDs from list_chats)",
    tags=["imessage", "send", "group"],
    annotations=ToolAnnotations(readOnlyHint=False),
)
async def send_to_group(chat_id: str, text: str) -> SendResult:
    """Send a message to a group chat.

    Args:
        chat_id: Group chat identifier (from list_chats)
        text: Message text to send

    Returns:
        SendResult with success status

    """
    status = check_messages_app()
    if not status["messages_running"]:
        return SendResult(
            success=False,
            chat_id=chat_id,
            error="Messages.app is not running. Please open it first.",
        )

    result = send_to_chat(chat_id, text)

    return SendResult(
        success=result["success"],
        chat_id=chat_id,
        error=result.get("error"),
    )


@tool(
    description="Search messages by text content across all conversations",
    tags=["imessage", "read", "search"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def search_messages(query: str, limit: int = 20) -> MessagesResult:
    """Search messages by content.

    Args:
        query: Text to search for
        limit: Maximum results (default 20)

    Returns:
        MessagesResult with matching messages

    """
    try:
        db = get_db()
        messages = db.get_messages(limit=limit, search=query)
        return MessagesResult(count=len(messages), messages=messages)
    except Exception as e:
        return MessagesResult(count=0, messages=[], error=str(e))


# Export all tools
imessage_tools = [
    check_status,
    read_messages,
    list_chats,
    get_chat_participants,
    send_imessage,
    send_to_group,
    search_messages,
]
