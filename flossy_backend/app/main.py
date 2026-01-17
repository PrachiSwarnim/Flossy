# app/main.py
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import ALLOWED_ORIGINS

from app.api.v1.api_router import api_router
from app.core.middleware import ClerkAuthMiddleware
from app.core.database import init_db
from app.reminders import reminder_daemon

import uvicorn

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.errors import ServerErrorMiddleware

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

app = FastAPI(
    title="FlossyAI API",
    description="AI Dental Assistant API-only backend",
)

# 1. Handle Proxy Headers (Correct way for Cloud Run/Load Balancers)
# This prevents scheme-switching redirects (HTTPS -> HTTP)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# 2. Add Auth Middleware (Clerk)
app.add_middleware(ClerkAuthMiddleware)



# Specific origins are now in app.core.config

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Routers
app.include_router(api_router, prefix="/api")

@app.on_event("startup")
async def startup():
    init_db()
    asyncio.create_task(reminder_daemon())

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
