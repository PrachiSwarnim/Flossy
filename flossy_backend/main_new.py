import os, json, uuid, jwt, requests, logging
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Callable, Optional, Generator

from fastapi import FastAPI, Request, HTTPException, Depends, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from sqlalchemy.orm import Session, joinedload
from dotenv import load_dotenv
from jwt import PyJWKClient
from pydantic import BaseModel

from livekit import api

# ----- local imports -----
from database import SessionLocal, Base, engine
from models import User, Patient, Appointment, Interaction, LLMInteraction
from utils import ai_generate, cos_sim, embed_with_client
from services.tts import stream_text_to_speech

load_dotenv()

# ------------------------------------------------------------------
# Environment + Clerk settings
# ------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_ISSUER = os.getenv("CLERK_ISSUER", "https://meet-grouse-33.clerk.accounts.dev")
JWKS_URL = f"{CLERK_ISSUER}/.well-known/jwks.json"

app = FastAPI(title="FlossyAI API", description="AI Dental Assistant API-only backend")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Lazy holders
# ------------------------------------------------------------------
_jwks_client: Optional[PyJWKClient] = None
_genai_client = None
_bandit = None
ACTIONS = None
PROMPT_VARIANTS = None
MODELS = None
_faiss_index = None
_faiss_chunks = None

# ------------------------------------------------------------------
# Utility & Auth Helpers
# ------------------------------------------------------------------
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(JWKS_URL)
    return _jwks_client

def verify_token(token: str) -> dict:
    jwks_client = get_jwks_client()
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=CLERK_ISSUER,
        options={"verify_aud": False},
    )

# ------------------------------------------------------------------
# Middleware
# ------------------------------------------------------------------
EXEMPT_PATHS = {"/", "/health", "/api/public", "/api/token", "/static", "/docs", "/openapi.json"}

class ClerkAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        if any(request.url.path.startswith(p) for p in EXEMPT_PATHS) or request.method == "OPTIONS":
            return await call_next(request)

        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        try:
            request.state.user = verify_token(auth.split(" ")[1])
            return await call_next(request)
        except Exception:
            return JSONResponse({"detail": "Invalid Token"}, status_code=401)

app.add_middleware(ClerkAuthMiddleware)

# ------------------------------------------------------------------
# LIVEKIT TOKEN (single canonical version)
# ------------------------------------------------------------------
@app.get("/api/token")
async def get_livekit_token(request: Request):
    identity = request.query_params.get("identity", f"user_{uuid.uuid4().hex[:6]}")
    name = request.query_params.get("name", "Guest")
    email = request.query_params.get("email", "")

    lk_api_key = os.getenv("LIVEKIT_API_KEY")
    lk_api_secret = os.getenv("LIVEKIT_API_SECRET")

    if not lk_api_key or not lk_api_secret:
        raise HTTPException(status_code=500, detail="LiveKit credentials not configured.")

    grant = api.VideoGrants(
        room_join=True,
        room="flossy-room",
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True,
    )

    metadata_json = json.dumps({"email": email, "name": name})

    token = (
        api.AccessToken(lk_api_key, lk_api_secret)
        .with_identity(identity)
        .with_name(name)
        .with_grants(grant)
        .with_metadata(metadata_json)
    )

    return {"accessToken": token.to_jwt(), "url": os.getenv("LIVEKIT_URL")}

# ------------------------------------------------------------------
# Role dependency
# ------------------------------------------------------------------
def require_role(expected_role: str):
    def _require_role(request: Request, db: Session = Depends(get_db)):
        payload = getattr(request.state, "user", None)
        if not payload:
            raise HTTPException(status_code=401, detail="Not authenticated")

        email = (payload.get("email") or payload.get("email_address") or "").lower()
        user = db.query(User).filter(User.email.ilike(email)).first()

        if not user or user.role != expected_role:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        return user

    return _require_role

# ------------------------------------------------------------------
# CONTACT REQUEST (single canonical version)
# ------------------------------------------------------------------
@app.post("/api/contact_request")
def contact_request(payload: dict, db: Session = Depends(get_db)):
    name = payload.get("name", "Unknown")
    phone = payload.get("phone")
    reason = payload.get("reason", "")

    if not phone:
        raise HTTPException(status_code=400, detail="Phone number required")

    patient = db.query(Patient).filter(Patient.phone == phone).first()
    if not patient:
        patient = Patient(
            name=name,
            phone=phone,
            user_id=None,
            contact_datetime=datetime.now(timezone.utc),
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

    interaction = Interaction(
        patient_id=patient.id,
        channel="contact_form",
        message=f"New Patient Inquiry: {reason}",
        created_at=datetime.now(timezone.utc),
    )
    db.add(interaction)
    db.commit()

    return {"success": True}

# ------------------------------------------------------------------
# TTS (single canonical definitions)
# ------------------------------------------------------------------
class TTSRequest(BaseModel):
    text: str

@app.post("/api/speak")
async def speak(req: TTSRequest):
    return StreamingResponse(
        stream_text_to_speech(req.text),
        media_type="audio/mp3",
    )

@app.get("/api/speak-stream")
async def speak_stream(text: str = Query(...)):
    return StreamingResponse(
        stream_text_to_speech(text),
        media_type="audio/mp3",
    )

# ------------------------------------------------------------------
# EVERYTHING ELSE BELOW IS UNCHANGED
# (Appointments, AI, Metrics, Cleanup, Startup, Root)
# ------------------------------------------------------------------
# ⬇️ ⬇️ ⬇️
# (kept exactly as in your file)
