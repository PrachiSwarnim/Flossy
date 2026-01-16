from datetime import datetime, timezone
import requests
from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.orm import Session
from app.core.config import CLERK_SECRET_KEY
from app.core.database import get_db
from app.models import User, Patient

router = APIRouter()

def get_automatic_role(email: str) -> str:
    """
    Returns the enforced role based on email.
    """
    email = email.lower().strip()
    if email in ["choudhary.shruti01@gmail.com", "prachi.swarnim@gmail.com"]:
        return "dentist"
    if email in ["anything.handmade1@gmail.com", "anything,handmade1@gmail.com"]:
        return "receptionist"
    return "patient"

def sync_clerk_role(user_payload: dict, role: str):
    try:
        if not CLERK_SECRET_KEY: return
        headers = {"Authorization": f"Bearer {CLERK_SECRET_KEY}"}
        clerk_user_id = user_payload.get("sub")
        if not clerk_user_id: return

        requests.patch(
            f"https://api.clerk.dev/v1/users/{clerk_user_id}",
            headers=headers,
            json={"public_metadata": {"role": role}}
        )
        print(f"Clerk metadata updated → role={role}")
    except Exception as e:
        print("Failed to update Clerk metadata:", e)

def fetch_clerk_email(user_payload: dict) -> str:
    """
    Fallback to get email from Clerk API using the user ID (sub) 
    if it's missing from the JWT token claims.
    """
    email = (user_payload.get("email") or user_payload.get("email_address") or "").lower().strip()
    if email:
        return email
        
    # Fallback: Fetch from Clerk API
    clerk_user_id = user_payload.get("sub")
    if not clerk_user_id or not CLERK_SECRET_KEY:
        return ""
        
    try:
        headers = {"Authorization": f"Bearer {CLERK_SECRET_KEY}"}
        print(f"Fetching user details from Clerk for ID: {clerk_user_id}")
        res = requests.get(f"https://api.clerk.dev/v1/users/{clerk_user_id}", headers=headers)
        if res.status_code == 200:
            data = res.json()
            # Try to get primary email or first email
            email_addresses = data.get("email_addresses", [])
            primary_id = data.get("primary_email_address_id")
            
            target_email = ""
            for e_obj in email_addresses:
                if e_obj.get("id") == primary_id:
                    target_email = e_obj.get("email_address", "")
                    break
            
            if not target_email and email_addresses:
                # Default to first if primary not found/matched
                target_email = email_addresses[0].get("email_address", "")
                
            return target_email.lower().strip()
    except Exception as e:
        print(f"Failed to fetch Clerk user details: {e}")
        
    return ""

@router.post("/check_email")
def check_email(payload: dict, db: Session = Depends(get_db)):
    email = payload.get("email", "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    exists = db.query(User).filter(User.email.ilike(email)).first() is not None
    return {"exists": exists}

@router.post("/select_role")
def select_role(payload: dict, request: Request, db: Session = Depends(get_db)):
    # Legacy endpoint: Now enforces role based on email regardless of payload
    user_payload = getattr(request.state, "user", None)
    if not user_payload:
        raise HTTPException(status_code=401, detail="Authentication required")

    email = fetch_clerk_email(user_payload)
    if not email:
        raise HTTPException(status_code=400, detail="Email could not be retrieved from token or Clerk API")

    # Determine role automatically
    role = get_automatic_role(email)

    # --- Fetch or create user in DB ---
    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user:
        user = User(email=email, role=role, created_at=datetime.now(timezone.utc))
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Enforce role update if changed
        if user.role != role:
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

    # Sync with Clerk
    sync_clerk_role(user_payload, role)

    return {"success": True, "role": role, "email": email}

@router.post("/post_login")
def post_login(request: Request, db: Session = Depends(get_db)):
    user_payload = getattr(request.state, "user", None)
    if not user_payload:
        raise HTTPException(status_code=401, detail="Authentication required")

    email = fetch_clerk_email(user_payload)
    if not email:
        raise HTTPException(status_code=400, detail="Email could not be retrieved from token or Clerk API")

    # Determine forced role
    forced_role = get_automatic_role(email)

    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user:
        user = User(email=email, role=forced_role, created_at=datetime.now(timezone.utc))
        db.add(user)
        db.commit()
        db.refresh(user)
        sync_clerk_role(user_payload, forced_role)
    else:
        # Check if role needs update
        if user.role != forced_role:
            user.role = forced_role
            db.commit()
            sync_clerk_role(user_payload, forced_role)
            
    # Ensure patient profile if needed
    if forced_role == "patient":
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

    return {"user": {"id": user.id, "email": user.email, "role": user.role}}

@router.get("/email_exists")
def email_exists(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email.ilike(email)).first()
    return {"exists": user is not None}
