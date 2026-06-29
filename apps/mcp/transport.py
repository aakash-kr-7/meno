# ==============================================================================
# (a) What this file is: Transport config for MENO MCP server.
# (b) What it does: Runs MCP server over stdio (default) or HTTP with auth middleware.
# (c) How it fits into the MENO system: Manages network boundaries and connections for MCP clients.
# ==============================================================================

import uvicorn

from core.config import settings
from apps.mcp.auth import MCPAuthMiddleware

def run_stdio(server) -> None:
    """run MCP server in stdio mode"""
    server.run(transport="stdio")

def run_http(server) -> None:
    """run on settings.meno_mcp_host:settings.meno_mcp_port"""
    app = server.streamable_http_app()
    app.add_middleware(MCPAuthMiddleware)
    uvicorn.run(app, host=settings.MENO_MCP_HOST, port=settings.MENO_MCP_PORT)
