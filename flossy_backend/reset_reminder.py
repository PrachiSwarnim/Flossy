from database import SessionLocal
from models import Appointment

db = SessionLocal()
try:
    appt = db.query(Appointment).filter(Appointment.id == 25).first()
    if appt:
        print(f"Current Level: {appt.reminder_level}")
        appt.reminder_level = 0
        db.commit()
        print(f"Reset Level to 0 for Appt {appt.id}")
    else:
        print("Appt 25 not found")
finally:
    db.close()
