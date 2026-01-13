from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import SessionLocal, engine
from app.models import User, Patient

def fix_and_check_db():
    db = SessionLocal()
    print("--- FIX AND CHECK DB ---")

    # 1. Update/Fix Roles
    mappings = {
        "choudhary.shruti01@gmail.com": "dentist",
        "prachi.swarnim@gmail.com": "dentist",
        "anything.handmade1@gmail.com": "receptionist"
    }

    for email, role in mappings.items():
        user = db.query(User).filter(User.email.ilike(email)).first()
        if user:
            print(f"Checking user {email}: Current role = {user.role}, Target = {role}")
            if user.role != role:
                user.role = role
                db.commit()
                print(f" -> UPDATED to {role}")
        else:
            print(f"User {email} not found.")

    # 2. Fix NULL archives in Patients (should be 0)
    try:
        # Use raw SQL for speed and robustness against legacy models
        with engine.connect() as conn:
            conn.execute(text("UPDATE patients SET is_archived = 0 WHERE is_archived IS NULL"))
            conn.commit()
            print("Fixed NULL is_archived values.")
    except Exception as e:
        print(f"Error fixing archives: {e}")

    # 3. Dump Counts
    p_count = db.query(Patient).count()
    u_count = db.query(User).count()
    print(f"\nTotal Users: {u_count}")
    print(f"Total Patients: {p_count}")

    if p_count == 0:
        print("⚠️ No patients found! Creating dummy patient for visibility.")
        dummy = Patient(name="Test Patient", phone="0000000000", source="system", is_archived=0)
        db.add(dummy)
        db.commit()
        print("Created 'Test Patient'")

    db.close()

if __name__ == "__main__":
    fix_and_check_db()
