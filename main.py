from operator import index
import os
import jwt
import requests
import json
import numpy as np
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from routers.sms import router as sms_router
from agent_server import app as agent_app, handle_user_utterance_text
from database import init_db, SessionLocal
from models import User, Patient, Appointment, Interaction, LLMInteraction, final_score
from dotenv import load_dotenv
from sqlalchemy.orm import Session, joinedload
from jwt import PyJWKClient
import faiss
from google.genai import Client
from rl_core import bandit, ACTIONS, PROMPT_VARIANTS, MODELS, build_actions, LinUCB
from llm_client import genai_client
from utils import ai_generate, cos_sim, embed_with_client

# --------------------------------------------------------------------------
#                         ENV + CLERK SETUP
# --------------------------------------------------------------------------

load_dotenv()
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
CLERK_API_BASE = "https://api.clerk.dev/v1"
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY")
CLERK_CLIENT_ID = os.getenv("CLERK_CLIENT_ID")
CLERK_CLIENT_SECRET = os.getenv("CLERK_CLIENT_SECRET")
CLERK_ISSUER = os.getenv("CLERK_ISSUER", "https://meet-grouse-33.clerk.accounts.dev")
JWKS_URL = f"{CLERK_ISSUER}/.well-known/jwks.json"

if not GEMINI_API_KEY:
    print("⚠️ GOOGLE_API_KEY not set — some features will fail if called.")

# instantiate genai_client if not already imported (llm_client should provide it, but keep safe)
try:
    genai_client = genai_client
except Exception:
    genai_client = Client(api_key=GEMINI_API_KEY)

# --------------------------------------------------------------------------
#                            FASTAPI SETUP
# --------------------------------------------------------------------------

app = FastAPI(title="FlossyAI", description="AI Dental Assistant Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "flossy_web")
app.mount("/agent", agent_app)
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

TEMPS = [0.0, 0.2, 0.4]
CTX_SIZES = [1, 3, 5]


ACTION_IDS = list(range(len(ACTIONS)))

# choose embedding dims for LinUCB context dimension
D = 768
try:
    bandit = bandit
except Exception:
    bandit = LinUCB(bandit_name="doctor_global_v1", actions=ACTION_IDS, d=D, alpha=1.0)

# --------------------------------------------------------------------------
#                         Helper functions
# --------------------------------------------------------------------------
def load_html(filename: str):
    try:
        file_path = os.path.join("flossy_web", filename)
        with open(file_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error loading {filename}</h1><p>{e}</p>", status_code=500)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_or_create_patient(db: Session, user: User, clerk_name: str = None, phone: str = None):
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if patient:
        return patient

    new_patient = Patient(
        name=clerk_name or "Unknown",
        phone=phone or "0000000000",
        user_id=user.id,
        contact_datetime=datetime.now(timezone.utc)
    )
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    return new_patient


def verify_token(token: str):
    try:
        jwks_client = PyJWKClient(JWKS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=CLERK_ISSUER,
            options={"verify_aud": False, "verify_iat": False},
            leeway=10
        )
        print("✅ Token verified:", {k: payload.get(k) for k in ("sub", "email", "email_address")})
        return payload
    except Exception as e:
        print("❌ JWT verification failed:", e)
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def store_user_if_new(db: Session, email: str, role: str = None, name: str = None):
    user = None
    try:
        if not email:
            print("⚠️ No email provided — skipping user creation.")
            return None

        email = email.lower().strip()
        valid_roles = {"dentist", "patient"}

        user = db.query(User).filter(User.email.ilike(email)).first()
        if not user:
            new_user = User(
                email=email,
                role=role if role in valid_roles else None,
                created_at=datetime.now(timezone.utc)
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            print(f"✅ Added new user: {email} ({new_user.role or 'no role'})")
            user = new_user
        elif user.role is None and role in valid_roles:
            user.role = role
            db.commit()
            db.refresh(user)
            print(f"🔄 Updated {email} role → {role}")
        else:
            print(f"ℹ️ User exists: {email} ({user.role})")
        return user
    except Exception as e:
        db.rollback()
        print(f"⚠️ Error storing user {email}: {e}")
        return user

# utilities
def update_implicit_reward(request_id, value):
    db = SessionLocal()
    try:
        row = db.query(LLMInteraction).filter_by(request_id=request_id).first()
        if row:
            row.implicit_reward = value
            db.commit()
    finally:
        db.close()

# --------------------------------------------------------------------------
#                            ROUTES (kept intact)
# --------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def serve_landing():
    return load_html("landing.html")


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return load_html("login.html")


@app.get("/signup", response_class=HTMLResponse)
def signup_page():
    return load_html("signup.html")


@app.get("/role_selection", response_class=HTMLResponse)
def role_selection():
    return load_html("role_selection.html")


@app.get("/dental_tourism", response_class=HTMLResponse)
def dental_tourism():
    return load_html("dental_tourism.html")


@app.get("/services", response_class=HTMLResponse)
def services():
    return load_html("services.html")


@app.get("/logout", response_class=HTMLResponse)
def logout():
    return RedirectResponse(url="/", status_code=302)

@app.get("/post_login", response_class=HTMLResponse)
async def post_login(request: Request):
    return load_html("post_login.html")

@app.get("/redirect_user")
async def redirect_user(request: Request, db: Session = Depends(get_db)):
    clerk_token = request.query_params.get("token")
    role_param = request.query_params.get("role")
    email_param = request.query_params.get("email")

    if not clerk_token:
        return RedirectResponse(url="/login?error=missing_token", status_code=302)

    try:
        payload = verify_token(clerk_token)
        user_id_clerk = payload.get("sub")

        # ----------------------------
        # Extract user email
        # ----------------------------
        email = (email_param or "").strip() or None
        if not email:
            email = payload.get("email") or payload.get("email_address") or None

        # fallback
        if not email:
            email = f"{user_id_clerk}@auto.clerk"

        email = email.lower().strip()

        # ----------------------------
        # Create/update user in DB
        # ----------------------------
        user = store_user_if_new(db, email, role=role_param)

        if not user:
            return RedirectResponse(url="/login?error=user_creation_failed", status_code=302)

        # ----------------------------
        # Redirect based on role
        # ----------------------------
        if user.role == "dentist":
            return RedirectResponse(url=f"/dentist?token={clerk_token}", status_code=302)

        if user.role == "patient":
            return RedirectResponse(url=f"/patient?token={clerk_token}", status_code=302)

        return RedirectResponse(url=f"/role_selection?token={clerk_token}&email={email}", status_code=302)

    except Exception as e:
        print("❌ redirect_user failure:", e)
        return RedirectResponse(url="/login?error=redirect_failure", status_code=302)

@app.get("/dentist", response_class=HTMLResponse)
def user_dashboard(request: Request):
    token = request.query_params.get("token")
    if not token:
        return RedirectResponse(url="/login")

    try:
        verify_token(token)
    except HTTPException:
        print("⚠️ Token failed verification. Redirecting user to /login.")
        return RedirectResponse(url="/login?reason=token_expired", status_code=302)

    return load_html("user_dashboard.html")

@app.get("/patient", response_class=HTMLResponse)
def patient_dashboard(request: Request):
    token = request.query_params.get("token")
    if not token:
        return RedirectResponse(url="/login")

    try:
        verify_token(token)
    except HTTPException:
        print("⚠️ Token failed verification. Redirecting user to /login.")
        return RedirectResponse(url="/login?reason=token_expired", status_code=302)

    return load_html("patient_dashboard.html")

@app.get("/signup/sso-callback")
async def clerk_signup_callback():
    return RedirectResponse(url="/post_login")


@app.get("/appointments/today")
def get_today_appointments(request: Request, db: Session = Depends(get_db)):
    token = request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Missing token")

    payload = verify_token(token)
    email = payload.get("email") or payload.get("email_address")
    if not email:
        raise HTTPException(status_code=401, detail="Email missing in token")

    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user:
        user = store_user_if_new(db, email)
        if not user:
            raise HTTPException(status_code=500, detail="User creation failed")

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


@app.get("/appointments/dentist_upcoming")
def dentist_upcoming(request: Request, db: Session = Depends(get_db)):
    token = request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Missing token")

    payload = verify_token(token)
    email = payload.get("email") or payload.get("email_address")
    if not email:
        raise HTTPException(status_code=401, detail="Email missing")

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

    def format_appt(a):
        return {
            "id": a.id,
            "time": a.datetime.isoformat(),
            "patient_name": a.patient.name if a.patient else "Unknown",
            "phone": a.patient.phone if a.patient else "Unknown",
            "status": a.status,
            "reason": a.reason,
        }

    return {
        "today": [format_appt(a) for a in today_appts],
        "upcoming": [format_appt(a) for a in upcoming_appts],
    }


@app.post("/appointments/mark_completed/{appt_id}")
def mark_completed(appt_id: int, db: Session = Depends(get_db)):
    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    appt.status = "completed"
    db.commit()
    return {"success": True}


# --------------------------------------------------------------------------
#                          RL DOCTOR API (core)
# --------------------------------------------------------------------------
@app.post("/doctor_ai/query")
async def doctor_ai(request: Request):
    payload = await request.json()
    query = payload.get("query", "").strip()
    if not query:
        return JSONResponse({"answer": "No query provided."}, status_code=400)

    # identify doctor name if token present
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
                    resp = requests.get(f"{CLERK_API_BASE}/users/{clerk_user_id}", headers=headers, timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        doctor_name = data.get("full_name") or ((data.get("first_name") or "") + " " + (data.get("last_name") or "")).strip() or "Doctor"
                except Exception:
                    pass
        except Exception:
            pass

    # FAISS + KB
    index = faiss.read_index("dental_embeddings.faiss")
    with open("dental_meta.json", "r", encoding="utf-8") as f:
        meta = json.load(f)
    chunks = meta.get("chunks", [])

    # embed query
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

    # retrieval
    qvec = np.array([query_emb], dtype="float32")
    ctx_size = max(1, min(ctx_size, len(chunks)))
    Dvals, I = index.search(qvec, ctx_size)
    context = "\n\n".join(chunks[i] for i in I[0] if i < len(chunks))

    # build prompt & generate
    prompt = chosen_prompt_template.format(doctor=doctor_name, context=context, query=query)
    answer = ai_generate(prompt, temperature=temp, model=chosen_model, client_override=genai_client)

    # immediate metrics
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

    # persist interaction (for nightly RL updates)
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


# --------------------------------------------------------------------------
#                          Patient AI (text) — RL-enabled
# --------------------------------------------------------------------------
@app.post("/ai_response")
async def ai_response(request: Request, payload: dict, db: Session = Depends(get_db)):
    user_msg = payload.get("query", "")
    if not user_msg:
        return {"answer": "I didn't receive any message. Could you please repeat that?"}

    db_user_id = None
    clerk_name = "Patient"
    patient = None

    # AUTH → Resolve user if token present
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
                resp = requests.get(f"{CLERK_API_BASE}/users/{clerk_user_id}", headers=headers, timeout=6)
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

    # symptom KB async process (fire & forget; non-blocking)
    if db_user_id and patient and user_msg:
        try:
            # handle_and_store_symptoms is async in agent_server; we call as background task if available
            from agent_server import handle_and_store_symptoms as kb_async_fn
            try:
                asyncio.create_task(kb_async_fn(db, patient.id, user_msg))
            except Exception:
                # If cannot create task, call synchronously
                await kb_async_fn(db, patient.id, user_msg)
        except Exception:
            # If not available, ignore
            pass

    # call into your text handler (already RL-enabled inside agent_server)
    try:
        reply = await handle_user_utterance_text(
            user_msg,
            user=str(db_user_id),
            db_user_id=db_user_id,
            clerk_name=clerk_name
        )
    except Exception as e:
        print("⚠ Error in handle_user_utterance_text:", e)
        # fallback: return brief failure message
        return JSONResponse({"answer": "Sorry, I couldn't process that right now."}, status_code=500)

    return JSONResponse({"answer": reply})


# --------------------------------------------------------------------------
#                           Monitoring & feedback endpoints
# --------------------------------------------------------------------------

@app.get("/llm_feedback")
async def llm_feedback(payload: dict):
    request_id = payload.get("request_id")
    reward = payload.get("reward")
    db = SessionLocal()
    try:
        row = db.query(LLMInteraction).filter_by(request_id=request_id).first()
        if row:
            row.explicit_reward = reward
            db.commit()
    finally:
        db.close()
    return {"status": "ok"}


@app.get("/metrics/llm")
def llm_metrics():
    db = SessionLocal()
    try:
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
    finally:
        db.close()
    return {"interactions": data}


@app.get("/appointments/next")
def get_next_appointment(request: Request, db: Session = Depends(get_db)):
    token = request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Missing token")
    payload = verify_token(token)
    email = payload.get("email") or payload.get("email_address")
    if not email:
        raise HTTPException(status_code=401, detail="Email missing in token")
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
    return {
        "appointment": {
            "time": appt.datetime.isoformat(),
            "doctor_name": appt.doctor_name,
            "reason": appt.reason,
            "patient_name": appt.patient.name if appt.patient else "Unknown"
        }
    }


# --------------------------------------------------------------------------
#                         Startup initialization
# --------------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    init_db()
    print("✅ FlossyAI server started | Clerk OAuth & JWT ready.")
