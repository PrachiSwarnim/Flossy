import os
import re
import json
import uuid
import jwt
import requests
import logging
import numpy as np

from datetime import datetime, timezone, timedelta
from typing import Callable, Optional, Generator, List
import io
from fpdf import FPDF
from reminders import send_simulated_notification

from fastapi import FastAPI, Request, HTTPException, Depends, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from sqlalchemy.orm import Session, joinedload
from dotenv import load_dotenv
from jwt import PyJWKClient
from pydantic import BaseModel

class PrescriptionCreate(BaseModel):
    patient_name: str
    details: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    recommendations: Optional[str] = None

class InvoiceItemCreate(BaseModel):
    treatment_name: str
    treatment_date: Optional[str] = None # format "YYYY-MM-DD"
    cost: float

class PaymentRecordCreate(BaseModel):
    receipt_number: Optional[str] = None
    paid_on: Optional[str] = None # format "YYYY-MM-DD"
    payment_method: str
    amount: float

class InvoiceCreate(BaseModel):
    patient_name: str
    invoice_number: Optional[str] = None
    currency: Optional[str] = "INR"
    discount: float = 0.0
    items: List[InvoiceItemCreate]
    payments: List[PaymentRecordCreate]

class ManualPatientAppointmentCreate(BaseModel):
    name: str
    phone: str
    datetime: datetime
    reason: str
    prescription_details: Optional[str] = None

class ReceptionistPatientAdd(BaseModel):
    name: str
    phone: str
    age: int
    datetime: datetime
    reason: str
    doctor_name: Optional[str] = None

from livekit import api

# ----- local imports -----
from database import SessionLocal, Base, engine
from models import User, Patient, Appointment, Interaction, LLMInteraction, Prescription, Invoice, InvoiceItem, PaymentRecord, TreatmentCatalog
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

# CORSMiddleware will be added later to ensure it wraps ClerkAuthMiddleware

# ------------------------------------------------------------------
# Lazy holders (Kept for your Dashboard metrics/RL)
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
    try: yield db
    finally: db.close()

def get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None: _jwks_client = PyJWKClient(JWKS_URL)
    return _jwks_client

def verify_token(token: str) -> dict:
    jwks_client = get_jwks_client()
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    # Added leeway=60 to handle "token is not yet valid" errors due to clock drift
    return jwt.decode(
        token, 
        signing_key.key, 
        algorithms=["RS256"], 
        issuer=CLERK_ISSUER, 
        options={"verify_aud": False},
        leeway=60
    )

def load_faiss_index():
    global _faiss_index, _faiss_chunks
    if _faiss_index is None:
        try:
            import faiss
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

def get_genai_client():
    global _genai_client
    if _genai_client is None:
        try:
            from google.genai import Client
            _genai_client = Client(api_key=GEMINI_API_KEY)
            print("GenAI client initialized (lazy).")
        except Exception as e:
            print("GenAI client failed to initialize:", e)
            _genai_client = None
    return _genai_client


def get_bandit_and_meta():
    global _bandit, ACTIONS, PROMPT_VARIANTS, MODELS
    if _bandit is None:
        try:
            from rl_core import bandit as bandit_obj, ACTIONS as _A, PROMPT_VARIANTS as _P, MODELS as _M, LinUCB as LinUCBClass
            ACTIONS, PROMPT_VARIANTS, MODELS = _A, _P, _M
            _bandit = bandit_obj if bandit_obj is not None else LinUCBClass(
                bandit_name="doctor_global_v1",
                actions=list(range(len(_A))),
                d=768,
                alpha=1.0
            )
            print("RL bandit loaded lazily.")
        except Exception as e:
            print("Failed to lazy-load RL bandit:", e)
            try:
                from rl_core import ACTIONS as _A, PROMPT_VARIANTS as _P, MODELS as _M
                ACTIONS, PROMPT_VARIANTS, MODELS = _A, _P, _M
            except Exception:
                ACTIONS, PROMPT_VARIANTS, MODELS = [], [], []
            _bandit = None
    return _bandit, ACTIONS, PROMPT_VARIANTS, MODELS

# ------------------------------------------------------------------
# Middleware
# ------------------------------------------------------------------
EXEMPT_PATHS = {"/health", "/api/public", "/api/generate-token", "/static", "/docs", "/openapi.json", "/api/treatments"}

# ------------------------------------------------------------------
# LiveKit Token Generation
# ------------------------------------------------------------------
@app.post("/api/generate-token")
async def generate_token():
    room_name = f"room-{uuid.uuid4().hex[:8]}"
    participant_identity = f"user-{uuid.uuid4().hex[:6]}"

    token = api.AccessToken(
        api_key=os.getenv("LIVEKIT_API_KEY"),
        api_secret=os.getenv("LIVEKIT_API_SECRET"),
    ).with_identity(participant_identity) \
     .with_name(f"Patient-{participant_identity}") \
     .with_grants(
        api.VideoGrants(
            room_join=True,
            room=room_name,
        )
     )

    return {
        "token": token.to_jwt(),
        "roomName": room_name,
    }


class ClerkAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path
        if any(path.startswith(p) for p in EXEMPT_PATHS) or request.method == "OPTIONS":
            return await call_next(request)
        
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        
        try:
            token = auth.split(" ")[1]
            request.state.user = verify_token(token)
            return await call_next(request)
        except HTTPException as e:
            # Re-raise HTTPExceptions so FastAPI can handle them correctly
            raise e
        except Exception as e:
            # Log specific error to console and return it for debugging
            print(f"❌ Middleware error: {str(e)}")
            return JSONResponse({"detail": f"Server Error: {str(e)}"}, status_code=500)

app.add_middleware(ClerkAuthMiddleware)

# --- CORS MIDDLEWARE (MUST BE OUTERMOST) ---
FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGINS", "*")
allow_origins = ["*"] if FRONTEND_ORIGINS == "*" else [o.strip() for o in FRONTEND_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# LIVEKIT TOKEN ENDPOINT (The Bridge to your Agent)
# ------------------------------------------------------------------

@app.get("/api/token")
async def get_livekit_token(request: Request):
    """
    Generates a LiveKit token with user EMAIL in metadata.
    """
    # 1. Get Params
    identity = request.query_params.get("identity", f"user_{uuid.uuid4().hex[:6]}")
    name = request.query_params.get("name", "Guest")
    email = request.query_params.get("email", "")  # <--- Capture Email

    lk_api_key = os.getenv("LIVEKIT_API_KEY")
    lk_api_secret = os.getenv("LIVEKIT_API_SECRET")

    if not lk_api_key or not lk_api_secret:
        raise HTTPException(status_code=500, detail="LiveKit credentials not configured.")

    # 2. Create VideoGrant
    grant = api.VideoGrants(
        room_join=True,
        room="flossy-room",
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True,
    )

    # 3. Build Metadata JSON (Crucial for Agent)
    metadata_json = json.dumps({
        "email": email,
        "name": name
    })

    # 4. Create Token
    token = api.AccessToken(lk_api_key, lk_api_secret) \
        .with_identity(identity) \
        .with_name(name) \
        .with_grants(grant) \
        .with_metadata(metadata_json)  # <--- Attach Metadata

    return {"accessToken": token.to_jwt(), "url": os.getenv("LIVEKIT_URL")}    

# ------------------------------------------------------------------
# Core Dental Logic (Existing Endpoints)
# ------------------------------------------------------------------
@app.post("/api/contact_request")
def contact_request(payload: dict, db: Session = Depends(get_db)):
    name = payload.get("name", "Unknown")
    phone = payload.get("phone")
    reason = payload.get("reason", "")

    if not phone:
        raise HTTPException(status_code=400, detail="Phone number is required")

    # Check if patient exists
    patient = db.query(Patient).filter(Patient.phone == phone).first()
    
    if not patient:
        patient = Patient(
            name=name,
            phone=phone,
            user_id=None, # Guest
            contact_datetime=datetime.now(timezone.utc),
            source="website"
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
    
    # Record interaction
    interaction = Interaction(
        patient_id=patient.id,
        channel="contact_form",
        message=f"New Patient Inquiry: {reason}",
        created_at=datetime.now(timezone.utc)
    )
    db.add(interaction)
    db.commit()

    return {"success": True, "message": "Inquiry received"}
    
# ------------------------------------------------------------------
# Role requirement dependency
# ------------------------------------------------------------------
def require_role(expected_role):
    def _require_role(request: Request, db: Session = Depends(get_db)):
        payload = getattr(request.state, "user", None)
        if not payload:
            raise HTTPException(status_code=401, detail="Not authenticated")

        email = (payload.get("email") or payload.get("email_address") or "").lower()
        user = db.query(User).filter(User.email.ilike(email)).first()

        if not user:
            raise HTTPException(status_code=403, detail="User not found in local database")

        if expected_role != "any":
            if isinstance(expected_role, list):
                if user.role not in expected_role:
                    raise HTTPException(status_code=403, detail="Insufficient permissions")
            elif user.role != expected_role:
                raise HTTPException(status_code=403, detail="Insufficient permissions")

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
        from sqlalchemy import inspect, text
        Base.metadata.create_all(bind=engine)
        
        inspector = inspect(engine)
        
        with engine.connect() as conn:
            # 1. Check 'patients' table
            try:
                columns = [c['name'].lower() for c in inspector.get_columns('patients')]
                if columns:
                    if "age" not in columns:
                        conn.execute(text("ALTER TABLE patients ADD COLUMN age INTEGER;"))
                    if "source" not in columns:
                        conn.execute(text("ALTER TABLE patients ADD COLUMN source VARCHAR(50) DEFAULT 'website';"))
                    if "is_archived" not in columns:
                        conn.execute(text("ALTER TABLE patients ADD COLUMN is_archived INTEGER DEFAULT 0;"))
            except Exception as e: print(f"Migration error (patients): {e}")
            
            # 2. Check 'appointments' table
            try:
                columns = [c['name'].lower() for c in inspector.get_columns('appointments')]
                if columns:
                    if "reminder_level" not in columns:
                        conn.execute(text("ALTER TABLE appointments ADD COLUMN reminder_level INTEGER DEFAULT 0;"))
                    if "follow_up_reason" not in columns:
                        conn.execute(text("ALTER TABLE appointments ADD COLUMN follow_up_reason TEXT;"))
                    if "follow_up_status" not in columns:
                        conn.execute(text("ALTER TABLE appointments ADD COLUMN follow_up_status VARCHAR(50);"))
            except Exception as e: print(f"Migration error (appointments): {e}")
            
            # 3. Check 'prescriptions' table
            try:
                columns = [c['name'].lower() for c in inspector.get_columns('prescriptions')]
                if columns and "diagnosis" not in columns:
                    conn.execute(text("ALTER TABLE prescriptions ADD COLUMN diagnosis TEXT;"))
                    conn.execute(text("ALTER TABLE prescriptions ADD COLUMN treatment_plan TEXT;"))
                    conn.execute(text("ALTER TABLE prescriptions ADD COLUMN recommendations TEXT;"))
                    # SQLite doesn't support DROP NOT NULL well, but we can try or skip
                    try: conn.execute(text("ALTER TABLE prescriptions ALTER COLUMN details DROP NOT NULL;"))
                    except: pass 
            except Exception as e: print(f"Migration error (prescriptions): {e}")
            
            # 4. Check 'invoices' table
            try:
                columns = [c['name'].lower() for c in inspector.get_columns('invoices')]
                if columns and "currency" not in columns:
                    conn.execute(text("ALTER TABLE invoices ADD COLUMN currency VARCHAR(10) DEFAULT 'INR';"))
            except Exception as e: print(f"Migration error (invoices): {e}")

            # 5. Seed Treatment Catalog
            try:
                res_tc = conn.execute(text("SELECT count(*) FROM treatment_catalog")).fetchone()
                if res_tc and res_tc[0] == 0:
                    print("🌱 Seeding Treatment Catalog...")
                    treatments = [
                        ("Dental Scaling & Polishing", 1500, "Preventive"),
                        ("Root Canal Treatment (RCT)", 500, "Endodontic"),
                        ("Dental Filling (Composite)", 2500, "Restorative"),
                        ("Tooth Extraction (Simple)", 800, "Surgical"),
                        ("Dental Crown (PFM)", 5500, "Restorative"),
                        ("Dental Crown (Zirconia)", 12000, "Restorative"),
                        ("Teeth Whitening", 8000, "Cosmetic"),
                        ("Dental Implant", 35000, "Surgical"),
                        ("Deep Cleaning (Scaling \u0026 Root Planing)", 3000, "Preventive")
                    ]
                    for name, cost, cat in treatments:
                        conn.execute(text("INSERT INTO treatment_catalog (name, default_cost, category) VALUES (:n, :c, :cat)"), {"n": name, "c": cost, "cat": cat})
                else:
                    # Force update for specific requested prices
                    conn.execute(text("UPDATE treatment_catalog SET default_cost = 500 WHERE name = 'Root Canal Treatment (RCT)'"))
                    conn.execute(text("UPDATE treatment_catalog SET default_cost = 800 WHERE name = 'Tooth Extraction (Simple)'"))
            except Exception as e:
                print(f"Migration/Seed error (catalog): {e}")

            conn.commit()
            print("✅ DB Schema auto-migration check complete.")
            
    except Exception as e:
        print(f"⚠️ init_db migration error: {e}")
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
@app.get("/api/debug/fix_my_role")
def fix_my_role(db: Session = Depends(get_db)):
    # HARDCODED FIX FOR PRACHI
    target_email = "prachi.swarnim@gmail.com"
    user = db.query(User).filter(User.email == target_email).first()
    msg = "User not found"
    
    if user:
        user.role = "dentist"
        db.commit()
        msg = f"Role updated to dentist for {target_email}"
        
        # Access secret key safely inside function
        secret = os.getenv("CLERK_SECRET_KEY")
        if secret:
            try:
                # Need to find clerk ID? usually user.id is NOT clerk id.
                # Assuming I can search clerk by email
                headers = {"Authorization": f"Bearer {secret}"}
                res = requests.get(f"https://api.clerk.dev/v1/users?email_address={target_email}", headers=headers)
                if res.ok and res.json():
                    uid = res.json()[0]["id"]
                    requests.patch(f"https://api.clerk.dev/v1/users/{uid}", headers=headers, json={"public_metadata": {"role": "dentist"}})
                    msg += " + Clerk metadata updated"
            except Exception as e:
                msg += f" (Clerk update failed: {str(e)})"

    return {"status": "done", "message": msg}

# ------------------------------------------------------------------
# Auth endpoints (select_role / post_login)
# ------------------------------------------------------------------
@app.post("/api/auth/select_role")
def select_role(payload: dict, request: Request, db: Session = Depends(get_db)):
    role = payload.get("role")
    if role not in {"patient", "dentist", "receptionist"}:
        raise HTTPException(status_code=400, detail="Invalid role")

    user_payload = getattr(request.state, "user", None)
    if not user_payload:
        raise HTTPException(status_code=401, detail="Authentication required")

    email = (user_payload.get("email") or user_payload.get("email_address") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email missing in token")

    # --- Fetch or create user in DB ---
    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user:
        user = User(email=email, role=role, created_at=datetime.now(timezone.utc))
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.role = role
        db.commit()

    # --- AUTO-CREATE PATIENT PROFILE IF ROLE = PATIENT ---
    if role == "patient":
        patient = db.query(Patient).filter(Patient.user_id == user.id).first()
        if not patient:
            patient = Patient(
                name=email.split("@")[0],
                phone="0000000000",
                user_id=user.id,
                contact_datetime=datetime.now(timezone.utc),
                source="website"
            )
            db.add(patient)
            db.commit()

    # ---------------------------------------------------------
    # ⭐ NEW: Write role to Clerk public metadata
    # ---------------------------------------------------------
    try:
        headers = {"Authorization": f"Bearer {CLERK_SECRET_KEY}"}
        clerk_user_id = user_payload["sub"]

        requests.patch(
            f"https://api.clerk.dev/v1/users/{clerk_user_id}",
            headers=headers,
            json={"public_metadata": {"role": role}}
        )

        print(f"Clerk metadata updated → role={role}")
    except Exception as e:
        print("Failed to update Clerk metadata:", e)

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

class AppointmentUpdate(BaseModel):
    datetime: Optional[datetime] = None
    status: Optional[str] = None
    reason: Optional[str] = None

# ... inside Appointments endpoints section ...

@app.put("/api/appointments/{id}")
def update_appointment(id: int, appointment_update: AppointmentUpdate, db: Session = Depends(get_db)):
    # 1. Fetch the appointment
    db_appointment = db.query(Appointment).filter(Appointment.id == id).first()
    if not db_appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # 2. Update fields if provided
    if appointment_update.datetime:
        db_appointment.datetime = appointment_update.datetime
    if appointment_update.status:
        db_appointment.status = appointment_update.status
    
    # 3. THIS IS THE FIX: Explicitly update the reason
    if appointment_update.reason:
        db_appointment.reason = appointment_update.reason 

    # 4. Commit changes
    db.commit()
    db.refresh(db_appointment)
    
    return {"message": "Appointment updated successfully", "appointment": {
        "id": db_appointment.id,
        "reason": db_appointment.reason,
        "status": db_appointment.status,
        "time": db_appointment.datetime.isoformat()
    }}


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

    if user.role == "dentist" or user.role == "receptionist":
        # Dentists (and Receptionists) see ALL appointments
        appts = base_query.all()
    else:
        # Patients only see their own
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
def dentist_upcoming(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_role("dentist"))
):
    user_payload = getattr(request.state, "user", None)
    if not user_payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    email = (user_payload.get("email") or user_payload.get("email_address") or "").lower()
    user = db.query(User).filter(User.email.ilike(email)).first()

    if not user or (user.role != "dentist" and email != "prachi.swarnim@gmail.com"):
        return {"today": [], "upcoming": []}

    # Normalize dentist name
    email_prefix = email.split("@")[0]
    clean = email_prefix.replace(".", " ")
    proper = " ".join(p.capitalize() for p in clean.split())
    dentist_name = f"Dr. {proper}"

    # ✅ DEFINE DATES (IST Localized)
    ist = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist)
    today_start = datetime(now_ist.year, now_ist.month, now_ist.day, tzinfo=ist)
    today_end = today_start + timedelta(days=1)

    # DEBUG LOGGING (now safe)
    try:
        with open("backend_debug.log", "a") as f:
            f.write("--- DENTIST UPCOMING DEBUG ---\n")
            f.write(f"Email: {email}\n")
            f.write(f"Generated Name: {dentist_name}\n")
            f.write(f"Today Start (UTC): {today_start}\n")
            f.write(f"Today End (UTC): {today_end}\n")
    except Exception as e:
        print(f"Log error: {e}")

    # Fetch candidates
    from sqlalchemy import or_
    all_candidates_query = db.query(Appointment).join(Appointment.patient).options(joinedload(Appointment.patient))
    
    # 🔓 SHOW ALL: All dentists now see all appointments
    # if email != "prachi.swarnim@gmail.com":
    #     all_candidates_query = all_candidates_query.filter(
    #         or_(
    #             Appointment.doctor_name.ilike(dentist_name),
    #             Appointment.doctor_name == None
    #         )
    #     )
    
    # 🕵️‍♂️ HIDE ARCHIVED PATIENTS
    all_candidates_query = all_candidates_query.filter(Patient.is_archived == 0)

    all_candidates = (
        all_candidates_query
        .order_by(Appointment.datetime.asc())
        .all()
    )

    today_appts, upcoming_appts = [], []

    for a in all_candidates:
        is_today_strict = today_start <= a.datetime < today_end
        is_past_pending = a.datetime < today_start and a.status == "scheduled"

        if is_today_strict or is_past_pending:
            today_appts.append(a)
        elif a.datetime >= today_end:
            upcoming_appts.append(a)

    def fmt(a):
        return {
            "id": a.id,
            "time": a.datetime.isoformat(),
            "patient_name": a.patient.name if a.patient else "Unknown",
            "patient_phone": a.patient.phone if a.patient else None,
            "patient_age": a.patient.age if a.patient else None,
            "reason": a.reason,
            "status": a.status,
            "follow_up_reason": a.follow_up_reason,
            "follow_up_status": a.follow_up_status,
        }

    return {
        "today": [fmt(a) for a in today_appts],
        "upcoming": [fmt(a) for a in upcoming_appts],
    }

@app.get("/api/appointments/receptionist_upcoming")
def receptionist_upcoming(
    db: Session = Depends(get_db),
    user=Depends(require_role("any")) # Dentists can also see this to view general clinic load
):
    """
    Returns ALL clinic appointments (Today/Upcoming) for all doctors.
    """
    # ✅ DEFINE DATES (IST Localized)
    ist = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist)
    today_start = datetime(now_ist.year, now_ist.month, now_ist.day, tzinfo=ist)
    today_end = today_start + timedelta(days=1)

    all_candidates = (
        db.query(Appointment)
        .join(Appointment.patient)
        .options(joinedload(Appointment.patient))
        .filter(Patient.is_archived == 0)
        .order_by(Appointment.datetime.asc())
        .all()
    )

    today_appts, upcoming_appts = [], []

    for a in all_candidates:
        is_today_strict = today_start <= a.datetime < today_end
        is_past_pending = a.datetime < today_start and a.status == "scheduled"

        if is_today_strict or is_past_pending:
            today_appts.append(a)
        elif a.datetime >= today_end:
            upcoming_appts.append(a)

    def fmt(a):
        return {
            "id": a.id,
            "time": a.datetime.isoformat(),
            "patient_name": a.patient.name if a.patient else "Unknown",
            "patient_phone": a.patient.phone if a.patient else None,
            "patient_age": a.patient.age if a.patient else None,
            "reason": a.reason,
            "status": a.status,
            "doctor_name": a.doctor_name or "Not Assigned"
        }

    return {
        "today": [fmt(a) for a in today_appts],
        "upcoming": [fmt(a) for a in upcoming_appts],
    }

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
# Get All Patients (For Prescription Dropdown)
# ------------------------------------------------------------------
@app.get("/api/patients")
def get_all_patients(db: Session = Depends(get_db), user = Depends(require_role("any"))):
    """
    Returns all non-archived patients with optimized formatting and source info.
    """
    patients = db.query(Patient).filter(Patient.is_archived == 0).all()
    
    results = []
    for p in patients:
        display_name = p.name.strip().title() if p.name else "Unknown Patient"
        results.append({
            "id": p.id,
            "name": display_name,
            "phone": p.phone,
            "age": p.age,
            "email": p.user.email if p.user else None,
            "source": p.source or "website"
        })
    
    results.sort(key=lambda x: x["name"])
    return results

class PatientUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None

@app.patch("/api/patients/{id}")
def update_patient(id: int, data: PatientUpdate, db: Session = Depends(get_db), user = Depends(require_role("receptionist"))):
    patient = db.query(Patient).filter(Patient.id == id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    if data.name:
        patient.name = data.name
    if data.phone:
        patient.phone = data.phone
    if data.age is not None:
        patient.age = data.age
        
    db.commit()
    return {"success": True}

@app.post("/api/patients/{id}/archive")
def archive_patient(id: int, db: Session = Depends(get_db), user = Depends(require_role("receptionist"))):
    patient = db.query(Patient).filter(Patient.id == id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    patient.is_archived = 1
    db.commit()
    return {"success": True}
    
    results.sort(key=lambda x: x["name"])
    return results

@app.post("/api/prescriptions")
def create_prescription(data: PrescriptionCreate, db: Session = Depends(get_db), user = Depends(require_role("dentist"))):
    # 1. Search for Patient record first (since all patients are now in the Patient table)
    # Match by name (strip and title case to match get_all_patients)
    search_name = data.patient_name.strip().title()
    patient = db.query(Patient).filter(Patient.name.ilike(search_name)).first()

    if not patient:
        # Fallback: Search in Users table for legacy or derived names
        target_user = None
        all_users = db.query(User).filter(User.role.ilike("patient")).all()
        
        for u in all_users:
            # Check linked patient name first
            p = db.query(Patient).filter(Patient.user_id == u.id).first()
            if p and p.name and p.name.strip().title() == search_name:
                patient = p
                break
            
            # Fallback: Derived name
            prefix = (u.email or "").split("@")[0]
            prefix_no_digits = re.sub(r'\d+', '', prefix)
            derived_name = prefix_no_digits.replace(".", " ").replace("_", " ").replace("-", " ").strip().title()
            
            if derived_name == search_name:
                target_user = u
                break
        
        if not patient and not target_user:
            raise HTTPException(status_code=404, detail="User not found for this patient name.")

        if not patient and target_user:
            # Create a Patient profile for this User
            patient = Patient(
                name=data.patient_name,
                phone=f"auto-{target_user.id}",
                user_id=target_user.id
            )
            db.add(patient)
            db.commit()
            db.refresh(patient)

    # 3. Create the prescription with structured fields
    new_presc = Prescription(
        patient_id=patient.id,
        doctor_id=user.id,
        details=data.details,
        diagnosis=data.diagnosis,
        treatment_plan=data.treatment_plan,
        recommendations=data.recommendations
    )
    db.add(new_presc)
    db.commit()
    db.refresh(new_presc)
    return {"success": True, "prescription_id": new_presc.id}

@app.get("/api/prescriptions/my")
def get_my_prescriptions(db: Session = Depends(get_db), user = Depends(require_role("patient"))):
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        return {"prescriptions": []}
    
    prescs = db.query(Prescription).filter(Prescription.patient_id == patient.id).order_by(Prescription.created_at.desc()).all()
    return {
        "prescriptions": [
            {
                "id": p.id,
                "doctor": p.doctor.email.split("@")[0].title() if p.doctor else "Dentist",
                "details": p.details,
                "diagnosis": p.diagnosis,
                "treatment_plan": p.treatment_plan,
                "recommendations": p.recommendations,
                "date": p.created_at.isoformat()
            }
            for p in prescs
        ]
    }

@app.get("/api/prescriptions/dentist")
def get_dentist_prescriptions(db: Session = Depends(get_db), user = Depends(require_role("dentist"))):
    prescs = db.query(Prescription).filter(Prescription.doctor_id == user.id).order_by(Prescription.created_at.desc()).all()
    return {
        "prescriptions": [
            {
                "id": p.id,
                "patient": p.patient.name,
                "details": p.details,
                "diagnosis": p.diagnosis,
                "treatment_plan": p.treatment_plan,
                "recommendations": p.recommendations,
                "date": p.created_at.isoformat()
            }
            for p in prescs
        ]
    }

@app.get("/api/prescriptions/{id}/pdf")
def download_prescription_pdf(id: int, db: Session = Depends(get_db)):
    presc = db.query(Prescription).filter(Prescription.id == id).first()
    if not presc:
        raise HTTPException(status_code=404, detail="Prescription not found")

    import re
    
    # 1. Clean Names for PDF
    p_name = presc.patient.name if presc.patient else "Valued Patient"
    if p_name.startswith("auto-") or p_name.lower() == "undefined":
        if presc.patient and presc.patient.user:
            prefix = presc.patient.user.email.split("@")[0]
            p_name = re.sub(r'\d+', '', prefix).replace(".", " ").replace("_", " ").replace("-", " ").strip().title()
    else:
        p_name = p_name.title()

    doc_raw = "Dentist"
    if presc.doctor:
        doc_raw = presc.doctor.email.split("@")[0]
        d_profile = db.query(Patient).filter(Patient.user_id == presc.doctor.id).first()
        if d_profile and d_profile.name and not d_profile.name.startswith("auto-"):
            doc_raw = d_profile.name
            
    doc_name = re.sub(r'\d+', '', doc_raw).replace(".", " ").replace("_", " ").replace("-", " ").strip().title()
    if not doc_name.startswith("Dr."):
        doc_name = f"Dr. {doc_name}"

    # 2. Generate PDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Background/Margin Decoration
    pdf.set_draw_color(212, 175, 55) # Gold
    pdf.set_line_width(0.5)
    pdf.rect(5, 5, 200, 287) # Subtle border
    
    # Header: Logo & Clinic Info
    logo_path = r"c:\Users\Prachi Swarnim\Desktop\Flossy\flossy-ui\public\static\assets\logo.png"
    try:
        pdf.image(logo_path, 10, 10, 30)
    except:
        pass
        
    pdf.set_xy(45, 12)
    pdf.set_font("Arial", "B", 18)
    pdf.set_text_color(212, 175, 55) # Unified Gold
    pdf.cell(0, 10, "SMILE ARTISTS DENTAL STUDIO", ln=True)
    
    pdf.set_x(45)
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, "Bangalore, India | Ph: +91 98765 43210", ln=True)
    pdf.set_x(45)
    pdf.cell(0, 5, "Email: hello@smileartists.in | Web: www.smileartists.in", ln=True)
    
    pdf.ln(15)
    
    pdf.set_font("Arial", "B", 14)
    pdf.set_fill_color(244, 244, 244)
    pdf.set_text_color(26, 26, 26)
    pdf.cell(190, 10, " MEDICAL PRESCRIPTION ", ln=True, align="C", fill=True)
    pdf.ln(5)
    
    # Info Section
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 8, "Patient Name:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(70, 8, p_name)
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 8, "Prescription ID:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, f"#{presc.id}", ln=True)
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 8, "Date:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(70, 8, presc.created_at.strftime("%d %b, %Y"))
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 8, "Dentist:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, doc_name, ln=True)
    
    pdf.ln(5)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)
    
    def add_section(title, content):
        if not content: return
        pdf.set_font("Arial", "B", 11)
        pdf.set_text_color(212, 175, 55) # Gold
        pdf.cell(0, 8, title.upper(), ln=True)
        pdf.ln(1)
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(40, 40, 40)
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line: continue
            clean_line = re.sub(r'^[•\-\*]\s*', '', line)
            try: clean_line.encode('latin-1')
            except UnicodeEncodeError: clean_line = clean_line.encode('ascii', 'ignore').decode('ascii')
            if not clean_line: continue
            pdf.set_x(15)
            pdf.cell(5, 6, "\xb7", ln=0)
            pdf.multi_cell(0, 6, clean_line)
        pdf.ln(4)

    if presc.diagnosis:
        add_section("Diagnosis", presc.diagnosis)
    if presc.treatment_plan:
        add_section("Treatment Plan", presc.treatment_plan)
    if presc.recommendations:
        add_section("Recommendations", presc.recommendations)

    if presc.details and not (presc.diagnosis or presc.treatment_plan or presc.recommendations):
        pdf.set_font("Arial", "B", 11)
        pdf.set_text_color(212, 175, 55)
        pdf.cell(0, 8, "ADVICE & NOTES:", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(0, 6, presc.details)
    
    # Authorized Signatory
    if pdf.get_y() > 240: pdf.add_page() # Check for space
    pdf.set_y(-50)
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 10, "Authorized Signatory", ln=True, align="R")
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 5, doc_name, ln=True, align="R")
    
    # Footer
    pdf.set_y(-20)
    pdf.set_draw_color(212, 175, 55)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, "Smile Artists Dental Studio - Dedicated to your perfect smile.", align="C")

    pdf_bytes = bytes(pdf.output())
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=prescription_{id}.pdf"}
    )

@app.get("/api/appointments/patient_upcoming")
def patient_upcoming(request: Request,
                     db: Session = Depends(get_db),
                     user = Depends(require_role("patient"))):

    user_payload = getattr(request.state, "user", None)
    if not user_payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    email = (user_payload.get("email") or user_payload.get("email_address") or "").lower()
    user = db.query(User).filter(User.email.ilike(email)).first()

    if not user or user.role != "patient":
        return {"today": [], "upcoming": []}

    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        return {"today": [], "upcoming": []}

    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    today_end = today_start + timedelta(days=1)

    today_appts = (
        db.query(Appointment)
        .options(joinedload(Appointment.doctor))
        .filter(Appointment.patient_id == patient.id,
                Appointment.datetime >= today_start,
                Appointment.datetime < today_end)
        .order_by(Appointment.datetime.asc())
        .all()
    )

    upcoming_appts = (
        db.query(Appointment)
        .options(joinedload(Appointment.doctor))
        .filter(Appointment.patient_id == patient.id,
                Appointment.datetime >= today_end)
        .order_by(Appointment.datetime.asc())
        .all()
    )

    history_appts = (
        db.query(Appointment)
        .options(joinedload(Appointment.doctor))
        .filter(Appointment.patient_id == patient.id,
                Appointment.datetime < today_start)
        .order_by(Appointment.datetime.desc())
        .all()
    )

    def fmt(a):
        # Resolve doctor name: 1. doctor_name str (legacy/UI) 2. a.doctor user (relation) 3. default
        d_name = a.doctor_name
        if not d_name and a.doctor:
             # If linked to a User, try to generate name or use email
             d_name = "Dr. " + (a.doctor.email.split("@")[0].title() if a.doctor.email else "Dentist")
        
        return {
            "id": a.id,
            "time": a.datetime.isoformat(),
            "doctor_name": d_name or "Dr. Available",
            "reason": a.reason,
            "status": a.status,
            "follow_up_reason": a.follow_up_reason,
            "follow_up_status": a.follow_up_status,
        }

    return {
        "today": [fmt(a) for a in today_appts],
        "upcoming": [fmt(a) for a in upcoming_appts],
        "history": [fmt(a) for a in history_appts]
    }

@app.post("/api/auth/check_email")
def check_email(payload: dict, db: Session = Depends(get_db)):
    email = payload.get("email", "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    exists = db.query(User).filter(User.email.ilike(email)).first() is not None
    return {"exists": exists}

@app.post("/api/appointments/mark_completed/{appt_id}")
def mark_completed(appt_id: int, payload: dict = Body(default={}), db: Session = Depends(get_db), user = Depends(require_role(["dentist", "receptionist"]))):
    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    follow_up = payload.get("follow_up_reason")
    if follow_up:
        appt.status = "follow_up"
        appt.follow_up_reason = follow_up
    else:
        appt.status = "completed"
    
    db.commit()
    return {"success": True}

@app.post("/api/dentist/add_patient_appointment")
def add_patient_appointment(data: ManualPatientAppointmentCreate, db: Session = Depends(get_db), user = Depends(require_role("dentist"))):
    # 1. Check/Create Patient
    patient = db.query(Patient).filter(Patient.phone == data.phone).first()
    if not patient:
        patient = Patient(
            name=data.name,
            phone=data.phone,
            contact_datetime=datetime.now(timezone.utc),
            source="manual"
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
    
    # normalize dentist name
    email_prefix = user.email.split("@")[0]
    clean = email_prefix.replace(".", " ")
    proper = " ".join(p.capitalize() for p in clean.split())
    dentist_name = f"Dr. {proper}"

    # 2. Create Appointment
    new_appt = Appointment(
        patient_id=patient.id,
        doctor_id=user.id,
        doctor_name=dentist_name,
        datetime=data.datetime,
        reason=data.reason,
        status="scheduled"
    )
    db.add(new_appt)
    db.commit()
    db.refresh(new_appt)

    # 3. Create Prescription if details provided
    if data.prescription_details:
        new_presc = Prescription(
            patient_id=patient.id,
            doctor_id=user.id,
            details=data.prescription_details,
            created_at=datetime.now(timezone.utc)
        )
        db.add(new_presc)
        db.add(new_presc)
        db.commit()

    # --- TRIGGER BOOKING CONFIRMATION SMS ---
    try:
        from reminders import send_simulated_notification
        send_simulated_notification(db, new_appt, level=0)
    except Exception as e:
        print(f"⚠️ Failed to send booking confirmation: {e}")

    return {"success": True, "appointment_id": new_appt.id}

@app.post("/api/appointments/{appt_id}/follow_up_status")
def update_follow_up_status(appt_id: int, payload: dict = Body(...), db: Session = Depends(get_db), user = Depends(require_role(["dentist", "receptionist"]))):
    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    status = payload.get("status")
    if status not in ["completed", "missed", "rescheduled"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    appt.follow_up_status = status
    db.commit()
    return {"success": True}

@app.post("/api/receptionist/add_patient")
def add_receptionist_patient(data: ReceptionistPatientAdd, db: Session = Depends(get_db), user = Depends(require_role("receptionist"))):
    # 1. Check/Create Patient
    patient = db.query(Patient).filter(Patient.phone == data.phone).first()
    if not patient:
        patient = Patient(
            name=data.name,
            phone=data.phone,
            age=data.age,
            contact_datetime=datetime.now(timezone.utc),
            source="manual"
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
    else:
        # Update age if changed
        patient.age = data.age
        db.commit()
    
    # 2. Assign a default doctor or let dentist pick (here we assign it to the first dentist found as a placeholder or nil)
    # Actually, the user says "go to dentist dashboard", usually dentist dashboard filters by doctor_name.
    # For now, let's leave doctor_id null if not specified, but the dentist dashboard currently filters by doctor_name based on email.
    
    # Let's create an appointment that any doctor can see OR assign a generic name?
    # Better: If a dentist exists, maybe assign it? 
    # USER said "go to dentist dashboard".
    
    new_appt = Appointment(
        patient_id=patient.id,
        datetime=data.datetime,
        reason=data.reason,
        status="scheduled",
        doctor_name=data.doctor_name
    )
    db.add(new_appt)
    db.commit()
    db.refresh(new_appt)

    # --- TRIGGER BOOKING CONFIRMATION SMS ---
    try:
        from reminders import send_simulated_notification
        send_simulated_notification(db, new_appt, level=0)
    except Exception as e:
        print(f"⚠️ Failed to send booking confirmation: {e}")
        
    return {"success": True, "appointment_id": new_appt.id}

@app.get("/api/appointments/next")
def get_next_appointment(request: Request, db: Session = Depends(get_db), user = Depends(require_role("patient"))):
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
@app.post("/doctor_ai/query")
async def doctor_ai(request: Request):
    payload = await request.json()
    query = payload.get("query", "").strip()
    if not query:
        return JSONResponse({"answer": "No query provided."}, status_code=400)

    doctor_name = payload.get("doctor_name", "Doctor")

    # --- Load FAISS index ---
    try:
        index, chunks = load_faiss_index()
    except FileNotFoundError:
        return JSONResponse({"answer": "Knowledge base not available on the server."}, status_code=500)
    except Exception as e:
        return JSONResponse({"answer": f"Error loading KB: {e}"}, status_code=500)

    # --- GenAI lazy ---
    genai_client = get_genai_client()

    # --- RL bandit lazy ---
    bandit, ACTIONS, PROMPT_VARIANTS, MODELS = get_bandit_and_meta()

    # --- Embedding ---
    try:
        query_emb = np.array(embed_with_client(genai_client, query), dtype=float)
    except Exception:
        query_emb = np.zeros(768, dtype=float)

    x_context = query_emb
    if bandit:
        if x_context.shape[0] != bandit.d:
            if x_context.shape[0] > bandit.d:
                x_context = x_context[:bandit.d]
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

    prompt = chosen_prompt_template.format(
        doctor=doctor_name,
        context=context,
        query=query
    )

    try:
        answer = ai_generate(prompt, temperature=temp, model=chosen_model, client_override=genai_client)
    except Exception as e:
        print("ai_generate failed:", e)
        answer = "FlossyAI couldn't generate an answer right now."

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

    # Optional: persist logs (only if DB configured)
    try:
        db = SessionLocal()
        interaction = LLMInteraction(
            request_id=request_id,
            doctor_id=doctor_name,
            query=query,
            response=answer,
            context_used=context,
            semantic_similarity=semantic_similarity,
            groundedness=groundedness,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(interaction)
        db.commit()
        db.close()
    except Exception as e:
        print("DB logging failed:", e)

    return {
        "answer": answer,
        "request_id": request_id,
        "semantic_similarity": semantic_similarity,
        "groundedness": groundedness
    }

@app.post("/api/ai_response")
async def ai_response(request: Request, user=Depends(require_role("patient"))):
    payload = await request.json()
    user_msg = payload.get("query", "").strip()
    if not user_msg:
        return {"answer": "I didn't receive any message. Could you please repeat that?"}

    db = SessionLocal()
    db_user_id = None
    clerk_name = "Patient"

    # ----------------------------------
    # AUTH (best-effort enrichment only)
    # ----------------------------------
    try:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            decoded = verify_token(token)

            email = decoded.get("email") or decoded.get("email_address")
            clerk_user_id = decoded.get("sub")

            # Fetch Clerk profile
            if clerk_user_id:
                try:
                    headers = {"Authorization": f"Bearer {CLERK_SECRET_KEY}"}
                    resp = requests.get(
                        f"https://api.clerk.dev/v1/users/{clerk_user_id}",
                        headers=headers,
                        timeout=6,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        full = data.get("full_name")
                        first = data.get("first_name") or ""
                        last = data.get("last_name") or ""
                        clerk_name = full or f"{first} {last}".strip() or clerk_name
                except Exception:
                    pass

            if email:
                db_user = db.query(User).filter(User.email.ilike(email)).first()
                if db_user:
                    db_user_id = db_user.id
                    try:
                        from utils import get_or_create_patient
                        get_or_create_patient(db, db_user, clerk_name=clerk_name)
                    except Exception:
                        pass
    except Exception:
        pass

    # ----------------------------------
    # SAFE HANDLER RESOLUTION
    # ----------------------------------
    handler = globals().get("_handle_user_utterance_text")

    if not handler or not callable(handler):
        db.close()
        return {"answer": "FlossyAI assistant not available."}

    # ----------------------------------
    # OPTIONAL BACKGROUND STORAGE (NON-BLOCKING)
    # ----------------------------------
    try:
        import asyncio
        asyncio.create_task(
            handler(
                query=user_msg,
                user=str(db_user_id),
                db_user_id=db_user_id,
                clerk_name=clerk_name,
            )
        )
    except Exception:
        pass

    # ----------------------------------
    # MAIN RESPONSE (SINGLE SOURCE OF TRUTH)
    # ----------------------------------
    try:
        reply = await handler(
            user_msg,
            user=str(db_user_id),
            db_user_id=db_user_id,
            clerk_name=clerk_name,
        )
    except Exception as e:
        print("Error in handle_user_utterance_text:", e)
        reply = "Sorry, I couldn't process that right now."
    finally:
        db.close()

    return {"answer": reply}
# -------------------------
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
        "accuracy_score": r.accuracy_score,
        "timestamp": r.timestamp
    } for r in rows]
    return {"interactions": data}

@app.get("/api/auth/email_exists")
def email_exists(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email.ilike(email)).first()
    return {"exists": user is not None}


# ------------------------------------------------------------------
# Auto-Cleanup: Mark missed appointments
# ------------------------------------------------------------------
def mark_missed_appointments():
    """
    Checks for appointments that are still 'scheduled' but are older than 48 hours.
    Marks them as 'not attended'.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=48)
        
        # Find candidates
        missed = db.query(Appointment).filter(
            Appointment.status == "scheduled",
            Appointment.datetime < cutoff
        ).all()
        
        if missed:
            print(f"🧹 Auto-Cleanup: Found {len(missed)} missed appointments. Marking as 'not attended'.")
            for appt in missed:
                appt.status = "not attended"
            db.commit()
        else:
            print("✅ Auto-Cleanup: No missed appointments found.")
            
    except Exception as e:
        print(f"❌ Auto-Cleanup Error: {e}")
        db.rollback()
    finally:
        db.close()

# ------------------------------------------------------------------
# ------------------------------------------------------------------
# 💰 Invoicing Endpoints
# ------------------------------------------------------------------

@app.post("/api/invoices")
def create_invoice(data: InvoiceCreate, 
                   db: Session = Depends(get_db), 
                   user = Depends(require_role("any"))):
    """
    Creates an itemized invoice. Accessible by both dentist and receptionist.
    """
    # 1. Find patient
    patient = db.query(Patient).filter(Patient.name.ilike(data.patient_name)).first()
    if not patient:
        # Fallback: check User table
        u_p = db.query(User).filter(User.name.ilike(data.patient_name)).first()
        if u_p:
            patient = db.query(Patient).filter(Patient.user_id == u_p.id).first()
            
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{data.patient_name}' not found.")

    # 2. Generate invoice number if not provided
    inv_num = data.invoice_number or f"INV-{uuid.uuid4().hex[:8].upper()}"

    # 3. Create main Invoice record
    invoice = Invoice(
        invoice_number=inv_num,
        patient_id=patient.id,
        doctor_id=user.id if user.role == "dentist" else None,
        discount=data.discount,
        currency=data.currency or "INR",
        status="paid"
    )
    db.add(invoice)
    db.flush() 

    # 4. Add items
    gross_amount = 0.0
    for itm in data.items:
        t_date = datetime.now(timezone.utc)
        if itm.treatment_date:
            try: t_date = datetime.strptime(itm.treatment_date, "%Y-%m-%d")
            except: pass
        
        db.add(InvoiceItem(
            invoice_id=invoice.id,
            treatment_name=itm.treatment_name,
            treatment_date=t_date,
            cost=itm.cost
        ))
        gross_amount += itm.cost

    invoice.total_amount = gross_amount - data.discount

    # 5. Add payments
    total_paid = 0.0
    for pay in data.payments:
        p_date = datetime.now(timezone.utc)
        if pay.paid_on:
            try: p_date = datetime.strptime(pay.paid_on, "%Y-%m-%d")
            except: pass
        
        rec_num = pay.receipt_number or f"REC-{uuid.uuid4().hex[:8].upper()}"
        db.add(PaymentRecord(
            invoice_id=invoice.id,
            receipt_number=rec_num,
            paid_on=p_date,
            payment_method=pay.payment_method,
            amount=pay.amount
        ))
        total_paid += pay.amount

    # Update status based on payment
    if total_paid >= invoice.total_amount:
        invoice.status = "paid"
    elif total_paid > 0:
        invoice.status = "partially_paid"
    else:
        invoice.status = "unpaid"

    db.commit()
    db.refresh(invoice)
    return {"success": True, "invoice_id": invoice.id, "invoice_number": invoice.invoice_number}

@app.get("/api/invoices/history")
def get_invoice_history(db: Session = Depends(get_db), 
                        user = Depends(require_role("any"))):
    """
    Returns invoice history. Receptionists see all, dentists see their own.
    """
    query = db.query(Invoice).order_by(Invoice.date.desc())
    if user.role == "dentist":
        query = query.filter(Invoice.doctor_id == user.id)
    
    invs = query.all()
    results = []
    for i in invs:
        results.append({
            "id": i.id,
            "invoice_number": i.invoice_number,
            "patient_name": i.patient.name,
            "date": i.date.isoformat(),
            "total": i.total_amount,
            "status": i.status
        })
    return {"invoices": results}

@app.get("/api/invoices/{id}/pdf")
def download_invoice_pdf(id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Background Decoration
    pdf.set_draw_color(212, 175, 55) # Gold
    pdf.set_line_width(0.5)
    pdf.rect(5, 5, 200, 287) 

    # --- HEADER ---
    logo_path = r"c:\Users\Prachi Swarnim\Desktop\Flossy\flossy-ui\public\static\assets\logo.png"
    try:
        pdf.image(logo_path, 10, 10, 30)
    except:
        pass
        
    pdf.set_xy(45, 12)
    pdf.set_font("Arial", "B", 18)
    pdf.set_text_color(212, 175, 55) # Gold
    pdf.cell(0, 10, "SMILE ARTISTS DENTAL STUDIO", ln=True)
    
    pdf.set_font("Arial", "I", 10)
    pdf.set_x(45)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, "...crafting smiles | ISO 9001:2015 Certified", ln=True)
    pdf.set_x(45)
    pdf.cell(0, 5, "Official Digital Invoice", ln=True)
    
    pdf.ln(12)
    
    # Document Title
    pdf.set_font("Arial", "B", 14)
    pdf.set_fill_color(244, 244, 244)
    pdf.set_text_color(26, 26, 26)
    pdf.cell(190, 10, " TAX INVOICE ", ln=True, align="C", fill=True)
    pdf.ln(5)
    
    # Patient Info Row
    p_name = invoice.patient.name.upper()
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 8, "Patient:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(70, 8, p_name)
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 8, "Invoice #:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, invoice.invoice_number, ln=True)
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 8, "Age/Sex:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(70, 8, f"{invoice.patient.age or 'N/A'}")
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 8, "Date:")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, invoice.date.strftime("%d %b, %Y"), ln=True)
    
    pdf.ln(8)

    # Treatment Table
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(212, 175, 55)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(15, 10, "S.No", border=1, align="C", fill=True)
    pdf.cell(100, 10, " Treatment Description", border=1, fill=True)
    pdf.cell(35, 10, " Date", border=1, align="C", fill=True)
    pdf.cell(0, 10, f" Amount ({invoice.currency})", border=1, align="C", fill=True, ln=True)
    
    pdf.set_text_color(26, 26, 26)
    pdf.set_font("Arial", "", 10)
    gross_amount = 0
    for idx, item in enumerate(invoice.items, 1):
        pdf.cell(15, 8, str(idx), border=1, align="C")
        pdf.cell(100, 8, f" {item.treatment_name}", border=1)
        pdf.cell(35, 8, item.treatment_date.strftime("%b %d, %Y"), border=1, align="C")
        pdf.cell(0, 8, f"{item.cost:,.2f}", border=1, align="R", ln=True)
        gross_amount += item.cost
        
    pdf.set_font("Arial", "B", 10)
    pdf.cell(150, 8, "Gross Amount", border=1, align="R")
    pdf.cell(0, 8, f"{gross_amount:,.2f}", border=1, align="R", ln=True)
    pdf.cell(150, 8, "Discount", border=1, align="R")
    pdf.cell(0, 8, f"({invoice.discount:,.2f})", border=1, align="R", ln=True)
    
    pdf.set_fill_color(245, 245, 245)
    pdf.cell(150, 10, "TOTAL PAYABLE", border=1, align="R", fill=True)
    pdf.cell(0, 10, f"{invoice.currency} {invoice.total_amount:,.2f}", border=1, align="R", fill=True, ln=True)
    
    pdf.ln(10)

    # Payment Table
    pdf.set_font("Arial", "B", 10)
    pdf.cell(130, 8, "Payment History", ln=True)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(15, 8, "S.No", border=1, align="C")
    pdf.cell(60, 8, " Receipt #", border=1)
    pdf.cell(35, 8, " Paid On", border=1, align="C")
    pdf.cell(40, 8, " Method", border=1, align="C")
    pdf.cell(0, 8, " Amount", border=1, align="C", ln=True)
    
    pdf.set_font("Arial", "", 9)
    total_paid = 0
    for idx, pay in enumerate(invoice.payment_records, 1):
        pdf.cell(15, 7, str(idx), border=1, align="C")
        pdf.cell(60, 7, f" {pay.receipt_number}", border=1)
        pdf.cell(35, 7, pay.paid_on.strftime("%b %d, %Y"), border=1, align="C")
        pdf.cell(40, 7, pay.payment_method, border=1, align="C")
        pdf.cell(0, 7, f"{pay.amount:,.2f}", border=1, align="R", ln=True)
        total_paid += pay.amount
        
    pdf.set_font("Arial", "B", 9)
    pdf.cell(150, 8, "Total Amount Paid", border=1, align="R")
    pdf.cell(0, 8, f"{total_paid:,.2f}", border=1, align="R", ln=True)

    # Final Summary
    due = invoice.total_amount - total_paid
    pdf.ln(10)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(130, 10, "BALANCE DUE (NET):", border="B")
    pdf.set_text_color(200, 0, 0) if due > 0 else pdf.set_text_color(0, 150, 0)
    pdf.cell(0, 10, f"{invoice.currency} {max(0, due):,.2f}", border="B", align="R", ln=True)

    # Signature/Footer
    if pdf.get_y() > 240: pdf.add_page()
    pdf.set_y(-25)
    pdf.set_draw_color(212, 175, 55)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, "Smile Artists Dental Studio - Computer Generated Electronic Invoice", align="C")

    pdf_bytes = bytes(pdf.output())
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=invoice_{invoice.invoice_number}.pdf"}
    )

# Startup event: lightweight init only
# ------------------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    # Only run the lightweight DB init at startup. Heavy imports are lazy.
    init_db()
    mark_missed_appointments()    
    # Start Reminder Daemon
    try:
        from reminders import reminder_daemon
        import asyncio
        asyncio.create_task(reminder_daemon())
        print("✅ Reminder Daemon scheduled.")
    except Exception as e:
        print(f"⚠️ Could not start Reminder Daemon: {e}")

    print("✅ FlossyAI API server started | Clerk JWT ready (lazy heavy loads).")

# ------------------------------------------------------------------
# If you want a tiny root page for sanity checks
# ------------------------------------------------------------------
@app.get("/api/treatments")
def get_treatment_catalog(db: Session = Depends(get_db)):
    """Fetches the list of standard dental treatments and their default costs."""
    catalog = db.query(TreatmentCatalog).all()
    return {
        "treatments": [
            {"id": t.id, "name": t.name, "cost": t.default_cost, "category": t.category} 
            for t in catalog
        ]
    }

@app.get("/")
def root():
    return {"service": "FlossyAI API", "status": "running"}

# ------------------------------------------------------------------
# NEW: Get All Doctors (for Dropdown)
# ------------------------------------------------------------------
@app.get("/api/doctors")
def get_doctors(db: Session = Depends(get_db)):
    from sqlalchemy import or_
    # 1. Get all users with role 'dentist' OR specific admin email (case-insensitive)
    dentists = db.query(User).filter(
        or_(
            User.role == "dentist",
            User.email.ilike("prachi.swarnim@gmail.com")
        )
    ).all()
    
    doctor_names = []
    for d in dentists:
        # Normalize name from email
        email_prefix = d.email.split("@")[0]
        clean = email_prefix.replace(".", " ")
        proper = " ".join(p.capitalize() for p in clean.split())
        doctor_names.append(f"Dr. {proper}")
        
    return {"doctors": sorted(list(set(doctor_names)))} # Unique & Sorted

# End of file
