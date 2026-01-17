from datetime import datetime, timezone
import requests
from app.core.config import CLERK_SECRET_KEY
from app.models import User, Patient
from sqlalchemy.orm import Session

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
        "anyhting.handmade1@gmail.com", 
        "anything.handmade1@gmail.com",
        "smileartists.reception@gmail.com" # Added fallback
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

def sync_user_to_db(db: Session, user_payload: dict, email_hint: str = None) -> User:
    """
    Ensures a User (and Patient profile) exists in the local DB.
    """
    email = fetch_clerk_email(user_payload)
    
    if not email and email_hint:
        print(f"💡 Email not in JWT, using hint: {email_hint}")
        email = email_hint.lower().strip()

    if not email:
        print(f"❌ sync_user_to_db aborted: No email found in payload {user_payload.get('sub')}")
        return None

    role = get_automatic_role(email)
    print(f"🔍 Syncing user {email}. Automatic role: {role}")
    
    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user:
        print(f"🌱 Creating new user in DB: {email} with role {role}")
        user = User(email=email, role=role, created_at=datetime.now(timezone.utc))
        db.add(user)
        db.commit()
        db.refresh(user)
        sync_clerk_role(user_payload, role)
    else:
        # Update role if it doesn't match the automatic assignment
        if user.role != role:
            print(f"🔄 Updating user role: {email} ({user.role} -> {role})")
            user.role = role
            db.commit()
            sync_clerk_role(user_payload, role)

    # ALWAYS ensure a patient profile exists for every user
    # This identifies them as a "person" in the system (Dentists/Staff are also people)
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        print(f"🌱 Creating patient profile for user: {email}")
        # Try to get names from payload
        fname = user_payload.get("given_name") or user_payload.get("first_name") or email.split("@")[0]
        lname = user_payload.get("family_name") or user_payload.get("last_name") or ""
        
        patient = Patient(
            name=f"{fname} {lname}".strip(),
            phone="0000000000",
            user_id=user.id,
            contact_datetime=datetime.now(timezone.utc),
            source="website"
        )
        db.add(patient)
        db.commit()
            
    return user

