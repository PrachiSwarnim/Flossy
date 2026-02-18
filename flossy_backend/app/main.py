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

# 1. Proxy Headers (Internal)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# 2. Dynamic Service Imports (Internal)
try:
    from app.core.middleware import ClerkAuthMiddleware
    app.add_middleware(ClerkAuthMiddleware)
    
    from app.api.v1.api_router import api_router
    app.include_router(api_router, prefix="/api")
    logger.info("✅ All routers and auth middleware loaded.")
except Exception as e:
    logger.error(f"❌ Critical error during service loading: {e}")

# 3. CORS (MUST BE ADDED LAST TO BE OUTERMOST)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://smileartistsdentalstudio.com",
        "https://www.smileartistsdentalstudio.com",
        "https://smile-artists-dental-studio.vercel.app",
        "https://flossy-ui.vercel.app",
        "https://flossy-ui-nine.vercel.app",
    ],
    allow_origin_regex=r"https?://.*smileartistsdentalstudio\.com|https?://.*vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.get("/health")
def health_check():
    return {
        "status": "healthy", 
        "service": "flossy-backend", 
        "version": "2.2.0",
        "deployment": os.getenv("K_REVISION", "local")
    }

@app.get("/health/db")
def health_db():
    """Diagnostic endpoint to check which database is being used."""
    from app.core.database import ACTIVE_DB_TYPE, ACTIVE_DB_URL_MASKED, get_engine
    from sqlalchemy import text
    
    db_info = {
        "db_type": ACTIVE_DB_TYPE,
        "db_url": ACTIVE_DB_URL_MASKED,
        "database_url_env_set": bool(os.getenv("DATABASE_URL")),
        "database_url_prefix": (os.getenv("DATABASE_URL") or "NOT_SET")[:30] + "...",
    }
    
    # Test actual connection
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            db_info["connection_test"] = "OK"
            
            # Check if tables exist and have data
            try:
                patients = conn.execute(text("SELECT count(*) FROM patients")).fetchone()
                appointments = conn.execute(text("SELECT count(*) FROM appointments")).fetchone()
                users = conn.execute(text("SELECT count(*) FROM users")).fetchone()
                db_info["table_counts"] = {
                    "patients": patients[0] if patients else 0,
                    "appointments": appointments[0] if appointments else 0,
                    "users": users[0] if users else 0,
                }
            except Exception as e:
                db_info["table_error"] = str(e)
    except Exception as e:
        db_info["connection_test"] = f"FAILED: {str(e)}"
    
    return db_info

@app.on_event("startup")
async def startup():
    logger.info("🚀 FLOSSY BACKEND STARTUP EVENT")
    
    # Ensure all tables exist (Auto-migration)
    try:
        from app.core.database import Base, engine
        import app.models  # Import models to register them with Base
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database schema synchronized (tables created if missing).")
    except Exception as e:
        logger.error(f"❌ Database error during startup: {e}")

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
