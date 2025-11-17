import os
import asyncio
import json
import base64
import tempfile
from datetime import datetime, timedelta, timezone, time 
from typing import Optional, Literal, List, Dict 

# --- NEW IMPORTS for Structured Output ---
from pydantic import BaseModel, Field
# ----------------------------------------

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from vosk import Model, KaldiRecognizer
import pyttsx3
from dateutil import parser as dtparser

# ⭐ CORRECT GEMINI IMPORT
from google.genai import Client

from sqlalchemy.orm import Session
from database import SessionLocal
from models import Patient, Appointment, Interaction
from sqlalchemy import func

load_dotenv()

# -----------------------------------------------------
# Pydantic Schema for Gemini Output
# -----------------------------------------------------
class FlossyAIResponse(BaseModel):
    """Schema for the structured output from the FlossyAI agent."""
    intent: Literal["book_appointment", "cancel_appointment", "symptom", "smalltalk"] = Field(
        ..., description="The primary intent of the user's utterance."
    )
    name: Optional[str] = Field(None, description="The name of the patient, if mentioned.")
    date: Optional[str] = Field(None, description="The appointment date (YYYY-MM-DD), if provided or inferred.")
    time: Optional[str] = Field(None, description="The appointment time (HH:MM in 24-hour format), if provided or inferred.")
    phone: Optional[str] = Field(None, description="The patient's phone number.")
    symptom_message: Optional[str] = Field(None, description="The reason or symptom for the appointment.")
    message: str = Field(..., description="A brief, conversational reply or question to move the interaction forward.")
    ready_for_booking: bool = Field(False, description="True if all booking slots (name, date, time, phone, symptom_message) are filled.")
    ready_for_cancellation: bool = Field(False, description="True if the phone slot is filled for cancellation.")


# -----------------------------------------------------
# CONFIG
# -----------------------------------------------------
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
VOSK_MODEL_PATH = os.getenv("VOSK_MODEL_PATH", "models/vosk-model-small-en-us-0.15")
SAMPLE_RATE = 16000

# --- SIMULATED DOCTOR SCHEDULE ---
BUSINESS_START_HOUR = 9
BUSINESS_END_HOUR = 17 # 5 PM
SLOT_DURATION_MINUTES = 30 
DEFAULT_DOCTOR_NAME = "Dr. Ava Sharma" 
# ---------------------------------

if not os.path.exists(VOSK_MODEL_PATH):
    raise RuntimeError("❌ Missing Vosk model")

vosk_model = Model(VOSK_MODEL_PATH)
genai_client = Client(api_key=GEMINI_API_KEY)

app = FastAPI(title="FlossyAI Voice Agent")

voice_states = {}
text_states = {}

# -----------------------------------------------------
# TTS
# -----------------------------------------------------
def tts_synthesize_wav(text: str) -> bytes:
    engine = pyttsx3.init()
    engine.setProperty("rate", 150)

    for v in engine.getProperty("voices"):
        if "female" in v.name.lower():
            engine.setProperty("voice", v.id)

    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)

    engine.save_to_file(text, path)
    engine.runAndWait()

    with open(path, "rb") as f:
        audio = f.read()
    os.remove(path)
    return audio


async def stream_audio(ws: WebSocket, audio: bytes):
    chunk = 32 * 1024
    for i in range(0, len(audio), chunk):
        part = audio[i:i+chunk]
        b64 = base64.b64encode(part).decode("ascii")
        await ws.send_text(json.dumps({"type": "audio_chunk", "data": b64}))
        await asyncio.sleep(0.005)

    await ws.send_text(json.dumps({"type": "audio_done"}))


# -----------------------------------------------------
# GEMINI CALL (Corrected API Usage with Pydantic)
# -----------------------------------------------------
async def ask_gemini(prompt: str) -> Optional[dict]:
    """
    Calls the Gemini API using Pydantic schema for robust structured JSON output.
    Includes cleanup logic to handle model output wrappers like markdown fences.
    """
    try:
        resp = genai_client.models.generate_content(
            # Using gemini-2.5-flash for speed and structured output capabilities
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                # Enforce JSON output using Pydantic schema
                "response_mime_type": "application/json",
                "response_schema": FlossyAIResponse.model_json_schema()
            }
        )
        
        # --- Cleanup to avoid the "Expecting value" error ---
        clean_text = resp.text.strip()
        # Remove common markdown fence wrappers
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:].strip()
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3].strip()

        # Parse the clean JSON text
        return json.loads(clean_text)
        
    except Exception as e:
        print(f"Gemini/JSON Parsing Error: {e}")
        # Log the problematic text for debugging if possible
        if 'resp' in locals():
             print(f"Problematic response text (start): '{resp.text[:200]}...'")
        return None


# -----------------------------------------------------
# AVAILABILITY LOGIC
# -----------------------------------------------------

def is_slot_available(db: Session, slot_time: datetime) -> bool:
    """Checks if a specific time slot is already booked."""
    
    # Define the end time for this slot based on the standard duration (30 mins)
    slot_end_time = slot_time + timedelta(minutes=SLOT_DURATION_MINUTES)

    # Check for overlapping appointments in the database
    # We query for any scheduled appointment (A) that overlaps with the target slot (S):
    # A_start < S_end AND A_end > S_start
    conflict = db.query(Appointment).filter(
        Appointment.status == "scheduled",
        Appointment.datetime < slot_end_time,
        (Appointment.datetime + timedelta(minutes=SLOT_DURATION_MINUTES)) > slot_time
    ).first()

    return conflict is None


def find_next_available_slot(db: Session, preferred_dt: datetime) -> datetime:
    """
    Finds the next available 30-minute slot starting from the preferred time,
    respecting business hours and database conflicts.
    """
    now_utc = datetime.now(timezone.utc)
    
    # 1. Start looking from the preferred time, or immediately if preferred time is past.
    current_check_dt = preferred_dt
    if current_check_dt < now_utc:
        # If the user suggested a past time, start checking from 30 minutes in the future
        current_check_dt = now_utc + timedelta(minutes=SLOT_DURATION_MINUTES)
    
    # Normalize the starting time to the nearest 30-minute increment
    current_check_dt = current_check_dt.replace(second=0, microsecond=0)
    if current_check_dt.minute % SLOT_DURATION_MINUTES != 0:
        minutes_to_add = SLOT_DURATION_MINUTES - (current_check_dt.minute % SLOT_DURATION_MINUTES)
        current_check_dt += timedelta(minutes=minutes_to_add)

    # Ensure we start checking on a business day
    while current_check_dt.weekday() in [5, 6]: # 5=Saturday, 6=Sunday
        current_check_dt += timedelta(days=1)
        current_check_dt = current_check_dt.replace(hour=BUSINESS_START_HOUR, minute=0)

    # 2. Iterate through slots until an available one is found
    MAX_DAYS_AHEAD = 30
    end_search_date = current_check_dt + timedelta(days=MAX_DAYS_AHEAD)
    
    while current_check_dt < end_search_date:
        
        # Check if the time is outside of today's business hours
        if current_check_dt.hour >= BUSINESS_END_HOUR:
            # Skip to the start of the next business day
            current_check_dt += timedelta(days=1)
            current_check_dt = current_check_dt.replace(hour=BUSINESS_START_HOUR, minute=0)
            
            # Ensure the new day is not a weekend
            while current_check_dt.weekday() in [5, 6]:
                current_check_dt += timedelta(days=1)
            continue
        
        # If the time is within business hours (and past current time) and the slot is free
        if current_check_dt.hour >= BUSINESS_START_HOUR and current_check_dt > now_utc and is_slot_available(db, current_check_dt):
            return current_check_dt # Found the next available slot!
        
        # Move to the next slot
        current_check_dt += timedelta(minutes=SLOT_DURATION_MINUTES)
        
    # Fallback if no slot is found within 30 days
    return now_utc + timedelta(days=MAX_DAYS_AHEAD + 1) # Return a very distant future date

# -----------------------------------------------------
# BOOKING LOGIC (shared)
# -----------------------------------------------------
def execute_booking(db: Session, st: Dict, db_user_id: Optional[int] = None) -> datetime:
    name = st["name"]
    date_val = st["date"]
    time_val = st["time"]
    phone = st["phone"]
    symptom_val = st.get("symptom_message", "Reason not provided by user.")
    
    now_utc = datetime.now(timezone.utc)
    
    # 1. Determine the user's *preferred* starting point (even if it's tentative)
    preferred_dt = now_utc + timedelta(minutes=5) # Default start point: 5 minutes from now

    # Try to combine date and time from the model. 
    # If the model gives "tomorrow" and "morning", the 'date' and 'time' fields will reflect this.
    try:
        dt_string = f"{date_val} {time_val}"
        parsed_dt = dtparser.parse(dt_string)
        if parsed_dt.tzinfo is None or parsed_dt.tzinfo.utcoffset(parsed_dt) is None:
             # Assume model results are relative to system local time if not specified, then convert to UTC
             parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
        
        # If the parsed date is reasonable and in the future, use it as the preferred starting point
        if parsed_dt > now_utc - timedelta(minutes=5):
            preferred_dt = parsed_dt
            
    except Exception:
        # If parsing fails (e.g., empty slots or bad format), use the default
        pass 

    # 2. Find the actual *available* booking time
    dt_final = find_next_available_slot(db, preferred_dt)

    # 3. Handle Patient Record (Create/Update Link)
    p = db.query(Patient).filter(Patient.phone == phone).first()
    if not p:
        p = Patient(name=name, phone=phone, contact_datetime=now_utc, user_id=db_user_id)
        db.add(p)
        db.commit()
    elif db_user_id is not None and p.user_id is None:
        p.user_id = db_user_id
        db.commit()

    # 4. Create Appointment
    appt = Appointment(
        patient_id=p.id,
        datetime=dt_final,
        status="scheduled",
        doctor_name=DEFAULT_DOCTOR_NAME # <--- NEW DOCTOR NAME ASSIGNMENT
    )
    db.add(appt)
    db.commit()

    # 5. Log Interaction
    log = Interaction(
        patient_id=p.id,
        channel="text", 
        message=f"Booked appointment for {name} on {dt_final} with {DEFAULT_DOCTOR_NAME}. Reason: {symptom_val}",
        created_at=now_utc
    )
    db.add(log)
    db.commit()

    return dt_final


# -----------------------------------------------------
# VOICE HANDLER
# -----------------------------------------------------
async def handle_user_utterance(ws: WebSocket, text: str, db_user_id: Optional[int] = None):
    cid = id(ws)
    db = SessionLocal()
    state = voice_states.get(cid, {})
    
    current_time_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    prompt = f"""
You are FlossyAI, the smart dental assistant. Your task is to extract necessary information
from the user's utterance and current STATE to fill the JSON schema accurately.
**CURRENT TIME: {current_time_utc}** - Suggest a future date/time relative to CURRENT TIME if needed.

Required for Booking: 'name', 'date', 'time', 'phone', 'symptom_message'. 
Required for Cancellation: 'phone'.

If any slot is missing, use the 'message' field to ask the user for it.
When all required fields for booking/cancellation are present, set the corresponding 'ready_for_' field to true.

USER: "{text}"
STATE: {state}
"""

    ai = await ask_gemini(prompt)
    if not ai:
        return await send_bot(ws, "I'm experiencing a communication error. Could you try rephrasing that?")

    if cid not in voice_states:
        voice_states[cid] = {}

    for key in ["name", "date", "time", "phone", "symptom_message"]:
        if ai.get(key):
            voice_states[cid][key] = ai[key]

    st = voice_states[cid]

    # BOOKING
    if ai.get("ready_for_booking"):
        dt_final = execute_booking(db, st, db_user_id)
        voice_states[cid] = {}
        
        # Display the time clearly, explicitly stating UTC to match the DB value
        formatted_time = dt_final.strftime('%A, %B %d at %I:%M %p UTC')
        # UPDATED CHAT MESSAGE WITH DOCTOR NAME
        return await send_bot(
            ws,
            f"All set, {st['name']}! Your appointment with {DEFAULT_DOCTOR_NAME} is booked for {formatted_time}. We have recorded your reason as: {st['symptom_message']}."
        )

    # CANCELLATION
    if ai.get("ready_for_cancellation"):
        phone = st.get("phone")
        if not phone:
            return await send_bot(ws, "What phone number is the appointment under?")

        p = db.query(Patient).filter(Patient.phone == phone).first()
        if not p:
            return await send_bot(ws, "No appointments found for that phone number.")

        appt = db.query(Appointment).filter(
            Appointment.patient_id == p.id,
            Appointment.status == "scheduled"
        ).first()

        if not appt:
            return await send_bot(ws, "There is no appointment to cancel.")

        appt.status = "cancelled"
        db.commit()

        voice_states[cid] = {}
        return await send_bot(ws, "Your appointment has been cancelled successfully.")

    # Normal reply
    return await send_bot(ws, ai.get("message", "I'm here to help!"))


# -----------------------------------------------------
# TEXT HANDLER for /ai_response
# -----------------------------------------------------
async def handle_user_utterance_text(query: str, user="default", db_user_id: Optional[int] = None):
    db = SessionLocal()
    st = text_states.get(user, {})
    
    current_time_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    prompt = f"""
You are FlossyAI (TEXT MODE). start the first chat with "Hi! Welcome to Smile Artists Dental Studio! I am Flossy AI." Say "How can I help you?" if the first chat starts with hello else help the patient with the query. Follow the same JSON structure and rules as the voice mode.
**CURRENT TIME: {current_time_utc}** - Suggest a future date/time relative to CURRENT TIME if needed.

Required for Booking: 'name', 'date', 'time', 'phone', 'symptom_message'. 
Required for Cancellation: 'phone'.

USER: "{query}"
STATE: {st}
"""

    ai = await ask_gemini(prompt)
    if not ai:
        return "Sorry, I couldn’t understand that."

    for k in ["name", "date", "time", "phone", "symptom_message"]:
        if ai.get(k):
            st[k] = ai[k]
    text_states[user] = st

    # BOOKING
    if ai.get("ready_for_booking"):
        dt_final = execute_booking(db, st, db_user_id)
        text_states[user] = {}
        
        # Display the time clearly, explicitly stating UTC to match the DB value
        formatted_time = dt_final.strftime('%A, %B %d at %I:%M %p UTC')
        # UPDATED CHAT MESSAGE WITH DOCTOR NAME
        return (
            f"All set, {st['name']}! 🎉 Your appointment with {DEFAULT_DOCTOR_NAME} is booked for {formatted_time}. We have recorded your reason as: {st['symptom_message']}."
        )

    # CANCELLATION
    if ai.get("ready_for_cancellation"):
        phone = st.get("phone")
        if not phone:
            return "Please provide the phone number."

        p = db.query(Patient).filter(Patient.phone == phone).first()
        if not p:
            return "No appointments found for that phone number."

        appt = db.query(Appointment).filter(
            Appointment.patient_id == p.id,
            Appointment.status == "scheduled"
        ).first()

        if not appt:
            return "There is no appointment to cancel."

        appt.status = "cancelled"
        db.commit()

        text_states[user] = {}
        return "Your appointment has been cancelled 😊"

    return ai.get("message", "How can I help you?")


# -----------------------------------------------------
# BOT RESPONSE (TTS + text)
# -----------------------------------------------------
async def send_bot(ws: WebSocket, text: str):
    await ws.send_text(json.dumps({"type": "bot_text", "text": text}))
    audio = await asyncio.get_running_loop().run_in_executor(None, tts_synthesize_wav, text)
    await stream_audio(ws, audio)


# -----------------------------------------------------
# WEBSOCKET ENDPOINT
# -----------------------------------------------------
@app.websocket("/ws/agent")
async def agent_ws_endpoint(ws: WebSocket):
    await ws.accept()
    print("🎤 Voice client connected")

    rec = KaldiRecognizer(vosk_model, SAMPLE_RATE)
    rec.SetWords(True)

    cid = id(ws)
    voice_states[cid] = {}

    await send_bot(ws, "Hello! I’m FlossyAI. How can I assist you today?")

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)

            if data.get("type") == "audio_chunk":
                chunk = base64.b64decode(data["data"])

                if rec.AcceptWaveform(chunk):
                    out = json.loads(rec.Result())
                    text = out.get("text", "")
                    if text:
                        await ws.send_text(json.dumps({"type": "transcript", "final": True, "text": text}))
                        # NOTE: db_user_id is not available in the WebSocket handler and is omitted here
                        asyncio.create_task(handle_user_utterance(ws, text)) 
                else:
                    partial = json.loads(rec.PartialResult()).get("partial", "")
                    if partial:
                        await ws.send_text(json.dumps({
                            "type": "transcript",
                            "final": False,
                            "text": partial
                        }))

    except WebSocketDisconnect:
        print("🔌 Voice client disconnected")
        voice_states.pop(cid, None)