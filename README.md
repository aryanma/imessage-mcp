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
| `read_messages` | Read messages with filters |
| `list_chats` | List conversations |
| `get_chat_participants` | Get chat members |
| `send_imessage` | Send to phone/email |
| `send_to_group` | Send to group chat |
| `search_messages` | Search messages |

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
