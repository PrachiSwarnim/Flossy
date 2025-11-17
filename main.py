import os
import jwt
import requests
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

# --------------------------------------------------------------------------
#                         ENV + CLERK SETUP
# --------------------------------------------------------------------------

load_dotenv()

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY")
CLERK_CLIENT_ID = os.getenv("CLERK_CLIENT_ID")
CLERK_CLIENT_SECRET = os.getenv("CLERK_CLIENT_SECRET")
CLERK_ISSUER = os.getenv("CLERK_ISSUER", "https://meet-grouse-33.clerk.accounts.dev")
JWKS_URL = f"{CLERK_ISSUER}/.well-known/jwks.json"

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
    - Dentist: sees ALL appointments
    - Patient: sees ONLY their appointments
    """

    token = request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Missing token")

    payload = verify_token(token)

    email = payload.get("email") or payload.get("email_address")
    if not email:
        raise HTTPException(status_code=401, detail="Email missing in token")

    # Get user
    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user:
        # If user is not in our DB but has a valid Clerk token, we need to create them before proceeding.
        user = store_user_if_new(db, email, role=None)
        if not user:
             raise HTTPException(status_code=404, detail="User lookup failed after token verification.")

    # ---- Today’s date range in UTC ----
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, now.day, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    
    # Base query for all scheduled appointments today
    base_query = db.query(Appointment).options(joinedload(Appointment.patient)).filter(
        Appointment.datetime >= start,
        Appointment.datetime < end,
        Appointment.status == "scheduled"
    ).order_by(Appointment.datetime.asc())

    # Dentist → show ALL appointments
    if user.role == "dentist":
        appts = base_query.all()
    # Patient → show ONLY their linked appointments
    else:
        patient = db.query(Patient).filter(Patient.user_id == user.id).first()
        if not patient:
            return {"appointments": []} # Patient user exists, but no linked Patient record yet.

        appts = base_query.filter(Appointment.patient_id == patient.id).all()

    # ---- Serialize ----
    result = [
        {
            "time": a.datetime.isoformat(),
            "patient_name": a.patient.name if a.patient else "Unknown",
            # Assuming symptom/reason is stored in the latest interaction log linked to the appointment's patient
            "reason": (
                db.query(Interaction.message)
                .filter(Interaction.patient_id == a.patient_id)
                .order_by(Interaction.created_at.desc())
                .limit(1).scalar()
            ) or "N/A", 
            "doctor_name": a.doctor_name
        }
        for a in appts
    ]

    return {"appointments": result}

@app.post("/ai_response")
async def ai_response(request: Request, payload: dict, db: Session = Depends(get_db)):
    """
    Handles text chat from patient dashboard.
    Obtains token from headers to identify the user ID.
    """
    user_msg = payload.get("query", "")
    if not user_msg:
        return {"answer": "I didn't receive any message. Could you please repeat that?"}
    
    # Attempt to get the authenticated user's ID
    db_user_id = None
    try:
        # Assuming JWT token is passed in the Authorization header for API calls
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            payload = verify_token(token)
            
            email = payload.get("email") or payload.get("email_address")
            if email:
                user = db.query(User).filter(User.email.ilike(email)).first()
                if user:
                    db_user_id = user.id
    except HTTPException:
        # Token is invalid, continue anonymously or handle as error
        pass

    # Call your AI logic
    # Pass the user's DB ID to allow the booking logic to link the Patient record
    reply = await handle_user_utterance_text(user_msg, user=str(db_user_id), db_user_id=db_user_id)

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