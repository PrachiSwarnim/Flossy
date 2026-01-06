from database import SessionLocal
from models import Appointment, Patient
from datetime import datetime, timezone

db = SessionLocal()
try:
    count_appt = db.query(Appointment).count()
    count_patient = db.query(Patient).count()
    print(f"DEBUG: Appointments count: {count_appt}")
    print(f"DEBUG: Patients count: {count_patient}")

    if count_appt > 0:
        print("\nChange upcoming appointments:")
        upcoming = db.query(Appointment).filter(Appointment.status == 'scheduled').all()
        for a in upcoming:
            print(f" - ID: {a.id} | Time: {a.datetime} | Level: {a.reminder_level} | Patient: {a.patient.name if a.patient else 'None'}")
finally:
    db.close()
