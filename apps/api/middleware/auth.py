"""
FastAPI auth middleware. Checks X-API-Key on all requests except SKIP_PATHS. Bypassed in development mode with a startup warning.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from core.config import settings
from core.auth import verify_key

class AuthMiddleware(BaseHTTPMiddleware):
    SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)
        if settings.app_env == "development":
            return await call_next(request)  # warning logged on startup

        key = request.headers.get(settings.api_key_header)
        if not key or not verify_key(key):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"}
            )
        return await call_next(request)
