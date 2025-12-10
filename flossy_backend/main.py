# flossy_backend/main.py
import os
import json
import uuid
import jwt
import requests
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Callable, Optional, Generator

from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from sqlalchemy.orm import Session, joinedload
from dotenv import load_dotenv
from jwt import PyJWKClient

# ----- local project imports (keep these lightweight) -----
from database import SessionLocal, Base, engine
from models import User, Patient, Appointment, Interaction, LLMInteraction
from utils import ai_generate, cos_sim, embed_with_client  # these are assumed lightweight wrappers
# Agent app and optional routers are mounted lazily below if available
# Heavy RL/FAISS/GenAI clients are lazy-loaded (see loaders)

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
    print("⚠️ GOOGLE_API_KEY not set — some features will fail if called, but the app will still run.")

# ------------------------------------------------------------------
# App + CORS
# ------------------------------------------------------------------
app = FastAPI(title="FlossyAI API", description="AI Dental Assistant API-only backend")

# FRONTEND_ORIGINS can be CSV or "*" (for quick dev)
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

# ------------------------------------------------------------------
# Lazy globals (no heavy imports at module import time)
# ------------------------------------------------------------------
_jwks_client: Optional[PyJWKClient] = None

# GenAI client lazy holder
_genai_client = None

# RL bandit lazy holder
_bandit = None
ACTIONS = None
PROMPT_VARIANTS = None
MODELS = None

# FAISS lazy holders
_faiss_index = None
_faiss_chunks = None

# optional agent app (if agent_server.py is present)
_agent_app = None
_handle_user_utterance_text = None

# ------------------------------------------------------------------
# Utility: DB dependency
# ------------------------------------------------------------------
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------------------------------------------------
# JWKS / Clerk helpers
# ------------------------------------------------------------------
def get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(JWKS_URL)
    return _jwks_client

def verify_token(token: str) -> dict:
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
        print("JWT verification failed:", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

# ------------------------------------------------------------------
# Lazy loaders to avoid startup memory spikes
# ------------------------------------------------------------------
def get_genai_client():
    global _genai_client
    if _genai_client is None:
        try:
            # lazy import to avoid heavy imports at startup
            from google.genai import Client
            _genai_client = Client(api_key=GEMINI_API_KEY)
            print("GenAI client initialized (lazy).")
        except Exception as e:
            print("GenAI client failed to initialize:", e)
            _genai_client = None
    return _genai_client

def get_bandit_and_meta():
    """
    Lazily import RL bandit / ACTIONS / PROMPT_VARIANTS / MODELS.
    The module that defines these may be heavy; we only import when endpoint uses them.
    """
    global _bandit, ACTIONS, PROMPT_VARIANTS, MODELS
    if _bandit is None:
        try:
            # local RL modules (these modules should be careful with heavy work on import)
            from rl_core import bandit as bandit_obj, ACTIONS as _A, PROMPT_VARIANTS as _P, MODELS as _M, LinUCB as LinUCBClass
            ACTIONS, PROMPT_VARIANTS, MODELS = _A, _P, _M
            _bandit = bandit_obj if bandit_obj is not None else LinUCBClass(bandit_name="doctor_global_v1", actions=list(range(len(_A))), d=768, alpha=1.0)
            print("RL bandit loaded lazily.")
        except Exception as e:
            print("Failed to lazy-load RL bandit:", e)
            # fallback to a simple stub bandit to avoid crash (non-optimal)
            try:
                from rl_core import ACTIONS as _A, PROMPT_VARIANTS as _P, MODELS as _M
                ACTIONS, PROMPT_VARIANTS, MODELS = _A, _P, _M
            except Exception:
                ACTIONS, PROMPT_VARIANTS, MODELS = [], [], []
            _bandit = None
    return _bandit, ACTIONS, PROMPT_VARIANTS, MODELS

def load_faiss_index():
    """
    Lazy-load FAISS index only when /api/doctor_ai/query is called.
    Raises FileNotFoundError if index/metadata missing.
    """
    global _faiss_index, _faiss_chunks
    if _faiss_index is None:
        try:
            import faiss  # local import
        except Exception as e:
            raise RuntimeError("faiss import failed: " + str(e))

        if not os.path.exists("dental_embeddings.faiss"):
            raise FileNotFoundError("FAISS file missing: dental_embeddings.faiss")

        if not os.path.exists("dental_meta.json"):
            raise FileNotFoundError("Meta file missing: dental_meta.json")

        _faiss_index = faiss.read_index("dental_embeddings.faiss")
        with open("dental_meta.json", "r", encoding="utf-8") as f:
            meta = json.load(f)
        _faiss_chunks = meta.get("chunks", [])
        print("FAISS index loaded (lazy).")

    return _faiss_index, _faiss_chunks

# ------------------------------------------------------------------
# Optional agent app mounting (safe/lazy)
# ------------------------------------------------------------------
try:
    # attempt to import agent_server without running heavy startup code
    import importlib
    agent_mod = importlib.import_module("agent_server")
    _agent_app = getattr(agent_mod, "app", None)
    _handle_user_utterance_text = getattr(agent_mod, "handle_user_utterance_text", None)
    if _agent_app:
        app.mount("/agent", _agent_app)
        print("Agent subapp mounted at /agent (if available).")
except Exception as e:
    print("No agent_server mount (or failed import):", e)

# ------------------------------------------------------------------
# Middleware: auto-verify Clerk token and attach user info
# ------------------------------------------------------------------
EXEMPT_PATHS = {
    "/health",
    "/openapi.json",
    "/docs",
    "/redoc",
    "/api/public",
    "/agent",
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
            request.state.user = payload
        except HTTPException as e:
            return JSONResponse({"detail": e.detail}, status_code=e.status_code)

        return await call_next(request)

app.add_middleware(ClerkAuthMiddleware)

# ------------------------------------------------------------------
# Role requirement dependency
# ------------------------------------------------------------------
def require_role(role: str):
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
        return user
    return _require_role

# ------------------------------------------------------------------
# Lightweight static mount and db init routine
# ------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "flossy_web")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

def init_db():
    """
    Lightweight DB initialization. This is safe to run on low-memory platforms.
    Avoid heavy operations here.
    """
    try:
        Base.metadata.create_all(bind=engine)
        print("DB tables ensured (init_db).")
    except Exception as e:
        print("init_db() failed:", e)
        raise

# ------------------------------------------------------------------
# Public endpoints
# ------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}

@app.get("/api/public")
def public_info():
    return {"service": "FlossyAI API", "version": "1.0"}

# ------------------------------------------------------------------
# Auth endpoints (select_role / post_login)
# ------------------------------------------------------------------
@app.post("/api/auth/select_role")
def select_role(payload: dict, request: Request, db: Session = Depends(get_db)):
    role = payload.get("role")
    if role not in {"patient", "dentist"}:
        raise HTTPException(status_code=400, detail="Invalid role")

    user_payload = getattr(request.state, "user", None)
    if not user_payload:
        raise HTTPException(status_code=401, detail="Authentication required")

    email = (user_payload.get("email") or user_payload.get("email_address") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email missing in token")

    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user:
        user = User(email=email, role=role, created_at=datetime.now(timezone.utc))
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.role = role
        db.commit()

    if role == "patient":
        patient = db.query(Patient).filter(Patient.user_id == user.id).first()
        if not patient:
            patient = Patient(name=email.split("@")[0], phone="0000000000", user_id=user.id, contact_datetime=datetime.now(timezone.utc))
            db.add(patient)
            db.commit()

    return {"success": True, "role": role, "email": email}

@app.post("/api/auth/post_login")
def post_login(request: Request, db: Session = Depends(get_db)):
    user_payload = getattr(request.state, "user", None)
    if not user_payload:
        raise HTTPException(status_code=401, detail="Authentication required")

    email = (user_payload.get("email") or user_payload.get("email_address") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email missing in token")

    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user:
        user = User(email=email, created_at=datetime.now(timezone.utc))
        db.add(user)
        db.commit()
        db.refresh(user)

    return {"user": {"id": user.id, "email": user.email, "role": user.role}}

# ------------------------------------------------------------------
# Appointments endpoints
# ------------------------------------------------------------------
@app.get("/api/appointments/today")
def get_today_appointments(request: Request, db: Session = Depends(get_db)):
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
# AI / RL Endpoints (use lazy loading inside)
# ------------------------------------------------------------------
@app.post("/api/doctor_ai/query")
async def doctor_ai(request: Request):
    payload = await request.json()
    query = payload.get("query", "").strip()
    if not query:
        return JSONResponse({"answer": "No query provided."}, status_code=400)

    # Identify doctor name if token present (best-effort, non-blocking)
    auth = request.headers.get("Authorization")
    doctor_name = "Doctor"
    if auth and auth.startswith("Bearer ") and CLERK_SECRET_KEY:
        try:
            token = auth.split(" ")[1]
            decoded = verify_token(token)
            clerk_user_id = decoded.get("sub")
            if clerk_user_id:
                headers = {"Authorization": f"Bearer {CLERK_SECRET_KEY}"}
                resp = requests.get(f"https://api.clerk.dev/v1/users/{clerk_user_id}", headers=headers, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    doctor_name = data.get("full_name") or ((data.get("first_name") or "") + " " + (data.get("last_name") or "")).strip() or "Doctor"
        except Exception:
            pass

    # Lazy: ensure FAISS & chunks available
    try:
        index, chunks = load_faiss_index()
    except FileNotFoundError:
        return JSONResponse({"answer": "Knowledge base not available on the server."}, status_code=500)
    except Exception as e:
        return JSONResponse({"answer": f"Error loading KB: {e}"}, status_code=500)

    # Lazy: genai client
    genai_client = get_genai_client()

    # Lazy: bandit and RL meta
    bandit, ACTIONS, PROMPT_VARIANTS, MODELS = get_bandit_and_meta()

    # Embedding the query (use embed_with_client wrapper)
    try:
        query_emb = np.array(embed_with_client(genai_client, query), dtype=float)
    except Exception:
        query_emb = np.zeros(768, dtype=float)  # fallback

    x_context = query_emb
    if bandit:
        if x_context.shape[0] != bandit.d:
            if x_context.shape[0] > bandit.d:
                x_context = x_context[: bandit.d]
            else:
                pad = np.zeros(bandit.d - x_context.shape[0], dtype=float)
                x_context = np.concatenate([x_context, pad])

        chosen_action_id, scores = bandit.choose(x_context, eps=0.1)
        try:
            prompt_idx, temp, ctx_size, model_idx = ACTIONS[chosen_action_id]
            chosen_prompt_template = PROMPT_VARIANTS[prompt_idx]
            chosen_model = MODELS[model_idx]
        except Exception:
            chosen_prompt_template = "{query}"
            temp = 0.0
            ctx_size = 2
            chosen_model = None
    else:
        # fallback behavior if no bandit
        chosen_prompt_template = "{query}"
        temp = 0.0
        ctx_size = 2
        chosen_model = None
        chosen_action_id = -1

    qvec = np.array([query_emb], dtype="float32")
    ctx_size = max(1, min(ctx_size, len(chunks)))
    try:
        Dvals, I = index.search(qvec, ctx_size)
        context = "\n\n".join(chunks[i] for i in I[0] if i < len(chunks))
    except Exception:
        context = ""

    prompt = chosen_prompt_template.format(doctor=doctor_name, context=context, query=query)
    try:
        answer = ai_generate(prompt, temperature=temp, model=chosen_model, client_override=genai_client)
    except Exception as e:
        print("ai_generate failed:", e)
        answer = "FlossyAI couldn't generate an answer right now."

    # metrics & persistence
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
            prompt_variant=(prompt_idx if 'prompt_idx' in locals() else None),
            action_id=(chosen_action_id if 'chosen_action_id' in locals() else None),
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

    # AUTH (best-effort)
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

            if email:
                user = db.query(User).filter(User.email.ilike(email)).first()
                if user:
                    db_user_id = user.id
                    # get_or_create_patient should be defined in your codebase
                    try:
                        from utils import get_or_create_patient
                        patient = get_or_create_patient(db, user, clerk_name=clerk_name)
                    except Exception:
                        patient = None
    except Exception:
        pass

    # optional: async KB storage call (if agent_server exposes helper)
    try:
        if _handle_user_utterance_text and callable(_handle_user_utterance_text):
            import asyncio
            try:
                asyncio.create_task(
                    _handle_user_utterance_text(
                        query=user_msg,
                        user=str(db_user_id),
                        db_user_id=db_user_id,
                        clerk_name=clerk_name
                    )
                )
            except Exception:
                # fallback to synchronous call if background scheduling fails
                try:
                    await _handle_user_utterance_text(
                        query=user_msg,
                        user=str(db_user_id),
                        db_user_id=db_user_id,
                        clerk_name=clerk_name
                    )
                except Exception:
                    pass
    except Exception:
        pass

    # call into existing handler if available
    try:
        if _handle_user_utterance_text:
            reply = await _handle_user_utterance_text(user_msg, user=str(db_user_id), db_user_id=db_user_id, clerk_name=clerk_name)
        else:
            reply = "FlossyAI assistant not available."
    except Exception as e:
        print("Error in handle_user_utterance_text:", e)
        reply = "Sorry, I couldn't process that right now."
    finally:
        db.close()

    return {"answer": reply}

# ------------------------------------------------------------------
# Monitoring endpoints
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
# Startup event: lightweight init only
# ------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    # Only run the lightweight DB init at startup. Heavy imports are lazy.
    init_db()
    print("✅ FlossyAI API server started | Clerk JWT ready (lazy heavy loads).")

# ------------------------------------------------------------------
# If you want a tiny root page for sanity checks
# ------------------------------------------------------------------
@app.get("/")
def root():
    return {"service": "FlossyAI API", "status": "running"}

# End of file
