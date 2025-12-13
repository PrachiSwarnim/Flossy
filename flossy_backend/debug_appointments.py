
from database import SessionLocal
from models import User, Patient, Appointment
import sys

# Add current directory to path if needed (it should be fine since we run from here)

def check_db():
    print("Connecting to DB...")
    try:
        db = SessionLocal()
        users = db.query(User).all()
        
        print(f"Found {len(users)} users.")
        print("-" * 30)
        
        for u in users:
            print(f"USER: {u.first_name} {u.last_name} ({u.email})")
            patient = db.query(Patient).filter(Patient.user_id == u.id).first()
            
            if patient:
                print(f"  PATIENT ID: {patient.id}")
                appts = db.query(Appointment).filter(Appointment.patient_id == patient.id).order_by(Appointment.datetime).all()
                if appts:
                    for a in appts:
                        print(f"    [APPT] ID: {a.id} | Date: {a.datetime} | Reason: {a.reason} | Status: {a.status}")
                else:
                    print("    No appointments found.")
            else:
                print("  No patient record found.")
            print("-" * 30)
            
        db.close()
    except Exception as e:
        print(f"Error reading DB: {e}")

if __name__ == "__main__":
    check_db()
