
import os
import sys
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from models import Appointment, Patient, User

# USER PROVIDED URL
DATABASE_URL = "postgresql+psycopg2://flossy_user:prachi2973@localhost/flossy_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def run_test():
    db = SessionLocal()
    try:
        # 1. Simulate Name Generation
        email = "prachi.swarnim@gmail.com" # Assumed email
        email_prefix = email.split("@")[0]
        clean = email_prefix.replace(".", " ")
        proper = " ".join([p.capitalize() for p in clean.split()])
        dentist_name = f"Dr. {proper}"
        
        print(f"DEBUG: Generating name for '{email}' -> '{dentist_name}'")

        # 2. Simulate Time Logic
        now = datetime.now(timezone.utc)
        today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        today_end = today_start + timedelta(days=1)
        
        print(f"DEBUG: Now(UTC): {now}")
        print(f"DEBUG: Today End(UTC): {today_end}")

        # 3. Run Query
        print("\n--- Running Upcoming Query ---")
        upcoming_appts = (
            db.query(Appointment)
            .filter(
                Appointment.doctor_name.ilike(dentist_name),
                Appointment.datetime >= today_end,
            )
            .order_by(Appointment.datetime.asc())
            .all()
        )
        
        print(f"Found {len(upcoming_appts)} upcoming appointments.")
        for a in upcoming_appts:
            print(f"  -> ID: {a.id}, Time: {a.datetime}, Doctor: '{a.doctor_name}'")

        # 4. Check if it exists WIHTOUT filter
        print("\n--- Check WITHOUT Date Filter ---")
        all_appts = db.query(Appointment).filter(Appointment.doctor_name.ilike(dentist_name)).all()
        for a in all_appts:
            print(f"  -> ID: {a.id}, Time: {a.datetime}, Is >= TodayEnd? {a.datetime >= today_end}")

    finally:
        db.close()

if __name__ == "__main__":
    run_test()
