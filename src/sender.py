# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""iMessage sending via AppleScript.

Uses osascript to control Messages.app on macOS.
"""

from __future__ import annotations

import subprocess


def escape_applescript_string(text: str) -> str:
    """Escape special characters for AppleScript strings."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def send_message(recipient: str, text: str) -> dict:
    """Send a text message via iMessage.

    Args:
        recipient: Phone number (+1234567890) or email address
        text: Message text to send

    Returns:
        Dict with success status and any error message

    """
    escaped_text = escape_applescript_string(text)
    escaped_recipient = escape_applescript_string(recipient)

    script = f'''
        tell application "Messages"
            set targetService to 1st service whose service type = iMessage
            set targetBuddy to buddy "{escaped_recipient}" of targetService
            send "{escaped_text}" to targetBuddy
        end tell
    '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr.strip() or "Unknown AppleScript error",
            }

        return {"success": True, "recipient": recipient}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "AppleScript execution timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_to_chat(chat_id: str, text: str) -> dict:
    """Send a message to a group chat by chat ID.

    Args:
        chat_id: Chat identifier (e.g., "chat123456789")
        text: Message text to send

    Returns:
        Dict with success status and any error message

    """
    escaped_text = escape_applescript_string(text)
    escaped_chat_id = escape_applescript_string(chat_id)

    script = f'''
        tell application "Messages"
            set targetChat to chat id "{escaped_chat_id}"
            send "{escaped_text}" to targetChat
        end tell
    '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr.strip() or "Unknown AppleScript error",
            }

        return {"success": True, "chat_id": chat_id}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "AppleScript execution timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def check_messages_app() -> dict:
    """Check if Messages.app is running and accessible.

    Returns:
        Dict with messages_running bool and any error

    """
    script = '''
        tell application "System Events"
            return (name of processes) contains "Messages"
        end tell
    '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        is_running = result.stdout.strip().lower() == "true"

        return {
            "messages_running": is_running,
            "error": None if is_running else "Messages.app is not running",
        }

    except Exception as e:
        return {"messages_running": False, "error": str(e)}
