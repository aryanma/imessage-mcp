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
from sender import (
    check_messages_app,
    search_contacts,
    send_attachment,
    send_attachment_to_chat,
    send_message,
    send_to_chat,
)


if TYPE_CHECKING:
    pass


# --- Database instance ---

_db: IMessageDatabase | None = None
_watcher_cursor: int | None = None  # Tracks last seen message ID for watching


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
    description="Read iMessage/SMS messages with optional filters. Use chronological=true for conversation threads.",
    tags=["imessage", "read", "messages"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def read_messages(
    limit: int = 50,
    chat_id: str | None = None,
    since: str | None = None,
    search: str | None = None,
    chronological: bool = False,
) -> MessagesResult:
    """Read messages from iMessage database.

    Args:
        limit: Maximum number of messages to return (default 50)
        chat_id: Filter by specific chat identifier (phone/email or group chat ID)
        since: ISO date string to filter messages after (e.g., "2024-01-15T00:00:00")
        search: Text to search for in message content
        chronological: If true, oldest first (for reading threads); if false, newest first

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
            chronological=chronological,
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
    description="Get unread messages from all conversations",
    tags=["imessage", "read", "unread"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_unread_messages(limit: int = 50) -> MessagesResult:
    """Get unread messages.

    Args:
        limit: Maximum number of messages (default 50)

    Returns:
        MessagesResult with unread messages

    """
    try:
        db = get_db()
        messages = db.get_messages(limit=limit, unread_only=True)
        return MessagesResult(count=len(messages), messages=messages)
    except Exception as e:
        return MessagesResult(count=0, messages=[], error=str(e))


@dataclass(frozen=True)
class AttachmentResult:
    """Result from getting attachments."""

    message_id: int
    count: int
    attachments: list[dict]
    error: str | None = None


@tool(
    description="Get attachments for a specific message by message ID",
    tags=["imessage", "read", "attachments"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_attachments(message_id: int) -> AttachmentResult:
    """Get attachments for a message.

    Args:
        message_id: Message ID (from read_messages)

    Returns:
        AttachmentResult with attachment info

    """
    try:
        db = get_db()
        attachments = db.get_attachments(message_id)
        return AttachmentResult(message_id=message_id, count=len(attachments), attachments=attachments)
    except Exception as e:
        return AttachmentResult(message_id=message_id, count=0, attachments=[], error=str(e))


@tool(
    description="Send a file attachment via iMessage to a phone number or email",
    tags=["imessage", "send", "attachment"],
    annotations=ToolAnnotations(readOnlyHint=False),
)
async def send_file(recipient: str, file_path: str, text: str | None = None) -> SendResult:
    """Send a file attachment.

    Args:
        recipient: Phone number or email
        file_path: Absolute path to file
        text: Optional message text to send with file

    Returns:
        SendResult with success status

    """
    status = check_messages_app()
    if not status["messages_running"]:
        return SendResult(success=False, recipient=recipient, error="Messages.app is not running")

    result = send_attachment(recipient, file_path, text)

    return SendResult(
        success=result["success"],
        recipient=recipient,
        error=result.get("error"),
    )


@tool(
    description="Send a file attachment to a group chat",
    tags=["imessage", "send", "attachment", "group"],
    annotations=ToolAnnotations(readOnlyHint=False),
)
async def send_file_to_group(chat_id: str, file_path: str, text: str | None = None) -> SendResult:
    """Send a file attachment to a group chat.

    Args:
        chat_id: Group chat identifier
        file_path: Absolute path to file
        text: Optional message text to send with file

    Returns:
        SendResult with success status

    """
    status = check_messages_app()
    if not status["messages_running"]:
        return SendResult(success=False, chat_id=chat_id, error="Messages.app is not running")

    result = send_attachment_to_chat(chat_id, file_path, text)

    return SendResult(
        success=result["success"],
        chat_id=chat_id,
        error=result.get("error"),
    )


@dataclass(frozen=True)
class WatcherResult:
    """Result from watcher operations."""

    watching: bool
    cursor: int | None
    message: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class NewMessagesResult:
    """Result from checking new messages."""

    count: int
    messages: list[dict]
    cursor: int | None
    error: str | None = None


@tool(
    description="Start watching for new messages. Call check_new_messages periodically to get updates.",
    tags=["imessage", "watch"],
    annotations=ToolAnnotations(readOnlyHint=False),
)
async def start_watching() -> WatcherResult:
    """Start watching for new messages.

    Sets a cursor at the current latest message. Subsequent calls to
    check_new_messages will return messages received after this point.

    Returns:
        WatcherResult with watching status

    """
    global _watcher_cursor
    try:
        db = get_db()
        _watcher_cursor = db.get_latest_message_id()
        return WatcherResult(watching=True, cursor=_watcher_cursor, message="Watching started")
    except Exception as e:
        return WatcherResult(watching=False, cursor=None, error=str(e))


@tool(
    description="Check for new messages since watching started. Returns new messages and updates cursor.",
    tags=["imessage", "watch", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def check_new_messages() -> NewMessagesResult:
    """Check for new messages since last check.

    Returns messages received since start_watching was called (or since
    the last check_new_messages call). Updates the cursor automatically.

    Returns:
        NewMessagesResult with new messages

    """
    global _watcher_cursor
    if _watcher_cursor is None:
        return NewMessagesResult(count=0, messages=[], cursor=None, error="Not watching. Call start_watching first.")

    try:
        db = get_db()
        messages = db.get_messages_since_id(_watcher_cursor)

        # Update cursor to latest message
        if messages:
            _watcher_cursor = max(m["id"] for m in messages)

        return NewMessagesResult(count=len(messages), messages=messages, cursor=_watcher_cursor)
    except Exception as e:
        return NewMessagesResult(count=0, messages=[], cursor=_watcher_cursor, error=str(e))


@tool(
    description="Stop watching for new messages",
    tags=["imessage", "watch"],
    annotations=ToolAnnotations(readOnlyHint=False),
)
async def stop_watching() -> WatcherResult:
    """Stop watching for new messages.

    Clears the cursor. Call start_watching to begin again.

    Returns:
        WatcherResult confirming stopped

    """
    global _watcher_cursor
    _watcher_cursor = None
    return WatcherResult(watching=False, cursor=None, message="Watching stopped")


@dataclass(frozen=True)
class ContactsResult:
    """Result from contact lookup."""

    query: str
    count: int
    contacts: list[dict]
    error: str | None = None


@tool(
    description="Search macOS Contacts by name to find phone numbers and emails",
    tags=["contacts", "lookup"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def lookup_contact(name: str) -> ContactsResult:
    """Look up a contact by name.

    Args:
        name: Name to search for (first, last, or full name)

    Returns:
        ContactsResult with matching contacts and their phone/email

    """
    try:
        contacts = search_contacts(name)
        return ContactsResult(query=name, count=len(contacts), contacts=contacts)
    except Exception as e:
        return ContactsResult(query=name, count=0, contacts=[], error=str(e))


# Export all tools
imessage_tools = [
    check_status,
    read_messages,
    list_chats,
    get_chat_participants,
    get_unread_messages,
    get_attachments,
    send_imessage,
    send_to_group,
    send_file,
    send_file_to_group,
    lookup_contact,
    start_watching,
    check_new_messages,
    stop_watching,
]
