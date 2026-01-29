# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""iMessage database access layer.

Reads from ~/Library/Messages/chat.db (SQLite).
Requires Full Disk Access permission on macOS.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path


# macOS epoch starts 2001-01-01, timestamps are in nanoseconds
MAC_EPOCH = datetime(2001, 1, 1).timestamp()


def get_db_path() -> str:
    """Get the default iMessage database path."""
    return os.path.expanduser("~/Library/Messages/chat.db")


def mac_timestamp_to_iso(ns_timestamp: int | None) -> str | None:
    """Convert macOS nanosecond timestamp to ISO string."""
    if ns_timestamp is None:
        return None
    seconds = ns_timestamp / 1_000_000_000
    unix_timestamp = seconds + MAC_EPOCH
    return datetime.fromtimestamp(unix_timestamp).isoformat()


class IMessageDatabase:
    """Read-only access to the iMessage SQLite database."""

    def __init__(self, db_path: str | None = None) -> None:
        """Initialize database connection.

        Args:
            db_path: Path to chat.db, defaults to ~/Library/Messages/chat.db

        """
        self.db_path = db_path or get_db_path()
        self._conn: sqlite3.Connection | None = None

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create a database connection."""
        if self._conn is None:
            if not Path(self.db_path).exists():
                msg = (
                    f"iMessage database not found at {self.db_path}. "
                    "Make sure you're on macOS and have Full Disk Access enabled."
                )
                raise FileNotFoundError(msg)
            # Open in read-only mode with URI
            self._conn = sqlite3.connect(
                f"file:{self.db_path}?mode=ro",
                uri=True,
                check_same_thread=False,
            )
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def get_messages(
        self,
        limit: int = 50,
        chat_id: str | None = None,
        since: str | None = None,
        search: str | None = None,
    ) -> list[dict]:
        """Fetch messages from the database.

        Args:
            limit: Maximum number of messages to return
            chat_id: Filter by specific chat ID
            since: ISO date string to filter messages after
            search: Text search in message content

        Returns:
            List of message dictionaries

        """
        conn = self._get_connection()

        query = """
            SELECT
                m.rowid as id,
                m.guid,
                m.text,
                m.date as timestamp,
                m.is_from_me,
                m.is_read,
                m.is_sent,
                m.is_delivered,
                m.cache_has_attachments as has_attachments,
                h.id as sender,
                c.chat_identifier,
                c.display_name as chat_name,
                c.group_id
            FROM message m
            LEFT JOIN handle h ON m.handle_id = h.rowid
            LEFT JOIN chat_message_join cmj ON m.rowid = cmj.message_id
            LEFT JOIN chat c ON cmj.chat_id = c.rowid
            WHERE 1=1
        """
        params: list = []

        if chat_id:
            query += " AND c.chat_identifier = ?"
            params.append(chat_id)

        if since:
            # Convert ISO date to macOS timestamp
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            since_mac = (since_dt.timestamp() - MAC_EPOCH) * 1_000_000_000
            query += " AND m.date > ?"
            params.append(int(since_mac))

        if search:
            query += " AND m.text LIKE ?"
            params.append(f"%{search}%")

        query += " ORDER BY m.date DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        return [
            {
                "id": row["id"],
                "guid": row["guid"],
                "text": row["text"],
                "timestamp": mac_timestamp_to_iso(row["timestamp"]),
                "is_from_me": bool(row["is_from_me"]),
                "is_read": bool(row["is_read"]),
                "is_sent": bool(row["is_sent"]),
                "is_delivered": bool(row["is_delivered"]),
                "has_attachments": bool(row["has_attachments"]),
                "sender": row["sender"],
                "chat_identifier": row["chat_identifier"],
                "chat_name": row["chat_name"],
                "is_group": bool(row["group_id"]),
            }
            for row in rows
        ]

    def list_chats(self, limit: int = 50) -> list[dict]:
        """List all chats/conversations.

        Args:
            limit: Maximum number of chats to return

        Returns:
            List of chat dictionaries with metadata

        """
        conn = self._get_connection()

        query = """
            SELECT
                c.rowid as id,
                c.chat_identifier,
                c.display_name,
                c.group_id,
                c.service_name,
                (
                    SELECT COUNT(*)
                    FROM chat_message_join cmj
                    WHERE cmj.chat_id = c.rowid
                ) as message_count,
                (
                    SELECT MAX(m.date)
                    FROM message m
                    JOIN chat_message_join cmj ON m.rowid = cmj.message_id
                    WHERE cmj.chat_id = c.rowid
                ) as last_message_date
            FROM chat c
            ORDER BY last_message_date DESC
            LIMIT ?
        """

        cursor = conn.execute(query, [limit])
        rows = cursor.fetchall()

        return [
            {
                "id": row["id"],
                "chat_identifier": row["chat_identifier"],
                "display_name": row["display_name"],
                "is_group": bool(row["group_id"]),
                "service": row["service_name"],
                "message_count": row["message_count"],
                "last_message": mac_timestamp_to_iso(row["last_message_date"]),
            }
            for row in rows
        ]

    def get_chat_participants(self, chat_identifier: str) -> list[dict]:
        """Get participants of a chat.

        Args:
            chat_identifier: Chat identifier string

        Returns:
            List of participant dictionaries

        """
        conn = self._get_connection()

        query = """
            SELECT DISTINCT h.id, h.service
            FROM handle h
            JOIN chat_handle_join chj ON h.rowid = chj.handle_id
            JOIN chat c ON chj.chat_id = c.rowid
            WHERE c.chat_identifier = ?
        """

        cursor = conn.execute(query, [chat_identifier])
        rows = cursor.fetchall()

        return [{"handle": row["id"], "service": row["service"]} for row in rows]
