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


def send_attachment(recipient: str, file_path: str, text: str | None = None) -> dict:
    """Send a file attachment via iMessage.

    Args:
        recipient: Phone number or email
        file_path: Absolute path to file
        text: Optional message text

    Returns:
        Dict with success status

    """
    escaped_recipient = escape_applescript_string(recipient)
    escaped_path = escape_applescript_string(file_path)

    if text:
        escaped_text = escape_applescript_string(text)
        script = f'''
            tell application "Messages"
                set targetService to 1st service whose service type = iMessage
                set targetBuddy to buddy "{escaped_recipient}" of targetService
                send "{escaped_text}" to targetBuddy
                send POSIX file "{escaped_path}" to targetBuddy
            end tell
        '''
    else:
        script = f'''
            tell application "Messages"
                set targetService to 1st service whose service type = iMessage
                set targetBuddy to buddy "{escaped_recipient}" of targetService
                send POSIX file "{escaped_path}" to targetBuddy
            end tell
        '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        if result.returncode != 0:
            return {"success": False, "error": result.stderr.strip() or "AppleScript error"}

        return {"success": True, "recipient": recipient, "file": file_path}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_contacts(query: str) -> list[dict]:
    """Search macOS Contacts by name.

    Args:
        query: Name to search for

    Returns:
        List of matching contacts with phones/emails

    """
    escaped_query = escape_applescript_string(query)

    script = f'''
        set output to ""
        tell application "Contacts"
            set matchedPeople to (every person whose name contains "{escaped_query}")
            repeat with p in matchedPeople
                set n to name of p
                set ph to ""
                set em to ""
                repeat with x in phones of p
                    set ph to ph & (value of x) & "|"
                end repeat
                repeat with x in emails of p
                    set em to em & (value of x) & "|"
                end repeat
                set output to output & n & "	" & ph & "	" & em & "\n"
            end repeat
        end tell
        return output
    '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        if result.returncode != 0:
            return []

        contacts = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                name = parts[0].strip()
                phones = [p.strip() for p in parts[1].split("|") if p.strip()]
                emails = [e.strip() for e in parts[2].split("|") if e.strip()]
                if name:
                    contacts.append({"name": name, "phones": phones, "emails": emails})

        return contacts

    except Exception:
        return []


def send_attachment_to_chat(chat_id: str, file_path: str, text: str | None = None) -> dict:
    """Send a file attachment to a group chat.

    Args:
        chat_id: Chat identifier
        file_path: Absolute path to file
        text: Optional message text

    Returns:
        Dict with success status

    """
    escaped_chat_id = escape_applescript_string(chat_id)
    escaped_path = escape_applescript_string(file_path)

    if text:
        escaped_text = escape_applescript_string(text)
        script = f'''
            tell application "Messages"
                set targetChat to chat id "{escaped_chat_id}"
                send "{escaped_text}" to targetChat
                send POSIX file "{escaped_path}" to targetChat
            end tell
        '''
    else:
        script = f'''
            tell application "Messages"
                set targetChat to chat id "{escaped_chat_id}"
                send POSIX file "{escaped_path}" to targetChat
            end tell
        '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        if result.returncode != 0:
            return {"success": False, "error": result.stderr.strip() or "AppleScript error"}

        return {"success": True, "chat_id": chat_id, "file": file_path}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}
