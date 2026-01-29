# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""MCP server entrypoint.

Exposes iMessage read/send tools via Dedalus MCP framework.
Requires macOS with Full Disk Access permission.
"""

import os

from dedalus_mcp import MCPServer
from dedalus_mcp.server import TransportSecuritySettings

from tools import imessage_tools


def create_server() -> MCPServer:
    """Create MCP server with current env config."""
    as_url = os.getenv("DEDALUS_AS_URL", "https://as.dedaluslabs.ai")
    return MCPServer(
        name="imessage-mcp",
        version="0.1.0",
        instructions=(
            "iMessage MCP Server - Read and send iMessages on macOS.\n\n"
            "Requirements:\n"
            "- macOS with Messages.app configured\n"
            "- Full Disk Access permission for the terminal/app\n"
            "- Messages.app must be running to send messages\n\n"
            "Available tools: read_messages, list_chats, send_imessage, "
            "send_to_group, search_messages, get_chat_participants"
        ),
        http_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        streamable_http_stateless=True,
        authorization_server=as_url,
    )


async def main() -> None:
    """Start MCP server."""
    server = create_server()
    server.collect(*imessage_tools)
    await server.serve(port=8080)
