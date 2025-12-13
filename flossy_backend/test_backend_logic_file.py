
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
    with open("test_output.txt", "w") as f:
        db = SessionLocal()
        try:
            # 1. Simulate Name Generation
            email = "prachi.swarnim@gmail.com" # Assumed email
            email_prefix = email.split("@")[0]
            clean = email_prefix.replace(".", " ")
            proper = " ".join([p.capitalize() for p in clean.split()])
            dentist_name = f"Dr. {proper}"
            
            f.write(f"DEBUG: Generating name for '{email}' -> '{dentist_name}'\n")

            # 2. Simulate Time Logic
            now = datetime.now(timezone.utc)
            today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
            today_end = today_start + timedelta(days=1)
            
            f.write(f"DEBUG: Now(UTC): {now}\n")
            f.write(f"DEBUG: Today End(UTC): {today_end}\n")

            # 3. Run Query
            f.write("\n--- Running Upcoming Query ---\n")
            upcoming_appts = (
                db.query(Appointment)
                .filter(
                    Appointment.doctor_name.ilike(dentist_name),
                    Appointment.datetime >= today_end,
                )
                .order_by(Appointment.datetime.asc())
                .all()
            )
            
            f.write(f"Found {len(upcoming_appts)} upcoming appointments.\n")
            for a in upcoming_appts:
                f.write(f"  -> ID: {a.id}, Time: {a.datetime}, Doctor: '{a.doctor_name}'\n")

            # 4. Check if it exists WIHTOUT filter
            f.write("\n--- Check WITHOUT Date Filter ---\n")
            all_appts = db.query(Appointment).filter(Appointment.doctor_name.ilike(dentist_name)).all()
            for a in all_appts:
                f.write(f"  -> ID: {a.id}, Time: {a.datetime}, Is >= TodayEnd? {a.datetime >= today_end}\n")

        except Exception as e:
            f.write(f"ERROR: {e}\n")
        finally:
            db.close()

if __name__ == "__main__":
    run_test()
