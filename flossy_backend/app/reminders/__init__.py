import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models import Appointment, Interaction, Patient
from app.core.database import SessionLocal
from app.services.llm_client import genai_client

# THRESHOLDS (Hours before appointment)
# We map levels to hours remaining
# Level 1: < 24 hours
# Level 2: < 12 hours
# Level 3: < 6 hours
# Level 4: < 1 hour
# Level 5: < 30 mins (0.5 hours)

THRESHOLDS = [
    (1, 10.0), # 10 Hours
    (2, 0.5)   # 30 Minutes
]

def generate_quirky_message_gemini(level: int, patient_name: str, time_str: str, doctor_name: str, remaining_text: str) -> str:
    """
    Generates a quirky, Zomato-style reminder message using Google Gemini.
    Falls back to a simple message if Gemini is unavailable or fails.
    """
    if not genai_client:
        return f"Reminder: You have an appointment at {time_str} ({level})."

    context_extra = ""
    if level == 0:
        context_extra = "Context: THIS IS A BOOKING CONFIRMATION. The patient just booked the appointment. Welcome them!"
    else:
        context_extra = f"Urgency Level: {level} (1=10hrs, 2=30mins)"

    prompt = f"""
    You are a quirky, fun, and engaging dental assistant named Flossy, inspired by Zomato's marketing style.
    Your task is to generate a short, funny, and attention-grabbing SMS for a dental appointment.

    Context:
    - Patient Name: {patient_name}
    - Doctor Name: {doctor_name}
    - Appointment Time: {time_str}
    - Time Remaining: {remaining_text}
    - {context_extra}

    Guidelines:
    - Use emojis! 🦷✨
    - Be witty and slightly dramatic but friendly.
    - Mention the EXACT time/date or remaining time as appropriate.
    - Keep it under 160 characters if possible, similar to a tweet/SMS.
    - Do NOT include any intro like "Here is a message:". Just return the message text.
    """

    try:
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"⚠️ Gemini message generation failed: {e}")
        # Fallback messages
        if level == 0:
            return f"Hi {patient_name}! Your appointment with {doctor_name} is confirmed for {time_str}. See you then! 🦷"
        elif level == 1:
            return f"Hey {patient_name}! Just 10h to go for your visit with {doctor_name} at {time_str}! ⏳"
        elif level == 2:
            return f"Hurry {patient_name}! 30 mins to go! We're ready for you! 🏃‍♂️"
        else:
            return f"Reminder: Appointment at {time_str} with {doctor_name}. See you soon!"



def send_simulated_notification(db: Session, appt: Appointment, level: int):
    """
    Sends an SMS via Twilio.
    Logs to 'Interaction' table.
    """
    from twilio.rest import Client
    import os

    patient = appt.patient
    if not patient:
        return

    time_str = appt.datetime.strftime("%I:%M %p")
    
    # Calculate exact remaining time string
    now_utc = datetime.now(timezone.utc)
    diff = appt.datetime - now_utc
    total_seconds = int(diff.total_seconds())
    
    # Ensure positive
    if total_seconds < 0:
        total_seconds = 0
        
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    if hours > 0:
        remaining_text = f"{hours}h {minutes}m"
    else:
        remaining_text = f"{minutes} mins"

    # Generate quirky message with exact time
    msg = generate_quirky_message_gemini(level, patient.name, time_str, appt.doctor_name, remaining_text)

    print(f"📢 [NOTIFICATION LOG] To: {patient.name} ({patient.phone}) | Msg: {msg}")

    # --- TWILIO SENDING ---
    account_sid = os.getenv("TWILIO_SID")
    auth_token = os.getenv("TWILIO_AUTH")
    twilio_from = os.getenv("TWILIO_FROM")
    
    # Clean phone number (Ensure it has +91 or +Code)
    to_number = patient.phone.strip()
    if not to_number.startswith("+"):
        # Default to +91 for India if no code provided, based on context
        to_number = f"+91{to_number}"
    
    sent_status = "simulated"
    
    if account_sid and auth_token and twilio_from:
        try:
            client = Client(account_sid, auth_token)
            message = client.messages.create(
                body=msg,
                from_=twilio_from,
                to=to_number
            )
            print(f"✅ Twilio SMS Sent! SID: {message.sid}")
            sent_status = "sent"
        except Exception as e:
            print(f"❌ Twilio Send Failed: {e}")
            sent_status = "failed"
    else:
        print("⚠️ Twilio credentials missing in .env")

    # Log to DB
    log = Interaction(
        patient_id=patient.id,
        channel=f"sms_{sent_status}",
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
            if eligible_level > appt.reminder_level:
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
    print("(Clock) Reminder Daemon Started")
    while True:
        await asyncio.to_thread(check_reminders_sync)
        await asyncio.sleep(60) # Run every 60 seconds
