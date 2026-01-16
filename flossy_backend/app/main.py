# app/main.py
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api_router import api_router
from app.core.middleware import ClerkAuthMiddleware
from app.core.database import init_db
from app.reminders import reminder_daemon

import uvicorn

app = FastAPI(
    title="FlossyAI API",
    description="AI Dental Assistant API-only backend"
)

# Middleware
app.add_middleware(ClerkAuthMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(api_router, prefix="/api")

@app.on_event("startup")
async def startup():
    init_db()
    asyncio.create_task(reminder_daemon())

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
