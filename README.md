# imessage-mcp

MCP server for iMessage on macOS. Read and send messages via AI agents.

## Requirements

- macOS
- Python 3.10+
- Full Disk Access (for reading messages)
- Messages.app running (for sending)

## Setup

```bash
uv sync
```

### Grant Full Disk Access

1. **System Settings** → **Privacy & Security** → **Full Disk Access**
2. Add your terminal (Terminal, iTerm, VS Code, Cursor)
3. Restart the terminal

## Run

```bash
cd src && python main.py
```

Server runs at `http://127.0.0.1:8080/mcp`

## Architecture

| Layer | Component | Description |
|-------|-----------|-------------|
| Transport | HTTP/MCP | Streamable HTTP via dedalus-mcp |
| Reads | `chat.db` | Direct SQL on `~/Library/Messages/chat.db` |
| Sends | `osascript` | AppleScript RPC to Messages.app |

## Tools

| Tool | Description |
|------|-------------|
| `check_status` | Check if iMessage is ready |
| `read_messages` | Read messages (filters: chat_id, search, since, chronological) |
| `list_chats` | List conversations |
| `get_chat_participants` | Get chat members |
| `get_unread_messages` | Get unread messages |
| `get_attachments` | Get attachments for a message |
| `download_attachment` | Copy attachment to local path |
| `send_imessage` | Send text to phone/email |
| `send_to_group` | Send text to group chat |
| `send_file` | Send file to phone/email |
| `send_file_to_group` | Send file to group chat |
| `lookup_contact` | Search Contacts.app by name |
| `start_watching` | Start watching for new messages |
| `check_new_messages` | Get messages since last check |
| `stop_watching` | Stop watching |

## MCP Config

Add to Claude Desktop config:

```json
{
  "mcpServers": {
    "imessage": {
      "url": "http://127.0.0.1:8080/mcp"
    }
  }
}
```
