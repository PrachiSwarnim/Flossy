# app/main.py
import asyncio
import os
import sys
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from strawberry.fastapi import GraphQLRouter
from app.api.v1.graphql_schema import schema

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

    # Serve uploads static directory
    from fastapi.staticfiles import StaticFiles
    uploads_path = "uploads"
    if not os.path.exists(uploads_path):
        os.makedirs(uploads_path)
    app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")
    
    # GraphQL Endpoint
    graphql_app = GraphQLRouter(schema)
    app.include_router(graphql_app, prefix="/graphql")
    
    logger.info("✅ All routers, GraphQL, and auth middleware loaded.")
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
    from app.core.database import ACTIVE_DB_TYPE, ACTIVE_DB_URL_MASKED, LAST_DB_ERRORS, get_engine, DATABASE_URL
    from sqlalchemy import text, create_engine as sa_create_engine
    
    db_info = {
        "db_type": ACTIVE_DB_TYPE,
        "db_url": ACTIVE_DB_URL_MASKED,
        "database_url_env_set": bool(os.getenv("DATABASE_URL")),
        "database_url_prefix": (os.getenv("DATABASE_URL") or "NOT_SET")[:40] + "...",
        "connection_errors": LAST_DB_ERRORS,
    }
    
    # Test current active connection
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            db_info["connection_test"] = "OK"
            
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
    
    # Try live Postgres connection (separate from active engine)
    pg_url = os.getenv("DATABASE_URL", "")
    if pg_url and "sqlite" not in pg_url:
        if pg_url.startswith("postgres://"):
            pg_url = pg_url.replace("postgres://", "postgresql://")
        try:
            test_engine = sa_create_engine(pg_url, connect_args={"connect_timeout": 10, "sslmode": "require"})
            with test_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                # Count rows in Supabase
                pg_patients = conn.execute(text("SELECT count(*) FROM patients")).fetchone()
                pg_appts = conn.execute(text("SELECT count(*) FROM appointments")).fetchone()
                db_info["live_postgres_test"] = "SUCCESS"
                db_info["postgres_counts"] = {
                    "patients": pg_patients[0] if pg_patients else 0,
                    "appointments": pg_appts[0] if pg_appts else 0,
                }
            test_engine.dispose()
        except Exception as e:
            db_info["live_postgres_test"] = f"FAILED: {str(e)}"
    
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
