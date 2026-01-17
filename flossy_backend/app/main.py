# app/main.py
import asyncio
import os
import sys
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flossy-backend")

app = FastAPI(
    title="FlossyAI API",
    description="AI Dental Assistant API",
)

# 1. CORS (Outermost)
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

# 2. Proxy Headers (for Cloud Run)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# 3. Dynamic Service Imports (Safe Boot)
try:
    from app.core.middleware import ClerkAuthMiddleware
    app.add_middleware(ClerkAuthMiddleware)
    
    from app.api.v1.api_router import api_router
    app.include_router(api_router, prefix="/api")
    logger.info("✅ All routers and auth middleware loaded.")
except Exception as e:
    logger.error(f"❌ Critical error during service loading: {e}")
    # We still allow the app to start so we can see logs/health

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "flossy-backend", "deployment": os.getenv("K_REVISION", "local")}

@app.on_event("startup")
async def startup():
    logger.info("🚀 FLOSSY BACKEND STARTUP EVENT")
    try:
        from app.reminders import reminder_daemon
        asyncio.create_task(reminder_daemon())
        logger.info("✅ Reminder daemon started.")
    except Exception as e:
        logger.error(f"⚠️ Could not start reminder daemon: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
