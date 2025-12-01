import os
import jwt
import requests
import json
import numpy as np
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from routers.sms import router as sms_router
from agent_server import app as agent_app
from database import init_db, SessionLocal
from models import User, Patient, Appointment, Interaction
from dotenv import load_dotenv
from sqlalchemy.orm import Session, joinedload
from jwt import PyJWKClient
from agent_server import handle_user_utterance_text
import faiss
from google.genai import Client

# --------------------------------------------------------------------------
#                         ENV + CLERK SETUP
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
genai_client = Client(api_key=GEMINI_API_KEY)

if not all([CLERK_SECRET_KEY, CLERK_CLIENT_ID, CLERK_CLIENT_SECRET]):
    raise RuntimeError("❌ Missing Clerk credentials in .env file")

# 🔑 HARDCODED LIST OF AUTHORIZED DENTIST EMAILS
AUTHORIZED_DENTIST_EMAILS = [
    "dr.shagufta@smileartists.com",
    "dr.shruti@smileartists.com",
    "dr.aishwarya@smileartists.com",
    "test_dentist@flossy.ai"
]

# --------------------------------------------------------------------------
#                            FASTAPI SETUP
# --------------------------------------------------------------------------

app = FastAPI(title="FlossyAI", description="AI Dental Assistant Platform")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Mount Static Files and Sub-Apps ---
# Use absolute path so FileResponse and load_html work independently of cwd
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "flossy_web")
app.mount("/agent", agent_app)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# --------------------------------------------------------------------------
#                             HELPER FUNCTIONS
# --------------------------------------------------------------------------
def load_html(filename: str):
    try:
        file_path = os.path.join("flossy_web", filename)
        with open(file_path, "r", encoding="utf-8") as f:
            html = f.read()
        return HTMLResponse(content=html, status_code=200)
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error loading {filename}</h1><p>{e}</p>", status_code=500)


def get_db():
    """Provide a new SQLAlchemy session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_or_create_patient(db: Session, user: User, clerk_name: str = None, phone: str = None):
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()

    if patient:
        return patient

    # Create new patient with full name from Clerk
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
    """Verify Clerk JWT and return the full payload. Accept small clock skew."""
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
        print("✅ Token verified successfully:", {k: payload.get(k) for k in ("sub","email","email_address")})
        return payload
    except Exception as e:
        print("❌ JWT verification failed:", e)
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def store_user_if_new(db: Session, email: str, role: str = None, name: str = None):
    """Safely store a user, updating role if missing."""
    user = None
    try:
        if not email:
            print("⚠️ No email provided — skipping user creation.")
            return None
        
        email = email.lower().strip()
        valid_roles = {"dentist", "patient"}
        
        user = db.query(User).filter(User.email.ilike(email)).first()
        
        if not user:
            # New user logic
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
            # Update role if it was missing
            user.role = role
            db.commit()
            db.refresh(user)
            print(f"🔄 Updated existing user {email} role → {role}")
        else:
            print(f"ℹ️ User already exists: {email} ({user.role})")
            
        return user
            
    except Exception as e:
        db.rollback()
        print(f"⚠️ Error storing user {email}: {e}")
        return user

@app.get("/appointments/today")
def get_today_appointments(request: Request, db: Session = Depends(get_db)):
    """
    Returns today's appointments:
    - Dentist → sees all appointments
    - Patient → sees only their appointments
    """

    # ---------------- TOKEN CHECK ----------------
    token = request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Missing token")

    payload = verify_token(token)

    email = payload.get("email") or payload.get("email_address")
    if not email:
        raise HTTPException(status_code=401, detail="Email missing in token")

    # ---------------- USER LOOKUP ----------------
    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user:
        user = store_user_if_new(db, email)
        if not user:
            raise HTTPException(status_code=500, detail="User creation failed")

    # ---------------- TODAY'S RANGE ----------------
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

    # ---------------- ROLE FILTER (FIXED FOR DENTIST) ----------------
    if user.role == "dentist":
        # Derive doctor name EXACTLY as stored in appointments.doctor_name
        # From email → prachi.swarnim@gmail.com → "Dr. Prachi Swarnim"
        email_prefix = email.split("@")[0]                 # prachi.swarnim
        clean = email_prefix.replace(".", " ")             # prachi swarnim
        proper = " ".join([p.capitalize() for p in clean.split()])  # Prachi Swarnim
        dentist_name = f"Dr. {proper}"

        print("👨‍⚕️ DENTIST NAME FOR FILTER:", dentist_name)

        appts = base_query.filter(
            Appointment.doctor_name.ilike(dentist_name)
        ).all()

    else:
        # PATIENT SIDE
        patient = db.query(Patient).filter(Patient.user_id == user.id).first()
        if not patient:
            return {"appointments": []}

        appts = base_query.filter(Appointment.patient_id == patient.id).all()

    # ---------------- FETCH LATEST INTERACTIONS (FAST) ----------------
    patient_ids = [a.patient_id for a in appts]

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

    # ---------------- FORMAT RESPONSE ----------------
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

    # Validate dentist user
    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user or user.role != "dentist":
        return {"today": [], "upcoming": []}

    # Build name identical to appointment table
    email_prefix = email.split("@")[0]
    clean = email_prefix.replace(".", " ")
    proper = " ".join([p.capitalize() for p in clean.split()])
    dentist_name = f"Dr. {proper}"

    print("🔍 FILTERING FOR:", dentist_name)

    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    today_end = today_start + timedelta(days=1)

    # Fetch today's appointments
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

    # Fetch upcoming appointments
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

@app.post("/ai_response")
async def ai_response(request: Request, payload: dict, db: Session = Depends(get_db)):
    user_msg = payload.get("query", "")
    if not user_msg:
        return {"answer": "I didn't receive any message. Could you please repeat that?"}

    db_user_id = None
    clerk_name = "Patient"   # fallback
    patient = None

    try:
        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            decoded = verify_token(token)

            email = decoded.get("email") or decoded.get("email_address")
            clerk_user_id = decoded.get("sub")

            # ---------------------------------------------------
            # FETCH FULL USER PROFILE FROM CLERK REST API
            # ---------------------------------------------------
            try:
                headers = {"Authorization": f"Bearer {CLERK_SECRET_KEY}"}
                url = f"{CLERK_API_BASE}/users/{clerk_user_id}"
                resp = requests.get(url, headers=headers, timeout=6)

                if resp.status_code == 200:
                    data = resp.json()

                    # Same logic as frontend – keeps names consistent
                    full = data.get("full_name")
                    first = data.get("first_name") or ""
                    last = data.get("last_name") or ""

                    clerk_name = full or (first + " " + last).strip() or "Patient"

                else:
                    print("⚠ Clerk REST fetch failed:", resp.status_code, resp.text)

            except Exception as e:
                print("⚠ Clerk REST name fetch error:", e)

            # ---------------------------------------------------
            # MATCH / CREATE LOCAL USER + PATIENT
            # ---------------------------------------------------
            if email:
                user = db.query(User).filter(User.email.ilike(email)).first()

                if user:
                    db_user_id = user.id

                    # Attach Clerk name to patient
                    patient = get_or_create_patient(
                        db,
                        user,
                        clerk_name=clerk_name
                    )

    except Exception as e:
        print("⚠ Error auto-linking patient:", e)

    # ---------------------------------------------------
    # PASS clerk_name to AI handler ALWAYS
    # ---------------------------------------------------
    reply = await handle_user_utterance_text(
        user_msg,
        user=str(db_user_id),
        db_user_id=db_user_id,
        clerk_name=clerk_name
    )

    return JSONResponse({"answer": reply})

# --------------------------------------------------------------------------
#                                 ROUTES
# --------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def serve_landing():
    return load_html("landing.html")

@app.get("/login", response_class=HTMLResponse)
def login_page():
    return load_html("login.html")

@app.get("/signup_redirect", response_class=RedirectResponse)
async def signup_redirect(request: Request, db: Session = Depends(get_db)):
    token = await Clerk.session.getToken(...)  # Clerk handles internally

    token = request.query_params.get("token")
    if not token:
        # Clerk auto-attaches the token on redirect after signup
        return RedirectResponse("/login?error=signup_no_token")

    payload = verify_token(token)
    email = payload.get("email") or payload.get("email_address")

    if not email:
        return RedirectResponse("/login?error=email_missing")

    email = email.lower().strip()

    # Check if user is already in DB
    user = db.query(User).filter(User.email.ilike(email)).first()

    if user and user.role:
        if user.role == "dentist":
            return RedirectResponse(f"/dentist?token={token}")
        else:
            return RedirectResponse(f"/patient?token={token}")

    # New user → no role → store and send to role selection
    if not user:
        store_user_if_new(db, email, role=None)

    return RedirectResponse(f"/role_selection?token={token}&email={email}")


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


@app.get("/dentist", response_class=HTMLResponse)
def user_dashboard(request: Request):
    token = request.query_params.get("token")
    if not token:
        return RedirectResponse(url="/login")
    
    try:
        # Attempt token verification
        verify_token(token)
    except HTTPException:
        # If verification fails, redirect the user back to login
        print("⚠️ Token failed verification. Redirecting user to /login.")
        return RedirectResponse(url="/login?reason=token_expired", status_code=302)
        
    return load_html("user_dashboard.html")


@app.get("/patient", response_class=HTMLResponse)
def patient_dashboard(request: Request):
    token = request.query_params.get("token")
    if not token:
        return RedirectResponse(url="/login")

    try:
        # Attempt token verification
        verify_token(token)
    except HTTPException:
        # If verification fails, redirect the user back to login
        print("⚠️ Token failed verification. Redirecting user to /login.")
        return RedirectResponse(url="/login?reason=token_expired", status_code=302)
        
    return load_html("patient_dashboard.html")

@app.get("/check_user_role")
def check_user_role(email: str, db: Session = Depends(get_db)):
    email = email.lower().strip()
    user = db.query(User).filter(User.email.ilike(email)).first()

    if not user:
        return {"exists": False}

    return {
        "exists": True,
        "role": user.role
    }

@app.post("/doctor_ai/query")
async def doctor_ai(request: Request):
    payload = await request.json()
    query = payload.get("query", "")

    # -----------------------------------------------------
    # 1) Get doctor identity from Authorization header
    # -----------------------------------------------------
    auth = request.headers.get("Authorization")
    doctor_name = "Doctor"  # fallback

    if auth and auth.startswith("Bearer "):
        token = auth.split(" ")[1]
        try:
            decoded = verify_token(token)
            email = decoded.get("email") or decoded.get("email_address")
            clerk_user_id = decoded.get("sub")

            # Fetch full doctor profile from Clerk
            headers = {"Authorization": f"Bearer {CLERK_SECRET_KEY}"}
            url = f"{CLERK_API_BASE}/users/{clerk_user_id}"
            resp = requests.get(url, headers=headers, timeout=5)

            if resp.status_code == 200:
                data = resp.json()
                full = data.get("full_name")
                first = data.get("first_name") or ""
                last = data.get("last_name") or ""
                doctor_name = full or (first + " " + last).strip() or "Doctor"

        except Exception as e:
            print("⚠ Doctor name fetch failed:", e)

    # -----------------------------------------------------
    # 2) Load KB (FAISS or numpy)
    # -----------------------------------------------------
    index = faiss.read_index("dental_embeddings.faiss")
    with open("dental_meta.json", "r", encoding="utf-8") as f:
        meta = json.load(f)
    chunks = meta["chunks"]

    # -----------------------------------------------------
    # 3) Get embedding for question
    # -----------------------------------------------------
    embedding_result = genai_client.models.embed_content(
        model="models/text-embedding-004",
        contents=[query]
    )
    # The result's .embeddings[0] is the ContentEmbedding object.
    query_emb_object = embedding_result.embeddings[0] 

    # FIX: Convert the ContentEmbedding object (which contains the vector data) 
    # to a standard list of floats before creating the NumPy array.
    query_vector = query_emb_object.values 
    query_vec = np.array([query_vector], dtype="float32")

    D, I = index.search(query_vec, 5)
    context = "\n\n".join(chunks[i] for i in I[0])
    # -----------------------------------------------------
    # 4) Generate response using name
    # -----------------------------------------------------
    response = genai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"""
You are FlossyAI Doctor Assistant.
Your response MUST be concise and CRISP, limited to a maximum of 5 lines, and use ONLY the provided CONTEXT.

RULES FOR RESPONSE FORMAT:
1. If the QUESTION is a simple greeting (e.g., "hi", "hello", "good morning"), respond briefly to the doctor's name {doctor_name} on the first line and then say them "Welcome to FlossyAI Doctor Assistant! How can I help you today?"
2. If the QUESTION is a substantive query (e.g., "what is plaque"), begin immediately with the concise answer. Do NOT include a greeting or the doctor's name.
3. Answer the QUESTION using ONLY the CONTEXT.
4. Be energetic and friendly in the responses.
5. If the doctor says to explain in laymann terms or simple terms do it.
CONTEXT:
{context}

QUESTION:
{query}
"""
    )

    return {"answer": response.text}

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

    # base query for future appointments
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
        # 1. Extract from token or URL
        # ----------------------------
        email = (email_param or "").strip() or None

        # try token payload if present
        if not email:
            email = payload.get("email") or payload.get("email_address") or None

        # if still no email, fetch from Clerk API using sub (user id)
        if not email and user_id_clerk:
            try:
                headers = {"Authorization": f"Bearer {CLERK_SECRET_KEY}"}
                resp = requests.get(f"{CLERK_ISSUER}/v1/users/{user_id_clerk}", headers=headers, timeout=6)
                if resp.status_code == 200:
                    user_data = resp.json()
                    # try new shape
                    primary = user_data.get("primary_email_address")
                    if isinstance(primary, dict):
                        email = primary.get("email_address")
                    # fallback older shape
                    if not email:
                        primary_id = user_data.get("primary_email_address_id")
                        email_obj = next(
                            (e for e in user_data.get("email_addresses", []) if e.get("id") == primary_id),
                            None
                        )
                        if email_obj:
                            email = email_obj.get("email_address")
                    # last fallback: if `email_addresses` array exists, pick first verified email
                    if not email and user_data.get("email_addresses"):
                        first = user_data.get("email_addresses")[0]
                        email = first.get("email_address")
                else:
                    print(f"⚠️ Clerk API returned {resp.status_code} when fetching user {user_id_clerk}")
            except Exception as e:
                print("⚠️ Clerk API fetch failed:", e)

        # absolute fallback – create unique placeholder so DB insertion still works
        if not email:
            email = f"{user_id_clerk or 'unknown'}@noemail.clerk"

        email = email.lower().strip()
        print(f"➡️ Resolved email for redirect_user: {email}")

        # -----------------------------------------
        # 2. Role Enforcement/Validation (NEW LOGIC)
        # -----------------------------------------
        
        # Only check the whitelist if the role is being explicitly set to 'dentist'
        if role_param == "dentist":
            # Check if the user's email is in the authorized list
            if email not in [e.lower() for e in AUTHORIZED_DENTIST_EMAILS]:
                # If unauthorized, force the role to 'patient'
                role_param = "patient"
                print(f"⚠️ UNAUTHORIZED DENTIST ATTEMPT: {email}. Forcing role to 'patient'.")
        
        # -----------------------------------------
        # 3. Create or update user in DB
        # -----------------------------------------
        user = store_user_if_new(db, email, role=role_param)

        if not user:
            return RedirectResponse(url="/login?error=user_creation_failed", status_code=302)

        # -----------------------------------------
        # 4. Role-based dashboard redirect
        # -----------------------------------------
        if user.role == "dentist":
            return RedirectResponse(url=f"/dentist?token={clerk_token}", status_code=302)

        if user.role == "patient":
            return RedirectResponse(url=f"/patient?token={clerk_token}", status_code=302)

        # -----------------------------------------
        # 5. User needs to choose a role (fallback)
        # -----------------------------------------
        # Pass the token for persistence across the role selection
        return RedirectResponse(url=f"/role_selection?token={clerk_token}&email={email}", status_code=302)

    except Exception as e:
        print("❌ redirect failure:", e)
        return RedirectResponse(url="/login?error=redirect_failure", status_code=302)

@app.get("/.well-known/appspecific/{path:path}")
def ignore_chrome_devtools(path: str):
    return JSONResponse({"status": "ignored"}, status_code=204)

@app.get("/post_login", response_class=HTMLResponse)
async def post_login(request: Request):
    return load_html("post_login.html")

@app.get("/signup/sso-callback")
async def clerk_signup_callback():
    return RedirectResponse(url="/post_login")

@app.get("/debug_users", response_class=JSONResponse)
def debug_users(db: Session = Depends(get_db)):
    """Lists all users (for dev/debug)."""
    users = db.query(User).all()
    return {
        "count": len(users),
        "users": [
            {"id": u.id, "email": u.email, "role": u.role, "created_at": str(u.created_at)}
            for u in users
        ],
    }


@app.on_event("startup")
def on_startup():
    init_db()
    print("✅ FlossyAI server started | Clerk OAuth & JWT ready.")