# main.py
import os
import json
import uuid
import jwt
import requests
import faiss
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Callable, Optional

from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session, joinedload
from dotenv import load_dotenv
from jwt import PyJWKClient

# ----- project-specific imports (adjust paths if needed) -----
from agent_server import app as agent_app, handle_user_utterance_text  # optional
from database import init_db, SessionLocal
from models import User, Patient, Appointment, Interaction, LLMInteraction
from utils import ai_generate, cos_sim, embed_with_client
from llm_client import genai_client
from rl_core import bandit, ACTIONS, PROMPT_VARIANTS, MODELS, LinUCB

# ------------------------------------------------------------------
# Environment + Clerk settings
# ------------------------------------------------------------------
load_dotenv()
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY")
CLERK_CLIENT_ID = os.getenv("CLERK_CLIENT_ID")
CLERK_CLIENT_SECRET = os.getenv("CLERK_CLIENT_SECRET")
CLERK_ISSUER = os.getenv("CLERK_ISSUER", "https://meet-grouse-33.clerk.accounts.dev")
JWKS_URL = f"{CLERK_ISSUER}/.well-known/jwks.json"

if not GEMINI_API_KEY:
    print("⚠️ GOOGLE_API_KEY not set — some features will fail if called.")

# make sure genai_client exists
try:
    genai_client = genai_client
except Exception:
    from google.genai import Client
    genai_client = Client(api_key=GEMINI_API_KEY)

# RL bandit safety
try:
    bandit = bandit
except Exception:
    D = 768
    bandit = LinUCB(bandit_name="doctor_global_v1", actions=list(range(len(ACTIONS))), d=D, alpha=1.0)

# ------------------------------------------------------------------
# FastAPI app
# ------------------------------------------------------------------
app = FastAPI(title="FlossyAI API", description="AI Dental Assistant API-only backend")

# Allow CORS for local frontend during development
FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGINS", "*")
if FRONTEND_ORIGINS == "*":
    allow_origins = ["*"]
else:
    allow_origins = [o.strip() for o in FRONTEND_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# If you still have a separate agent app, mount it (optional)
try:
    app.mount("/agent", agent_app)
except Exception:
    pass

# optional: mount static for any static assets (keep or remove as needed)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "flossy_web")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ------------------------------------------------------------------
# Database helpers
# ------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------------------------------------------------
# Clerk JWT verification helper
# ------------------------------------------------------------------
_jwks_client: Optional[PyJWKClient] = None

def get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(JWKS_URL)
    return _jwks_client

def verify_token(token: str) -> dict:
    """
    Verifies Clerk JWT using JWKS. Raises HTTPException(401) on failure.
    Returns the decoded payload.
    """
    try:
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=CLERK_ISSUER,
            options={"verify_aud": False, "verify_iat": False},
            leeway=10
        )
        return payload
    except Exception as e:
        # log error server-side for debugging
        print("JWT verification failed:", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

# ------------------------------------------------------------------
# Middleware: auto-verify Clerk token and attach user info
# ------------------------------------------------------------------
EXEMPT_PATHS = {
    "/health",
    "/openapi.json",
    "/docs",
    "/redoc",
    "/api/public",     # any public API prefix you want to keep open
    "/agent",          # if agent sub-app should be accessible
    "/static",
}

class ClerkAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path

        # Allow exempt paths
        if any(path.startswith(p) for p in EXEMPT_PATHS):
            return await call_next(request)

        # Allow OPTIONS preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            return JSONResponse({"detail": "Missing authorization token"}, status_code=401)

        token = auth.split(" ")[1]
        try:
            payload = verify_token(token)
            # attach to request.state for downstream handlers
            request.state.user = payload
        except HTTPException as e:
            return JSONResponse({"detail": e.detail}, status_code=e.status_code)

        return await call_next(request)

app.add_middleware(ClerkAuthMiddleware)

# ------------------------------------------------------------------
# Role requirement dependency
# ------------------------------------------------------------------
def require_role(role: str):
    """
    Returns a dependency function that verifies the user in request.state has the given role
    by checking the application's User table. Raises 403 if mismatch.
    """
    def _require_role(request: Request, db: Session = Depends(get_db)):
        user_payload = getattr(request.state, "user", None)
        if not user_payload:
            raise HTTPException(status_code=401, detail="Not authenticated")

        email = (user_payload.get("email") or user_payload.get("email_address") or "").lower()
        if not email:
            raise HTTPException(status_code=400, detail="Email missing in token")

        user = db.query(User).filter(User.email.ilike(email)).first()
        if not user or user.role != role:
            raise HTTPException(status_code=403, detail="Insufficient role permissions")
        # return the user DB object for convenience
        return user
    return _require_role

# ------------------------------------------------------------------
# API: Health + Public
# ------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}

@app.get("/api/public")
def public_info():
    return {"service": "FlossyAI API", "version": "1.0"}

# ------------------------------------------------------------------
# API: Auth endpoints
# ------------------------------------------------------------------
@app.post("/api/auth/select_role")
def select_role(payload: dict, request: Request, db: Session = Depends(get_db)):
    """
    Body: { role: "patient" | "dentist" }
    Requires Clerk Bearer token (middleware attaches request.state.user).
    """
    role = payload.get("role")
    if role not in {"patient", "dentist"}:
        raise HTTPException(status_code=400, detail="Invalid role")

    user_payload = getattr(request.state, "user", None)
    if not user_payload:
        raise HTTPException(status_code=401, detail="Authentication required")

    email = (user_payload.get("email") or user_payload.get("email_address") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email missing in token")

    # Create or update user record
    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user:
        user = User(email=email, role=role, created_at=datetime.now(timezone.utc))
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.role = role
        db.commit()

    # Ensure Patient row if patient role
    if role == "patient":
        patient = db.query(Patient).filter(Patient.user_id == user.id).first()
        if not patient:
            patient = Patient(name=email.split("@")[0], phone="0000000000", user_id=user.id, contact_datetime=datetime.now(timezone.utc))
            db.add(patient)
            db.commit()

    return {"success": True, "role": role, "email": email}

@app.post("/api/auth/post_login")
def post_login(request: Request, db: Session = Depends(get_db)):
    """
    Optional route: returns user DB info and role after a successful Clerk login.
    Expects Authorization header with Clerk session token.
    """
    user_payload = getattr(request.state, "user", None)
    if not user_payload:
        raise HTTPException(status_code=401, detail="Authentication required")

    email = (user_payload.get("email") or user_payload.get("email_address") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email missing in token")

    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user:
        # create user record with no role
        user = User(email=email, created_at=datetime.now(timezone.utc))
        db.add(user)
        db.commit()
        db.refresh(user)

    return {"user": {"id": user.id, "email": user.email, "role": user.role}}

# ------------------------------------------------------------------
# API: Appointments
# ------------------------------------------------------------------
@app.get("/api/appointments/today")
def get_today_appointments(request: Request, db: Session = Depends(get_db)):
    """
    Returns today's appointments for the authenticated user.
    If dentist: returns appointments for that dentist. If patient: for that patient.
    """
    user_payload = getattr(request.state, "user", None)
    if not user_payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    email = (user_payload.get("email") or user_payload.get("email_address") or "").lower()
    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user:
        user = User(email=email, created_at=datetime.now(timezone.utc))
        db.add(user)
        db.commit()
        db.refresh(user)

    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, now.day, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    base_query = (
        db.query(Appointment)
        .options(joinedload(Appointment.patient))
        .filter(
            Appointment.datetime >= start,
            Appointment.datetime < end,
            Appointment.status == "scheduled"
        )
        .order_by(Appointment.datetime.asc())
    )

    if user.role == "dentist":
        email_prefix = email.split("@")[0]
        clean = email_prefix.replace(".", " ")
        proper = " ".join([p.capitalize() for p in clean.split()])
        dentist_name = f"Dr. {proper}"
        appts = base_query.filter(Appointment.doctor_name.ilike(dentist_name)).all()
    else:
        patient = db.query(Patient).filter(Patient.user_id == user.id).first()
        if not patient:
            return {"appointments": []}
        appts = base_query.filter(Appointment.patient_id == patient.id).all()

    # map latest interactions per patient
    patient_ids = [a.patient_id for a in appts] if appts else []
    latest_interactions = []
    if patient_ids:
        latest_interactions = (
            db.query(Interaction)
            .filter(Interaction.patient_id.in_(patient_ids))
            .order_by(Interaction.patient_id, Interaction.created_at.desc())
            .all()
        )

    interaction_map = {}
    for inter in latest_interactions:
        if inter.patient_id not in interaction_map:
            interaction_map[inter.patient_id] = inter.message

    result = [
        {
            "time": a.datetime.isoformat(),
            "patient_name": a.patient.name if a.patient else "Unknown",
            "reason": interaction_map.get(a.patient_id, "N/A"),
            "doctor_name": a.doctor_name,
        }
        for a in appts
    ]

    return {"appointments": result}

@app.get("/api/appointments/dentist_upcoming")
def dentist_upcoming(request: Request, db: Session = Depends(get_db)):
    """
    Returns today's and upcoming appointments for the dentist.
    Requires authenticated user whose email maps to a dentist role.
    """
    user_payload = getattr(request.state, "user", None)
    if not user_payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    email = (user_payload.get("email") or user_payload.get("email_address") or "").lower()
    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user or user.role != "dentist":
        return {"today": [], "upcoming": []}

    email_prefix = email.split("@")[0]
    clean = email_prefix.replace(".", " ")
    proper = " ".join([p.capitalize() for p in clean.split()])
    dentist_name = f"Dr. {proper}"

    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    today_end = today_start + timedelta(days=1)

    today_appts = (
        db.query(Appointment)
        .options(joinedload(Appointment.patient))
        .filter(
            Appointment.doctor_name.ilike(dentist_name),
            Appointment.datetime >= today_start,
            Appointment.datetime < today_end,
        )
        .order_by(Appointment.datetime.asc())
        .all()
    )

    upcoming_appts = (
        db.query(Appointment)
        .options(joinedload(Appointment.patient))
        .filter(
            Appointment.doctor_name.ilike(dentist_name),
            Appointment.datetime >= today_end,
        )
        .order_by(Appointment.datetime.asc())
        .all()
    )

    def fmt(a):
        return {
            "id": a.id,
            "time": a.datetime.isoformat(),
            "patient_name": a.patient.name if a.patient else "Unknown",
            "phone": a.patient.phone if a.patient else "Unknown",
            "status": a.status,
            "reason": a.reason,
        }

    return {"today": [fmt(a) for a in today_appts], "upcoming": [fmt(a) for a in upcoming_appts]}

@app.post("/api/appointments/mark_completed/{appt_id}")
def mark_completed(appt_id: int, db: Session = Depends(get_db), user = Depends(require_role("dentist"))):
    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    appt.status = "completed"
    db.commit()
    return {"success": True}

@app.get("/api/appointments/next")
def get_next_appointment(request: Request, db: Session = Depends(get_db)):
    user_payload = getattr(request.state, "user", None)
    if not user_payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    email = (user_payload.get("email") or user_payload.get("email_address") or "").lower()
    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user:
        return {"appointment": None}

    now = datetime.now(timezone.utc)
    query = (
        db.query(Appointment)
        .options(joinedload(Appointment.patient))
        .filter(
            Appointment.datetime >= now,
            Appointment.status == "scheduled"
        )
        .order_by(Appointment.datetime.asc())
    )

    if user.role != "dentist":
        patient = db.query(Patient).filter(Patient.user_id == user.id).first()
        if not patient:
            return {"appointment": None}
        query = query.filter(Appointment.patient_id == patient.id)

    appt = query.first()
    if not appt:
        return {"appointment": None}

    return {"appointment": {
        "time": appt.datetime.isoformat(),
        "doctor_name": appt.doctor_name,
        "reason": appt.reason,
        "patient_name": appt.patient.name if appt.patient else "Unknown"
    }}

# ------------------------------------------------------------------
# AI / RL Endpoints
# ------------------------------------------------------------------
@app.post("/api/doctor_ai/query")
async def doctor_ai(request: Request):
    payload = await request.json()
    query = payload.get("query", "").strip()
    if not query:
        return JSONResponse({"answer": "No query provided."}, status_code=400)

    # Identify doctor name if token present
    auth = request.headers.get("Authorization")
    doctor_name = "Doctor"
    if auth and auth.startswith("Bearer "):
        token = auth.split(" ")[1]
        try:
            decoded = verify_token(token)
            clerk_user_id = decoded.get("sub")
            if clerk_user_id:
                headers = {"Authorization": f"Bearer {CLERK_SECRET_KEY}"}
                try:
                    resp = requests.get(f"https://api.clerk.dev/v1/users/{clerk_user_id}", headers=headers, timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        doctor_name = data.get("full_name") or ((data.get("first_name") or "") + " " + (data.get("last_name") or "")).strip() or "Doctor"
                except Exception:
                    pass
        except Exception:
            pass

    # Retrieval & generation (FAISS + your RL bandit)
    index = faiss.read_index("dental_embeddings.faiss")
    with open("dental_meta.json", "r", encoding="utf-8") as f:
        meta = json.load(f)
    chunks = meta.get("chunks", [])

    query_emb = np.array(embed_with_client(genai_client, query), dtype=float)
    x_context = query_emb
    if x_context.shape[0] != bandit.d:
        if x_context.shape[0] > bandit.d:
            x_context = x_context[: bandit.d]
        else:
            pad = np.zeros(bandit.d - x_context.shape[0], dtype=float)
            x_context = np.concatenate([x_context, pad])

    chosen_action_id, scores = bandit.choose(x_context, eps=0.1)
    prompt_idx, temp, ctx_size, model_idx = ACTIONS[chosen_action_id]
    chosen_prompt_template = PROMPT_VARIANTS[prompt_idx]
    chosen_model = MODELS[model_idx]

    qvec = np.array([query_emb], dtype="float32")
    ctx_size = max(1, min(ctx_size, len(chunks)))
    Dvals, I = index.search(qvec, ctx_size)
    context = "\n\n".join(chunks[i] for i in I[0] if i < len(chunks))

    prompt = chosen_prompt_template.format(doctor=doctor_name, context=context, query=query)
    answer = ai_generate(prompt, temperature=temp, model=chosen_model, client_override=genai_client)

    # metrics
    try:
        answer_vec = np.array(embed_with_client(genai_client, answer), dtype=float)
    except Exception:
        answer_vec = np.zeros_like(query_emb)
    try:
        context_vec = np.array(embed_with_client(genai_client, context), dtype=float) if context else np.zeros_like(query_emb)
    except Exception:
        context_vec = np.zeros_like(query_emb)

    semantic_similarity = float(cos_sim(query_emb, answer_vec))
    groundedness = float(cos_sim(answer_vec, context_vec))

    # persist interaction
    request_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        interaction = LLMInteraction(
            request_id=request_id,
            doctor_id=doctor_name,
            query=query,
            response=answer,
            context_used=context,
            semantic_similarity=semantic_similarity,
            groundedness=groundedness,
            prompt_variant=prompt_idx,
            action_id=chosen_action_id,
            temp_used=temp,
            model_used=chosen_model,
            ctx_size_used=ctx_size,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(interaction)
        db.commit()
    finally:
        db.close()

    return {"answer": answer, "request_id": request_id}

@app.post("/api/ai_response")
async def ai_response(request: Request):
    payload = await request.json()
    user_msg = payload.get("query", "")
    if not user_msg:
        return {"answer": "I didn't receive any message. Could you please repeat that?"}

    db = SessionLocal()
    db_user_id = None
    clerk_name = "Patient"
    patient = None

    # AUTH → resolve user if token present
    try:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            decoded = verify_token(token)
            email = decoded.get("email") or decoded.get("email_address")
            clerk_user_id = decoded.get("sub")

            # fetch clerk profile for clerk_name
            try:
                headers = {"Authorization": f"Bearer {CLERK_SECRET_KEY}"}
                resp = requests.get(f"https://api.clerk.dev/v1/users/{clerk_user_id}", headers=headers, timeout=6)
                if resp.status_code == 200:
                    data = resp.json()
                    full = data.get("full_name")
                    first = data.get("first_name") or ""
                    last = data.get("last_name") or ""
                    clerk_name = full or (first + " " + last).strip() or "Patient"
            except Exception:
                pass

            # local user
            if email:
                user = db.query(User).filter(User.email.ilike(email)).first()
                if user:
                    db_user_id = user.id
                    patient = get_or_create_patient(db, user, clerk_name=clerk_name)
    except Exception:
        pass

    # optional: async KB storage call (if agent_server exposes helper)
    try:
        from agent_server import handle_and_store_symptoms as kb_async_fn
        try:
            # schedule background task - rely on agent_server / event loop
            import asyncio
            asyncio.create_task(kb_async_fn(db, patient.id, user_msg))
        except Exception:
            # fallback synchronous
            await kb_async_fn(db, patient.id, user_msg)
    except Exception:
        pass

    # call into your existing handler
    try:
        reply = await handle_user_utterance_text(user_msg, user=str(db_user_id), db_user_id=db_user_id, clerk_name=clerk_name)
    except Exception as e:
        print("Error in handle_user_utterance_text:", e)
        return JSONResponse({"answer": "Sorry, I couldn't process that right now."}, status_code=500)
    finally:
        db.close()

    return {"answer": reply}

# ------------------------------------------------------------------
# Monitoring & metrics endpoints
# ------------------------------------------------------------------
@app.get("/api/metrics/llm")
def llm_metrics(db: Session = Depends(get_db)):
    rows = db.query(LLMInteraction).all()
    data = [{
        "request_id": r.request_id,
        "query": r.query,
        "semantic_similarity": r.semantic_similarity,
        "groundedness": r.groundedness,
        "instruction_score": r.instruction_score,
        "safety_score": r.safety_score,
        "coherence_score": r.coherence_score,
        "accuracy_score": r.accuarcy_score,
        "timestamp": r.timestamp
    } for r in rows]
    return {"interactions": data}

# ------------------------------------------------------------------
# Startup
# ------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    init_db()
    print("✅ FlossyAI API server started | Clerk JWT ready.")

