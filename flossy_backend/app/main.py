# app/main.py
import asyncio
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api_router import api_router
from app.core.middleware import ClerkAuthMiddleware
from app.reminders import reminder_daemon

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
import uvicorn

app = FastAPI(
    title="FlossyAI API",
    description="AI Dental Assistant API-only backend",
)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "flossy-backend"}

# Cloud Run / Load Balancer headers
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# Auth
app.add_middleware(ClerkAuthMiddleware)

# Routers
app.include_router(api_router, prefix="/api")

# CORS (this is fine)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://smileartistsdentalstudio.com",
        "https://www.smileartistsdentalstudio.com",
        "https://smile-artists-dental-studio.vercel.app",
    ],
    allow_origin_regex=r"https?://.*smileartistsdentalstudio\.com|https?://.*vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    print("🚀 FLOSSY BACKEND STARTED")
    asyncio.create_task(reminder_daemon())

# ✅ CLOUD RUN ENTRYPOINT
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )
