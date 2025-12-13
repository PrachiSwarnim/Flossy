import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from models import Appointment, Interaction, Patient
from database import SessionLocal

# THRESHOLDS (Hours before appointment)
# We map levels to hours remaining
# Level 1: < 24 hours
# Level 2: < 12 hours
# Level 3: < 6 hours
# Level 4: < 1 hour
# Level 5: < 30 mins (0.5 hours)

THRESHOLDS = [
    (1, 24.0),
    (2, 12.0),
    (3, 6.0),
    (4, 1.0),
    (5, 0.5)
]

def send_simulated_notification(db: Session, appt: Appointment, level: int):
    """
    Simulates sending an SMS/Email.
    In real life, this would use Twilio/SendGrid.
    Here, we log to 'Interaction' table so it appears in history.
    """
    patient = appt.patient
    if not patient:
        return

    time_str = appt.datetime.strftime("%I:%M %p")
    msg = ""
    
    if level == 1:
        msg = f"Reminder: You have an appointment tomorrow at {time_str} with {appt.doctor_name}."
    elif level == 2:
        msg = f"Reminder: Your appointment is in about 12 hours ({time_str})."
    elif level == 3:
        msg = f"Reminder: See you in 6 hours for your dental checkup!"
    elif level == 4:
        msg = f"Urgent: Your appointment is in 1 hour ({time_str}). Please leave soon."
    elif level == 5:
        msg = f"Hurry! Your appointment starts in 30 minutes."

    print(f"📢 [NOTIFICATION] To: {patient.name} ({patient.phone}) | Msg: {msg}")

    # Log to DB
    log = Interaction(
        patient_id=patient.id,
        channel="sms_reminder",
        message=msg,
        created_at=datetime.now(timezone.utc)
    )
    db.add(log)
    db.commit()

def check_reminders_sync():
    """
    Synchronous worker to check all appointments.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        
        # Get all future scheduled appointments
        appts = db.query(Appointment).filter(
            Appointment.status == "scheduled",
            Appointment.datetime > now
        ).all()

        for appt in appts:
            # Calculate time remaining in hours
            diff = appt.datetime - now
            hours_remaining = diff.total_seconds() / 3600.0
            
            # Determine highest eligible level
            eligible_level = 0
            for lvl, threshold in THRESHOLDS:
                # If we are within the threshold (e.g. 23 hours < 24 hours)
                if hours_remaining <= threshold:
                    eligible_level = lvl
            
            # If we reached a new level that hasn't been sent yet
            # e.g. current level 0, eligible 1 -> Send 1
            # e.g. current level 1, eligible 2 -> Send 2
            # We strictly move up one by one or jump if missed (but usually sequential)
            if eligible_level > appt.reminder_level:
                # Send the notification for the *specific* level we just crossed
                # or strictly the highest one? 
                # Let's just update to the eligible level and send that specific message.
                
                send_simulated_notification(db, appt, eligible_level)
                
                appt.reminder_level = eligible_level
                db.commit()

    except Exception as e:
        print(f"Error in check_reminders: {e}")
    finally:
        db.close()

async def reminder_daemon():
    """
    Background task to run every minute.
    """
    print("⏰ Reminder Daemon Started")
    while True:
        await asyncio.to_thread(check_reminders_sync)
        await asyncio.sleep(60) # Run every 60 seconds
