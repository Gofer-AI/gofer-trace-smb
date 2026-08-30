"""Launch the Gofer MCP service consumed by the TrueForge runtime."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

from vault.mcp_server import mcp


if __name__ == "__main__":
    os.environ.setdefault("GOFER_OFFLINE", "1")
    mcp.run(transport="streamable-http")
