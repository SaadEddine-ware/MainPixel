from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.security import decode_token


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        skip_paths = ["/health", "/docs", "/openapi.json", "/api/v1/auth/login", "/api/v1/auth/refresh"]
        if any(request.url.path.startswith(p) for p in skip_paths):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return await call_next(request)

        token = auth_header.split(" ")[1]
        payload = decode_token(token)
        if payload:
            request.state.user_id = payload.get("sub")
            request.state.user_role = payload.get("role")
            request.state.school_id = payload.get("school_id")

        return await call_next(request)
