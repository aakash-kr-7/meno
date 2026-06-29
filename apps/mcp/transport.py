# ==============================================================================
# Transport config. stdio (default): calling tool spawns this as child process, zero network exposure. http:
# streamable HTTP for team deployments, auth enforced.
# ==============================================================================
"""
Transport config. stdio (default): calling tool spawns this as child process, zero network exposure. http:
streamable HTTP for team deployments, auth enforced.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import uvicorn

from core.config import settings
from core.auth import verify_key

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if settings.app_env != "development":
            api_key = request.headers.get(settings.api_key_header)
            auth_header = request.headers.get("authorization")
            
            # If API key is not present directly, check Bearer token
            if not api_key and auth_header:
                if auth_header.lower().startswith("bearer "):
                    api_key = auth_header[7:]
            
            if not api_key or not verify_key(api_key):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
        
        return await call_next(request)

def run_stdio(server) -> None:
    """run MCP server in stdio mode"""
    server.run(transport="stdio")

def run_http(server) -> None:
    """run on settings.meno_mcp_host:settings.meno_mcp_port"""
    app = server.streamable_http_app()
    app.add_middleware(AuthMiddleware)
    uvicorn.run(app, host=settings.MENO_MCP_HOST, port=settings.MENO_MCP_PORT)
