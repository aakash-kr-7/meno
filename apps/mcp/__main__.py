# ==============================================================================
# Entry point. python -m apps.mcp launches in stdio mode (default). Set MENO_MCP_TRANSPORT=http for
# team deployments.
# ==============================================================================
"""
Entry point. python -m apps.mcp launches in stdio mode (default). Set MENO_MCP_TRANSPORT=http for
team deployments.
"""

from core.config import settings
from apps.mcp.server import mcp
from apps.mcp.transport import run_stdio, run_http

def main() -> None:
    transport = (settings.MENO_MCP_TRANSPORT or "stdio").lower()
    if transport == "http":
        run_http(mcp)
    else:
        run_stdio(mcp)

if __name__ == "__main__":
    main()
