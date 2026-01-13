from typing import Callable
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from .security import verify_token

# Paths that do not require authentication
EXEMPT_PATHS = {
    "/health",
    "/api/public",
    "/api/docs",
    "/api/openapi.json",
    "/api/treatments",
    "/api/doctors",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/static"
}

class ClerkAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path
        
        # Check if path starts with any exempt path or is OPTIONS request
        if request.method == "OPTIONS" or any(path.startswith(p) for p in EXEMPT_PATHS):
            return await call_next(request)
        
        # Additional check for strict equality on some paths if needed, but prefix is usually safe for /docs etc.
        # LiveKit token gen used to be exempt in old main.py? 
        # "generate-token" was exempt.
        if "/api/v1/livekit/token" in path or "/api/livekit/token" in path:
             # Usually token generation requires auth if it's for a known user, 
             # but if it's for a guest interaction via voice agent it might be open.
             # The old code had "/api/generate-token" in EXEMPT_PATHS.
             pass

        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        
        try:
            token = auth.split(" ")[1]
            request.state.user = verify_token(token)
            return await call_next(request)
        except HTTPException as e:
            # Re-raise HTTPExceptions so FastAPI can handle them correctly
            # Note: Middleware handling of HTTPException is tricky, often better to return JSONResponse directly
            return JSONResponse({"detail": e.detail}, status_code=e.status_code)
        except Exception as e:
            # Log specific error to console and return it for debugging
            print(f"❌ Middleware error: {str(e)}")
            return JSONResponse({"detail": "Invalid Token or Server Error"}, status_code=401)
