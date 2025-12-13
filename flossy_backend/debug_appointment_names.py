
import sys
import traceback

try:
    from database import SessionLocal
    from models import Appointment, User
except Exception:
    traceback.print_exc()
    sys.exit(1)

def debug_db():
    try:
        db = SessionLocal()
    except Exception:
        print("Failed to create session.")
        traceback.print_exc()
        return

    try:
        # Get all appointments
        appts = db.query(Appointment).all()
        print(f"Found {len(appts)} appointments.")
        for a in appts:
            print(f"ID: {a.id}, Time: {a.datetime}, Status: {a.status}, Doctor: '{a.doctor_name}', PatientID: {a.patient_id}")
        
        # Get all users (dentists)
        dentists = db.query(User).filter(User.role == "dentist").all()
        print(f"\nFound {len(dentists)} dentists.")
        for d in dentists:
            print(f"ID: {d.id}, Email: {d.email}, Role: {d.role}")
            email_part = d.email.split("@")[0].replace(".", " ").title()
            generated_name = f"Dr. {email_part}"
            print(f"  -> Generated Name (Agent style): '{generated_name}'")

    except Exception:
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_db()
