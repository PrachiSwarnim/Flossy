from datetime import datetime, timezone
import requests
from app.core.config import CLERK_SECRET_KEY
from app.models import User, Patient
from sqlalchemy.orm import Session
import re

def extract_names_from_email(email: str) -> tuple:
    """Extract first and last names from an email address."""
    if not email or "@" not in email:
        return email or "Unknown", ""

    local_part = email.split("@")[0]
    # Split by common separators OR digits
    parts = re.split(r'[._\-\d]+', local_part)
    # Clean up common titles/prefixes
    titles = ['mr', 'ms', 'mrs', 'dr', 'prof']
    parts = [p for p in parts if p.lower() not in titles]
    # Filter empty/short parts and TitleCase them
    parts = [p.strip().title() for p in parts if len(p.strip()) >= 1]

    if len(parts) >= 2:
        # Standard: first.last -> First Last (DO NOT REVERSE)
        return parts[0], " ".join(parts[1:])
    elif len(parts) == 1:
        return parts[0], ""
    else:
        return "Unknown", ""

def get_automatic_role(email: str) -> str:
    """
    Returns the enforced role based on email.
    """
    email = email.lower().strip()
    # Dentist / Admin emails
    if email in [
        "prachi.swarnim@gmail.com", 
        "choudhary.shruti01@gmail.com", 
        "smileartistsdental@gmail.com",  # Added fallback
        "dr.prachi@smileartists.com"      # Added potential work email
    ]:
        return "dentist"
    
    # Receptionist emails
    if email in [ 
        "anything.handmade1@gmail.com",
        "prachi.swarnim07@gmail.com",
        "purviraj236@gmail.com",
        "aartikumari0975@gmail.com",
        "shruti@smileartists.in"
    ]:
        return "receptionist"
    
    # All other emails are patients
    return "patient"

def sync_clerk_role(user_payload: dict, role: str):
    try:
        if not CLERK_SECRET_KEY: return
        headers = {"Authorization": f"Bearer {CLERK_SECRET_KEY}"}
        clerk_user_id = user_payload.get("sub")
        if not clerk_user_id: return

        requests.patch(
            f"https://api.clerk.com/v1/users/{clerk_user_id}",
            headers=headers,
            json={"public_metadata": {"role": role}}
        )
        print(f"Clerk metadata updated → role={role}")
    except Exception as e:
        print("Failed to update Clerk metadata:", e)

# Known users with correct names (to prevent Clerk/email extraction errors)
KNOWN_USERS = {
    "prachi.swarnim@gmail.com": {"first_name": "Prachi", "last_name": "Swarnim"},
    "choudhary.shruti01@gmail.com": {"first_name": "Shruti", "last_name": "Choudhary"},
    "prachiswarnim03@gmail.com": {"first_name": "Prachi", "last_name": "Swarnim"},
}

def fetch_clerk_email(user_payload: dict) -> str:
    """
    Fallback to get email from Clerk API using the user ID (sub) 
    if it's missing from the JWT token claims.
    """
    email = (user_payload.get("email") or \
             user_payload.get("email_address") or \
             user_payload.get("primary_email_address") or \
             user_payload.get("preferred_username") or "").lower().strip()
    
    if email and "@" in email:
        return email
        
    # 2. Fallback: Fetch from Clerk API (Requires CLERK_SECRET_KEY)
    clerk_user_id = user_payload.get("sub")
    if not clerk_user_id:
        print("❌ No 'sub' found in user_payload")
        return ""
        
    if not CLERK_SECRET_KEY:
        print("❌ CLERK_SECRET_KEY is missing, cannot fetch email from API")
        return ""
        
    try:
        headers = {"Authorization": f"Bearer {CLERK_SECRET_KEY}"}
        # print(f"🔍 Fetching email from Clerk API for sub: {clerk_user_id}")
        res = requests.get(f"https://api.clerk.com/v1/users/{clerk_user_id}", headers=headers)
        if res.status_code == 200:
            data = res.json()
            email_addresses = data.get("email_addresses", [])
            primary_id = data.get("primary_email_address_id")
            
            target_email = ""
            for e_obj in email_addresses:
                if e_obj.get("id") == primary_id:
                    target_email = e_obj.get("email_address", "")
                    break
            
            if not target_email and email_addresses:
                target_email = email_addresses[0].get("email_address", "")
                
            print(f"✅ Found email from API: {target_email}")
            return target_email.lower().strip()
        else:
            print(f"❌ Clerk API Error ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"❌ Failed to fetch Clerk user details: {e}")
        
    return ""

def sync_user_to_db(db: Session, user_payload: dict, email_hint: str = None, fname_hint: str = None, lname_hint: str = None) -> User:
    """
    Ensures a User (and Patient profile) exists in the local DB.
    Force updates names and roles on every sync (login).
    """
    email = fetch_clerk_email(user_payload)
    if not email and email_hint:
        email = email_hint.lower().strip()

    if not email:
        return None

    role = get_automatic_role(email)
    
    # 1. Check JWT payload first (sometimes Clerk includes it)
    clerk_fname = (user_payload.get("first_name") or \
                   user_payload.get("given_name") or \
                   user_payload.get("firstName") or "").strip()
    clerk_lname = (user_payload.get("last_name") or \
                   user_payload.get("family_name") or \
                   user_payload.get("lastName") or "").strip()
    
    clerk_user_id = user_payload.get("sub")
    
    # 2. Clerk API Details (Fetch if JWT doesn't have it)
    if not clerk_fname and CLERK_SECRET_KEY and clerk_user_id:
        try:
            print(f"🔍 Fetching name from Clerk API for {clerk_user_id}...")
            headers = {"Authorization": f"Bearer {CLERK_SECRET_KEY}"}
            res = requests.get(f"https://api.clerk.com/v1/users/{clerk_user_id}", headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                clerk_fname = data.get("first_name") or ""
                clerk_lname = data.get("last_name") or ""
                print(f"✅ Clerk API returned: {clerk_fname} {clerk_lname}")
            else:
                print(f"⚠️ Clerk API error: {res.status_code} - {res.text}")
        except Exception as e:
            print(f"❌ Clerk API call failed: {e}")

    # 3. Extract names as THIRD priority fallback
    extracted_fname, extracted_lname = extract_names_from_email(email)
    
    def sanitize(val):
        if not val or str(val).lower() in ["none", "null", "undefined", "empty"]:
            return ""
        return str(val).strip()

    # PRIORITY ORDER:
    # 1. KNOWN_USERS mapping (highest priority - prevents incorrect Clerk data)
    # 2. Clerk API/JWT
    # 3. Frontend Hints (fname_hint, lname_hint)
    # 4. Email Extraction
    
    if email.lower() in KNOWN_USERS:
        known = KNOWN_USERS[email.lower()]
        final_fname = known["first_name"]
        final_lname = known["last_name"]
        print(f"✅ Using KNOWN_USERS mapping for {email}: {final_fname} {final_lname}")
    else:
        final_fname = sanitize(clerk_fname) or sanitize(fname_hint) or extracted_fname
        final_lname = sanitize(clerk_lname) or sanitize(lname_hint) or extracted_lname

    # 3. Create or Update User
    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user:
        user = User(email=email, role=role, created_at=datetime.now(timezone.utc))
        db.add(user)
        db.commit()
        db.refresh(user)
        sync_clerk_role(user_payload, role)
    
    # Sync names and role to User record
    user.first_name = final_fname
    user.last_name = final_lname
    user.role = role
    db.add(user)
    db.commit()

    # 4. Create or Update Patient Profile
    # IMPORTANT: Always check if patient exists, even for existing users
    # This handles cases where patient was deleted but user still exists
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    
    if not patient:
        import time
        unique_phone = f"TEMP_{user.id}_{int(time.time()) % 100000}"
        print(f"📝 Creating NEW Patient record for user_id={user.id}, email={email}")
        patient = Patient(
            user_id=user.id,
            name=f"{final_fname} {final_lname}".strip() or email.split('@')[0],
            first_name=final_fname,
            last_name=final_lname,
            phone=unique_phone,
            source="website",
            contact_datetime=datetime.now(timezone.utc)
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        print(f"✅ Patient created: id={patient.id}, name={patient.name}")
    else:
        print(f"📝 Updating EXISTING Patient record id={patient.id} for user_id={user.id}")
        # Force update patient names
        patient.first_name = final_fname
        patient.last_name = final_lname
        patient.name = f"{final_fname} {final_lname}".strip()
        db.add(patient)
        db.commit()
        print(f"✅ Patient updated: name={patient.name}")
    
    return user

