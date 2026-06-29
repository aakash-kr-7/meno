# ==============================================================================
# (a) What this file is: Auth for MENO MCP HTTP transport.
# (b) What it does: Reuses core/auth.py verify_key() — exactly one valid-key definition in all of MENO. Stdio transport is exempt (child process, no network boundary). HTTP transport enforces auth when APP_ENV != development.
# (c) How it fits into the MENO system: Guards incoming HTTP MCP requests with API key or Bearer token verification.
# ==============================================================================

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from core.config import settings
from core.auth import verify_key

class MCPAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Enforces auth when APP_ENV != development
        if settings.APP_ENV == "development":
            return await call_next(request)
            
        # Exempt the tools/list endpoint so clients can discover tools without auth
        path = request.url.path.rstrip("/")
        if path.endswith("/tools") or path.endswith("/tools/list"):
            return await call_next(request)
            
        # Check X-API-Key header or Bearer token
        api_key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        
        if not api_key and auth_header:
            if auth_header.lower().startswith("bearer "):
                api_key = auth_header[7:]
                
        if not api_key or not verify_key(api_key):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
        return await call_next(request)
