import os
import asyncio
import json
import base64
import tempfile
import re
import difflib
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal, Dict, Tuple
from zoneinfo import ZoneInfo
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import pyttsx3
from dateutil import parser as dtparser
# Google AI (Gemini)
from google.genai import Client
# Google Speech-to-Text
from google.cloud import speech
from google.oauth2 import service_account
# Database (adjust to your project)
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Patient, Appointment, Interaction, User

load_dotenv()

# CONFIG
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY")

genai_client = Client(api_key=GEMINI_API_KEY)

BUSINESS_START_HOUR = 9
BUSINESS_END_HOUR = 17
SLOT_DURATION_MINUTES = 30
MAX_SLOTS_PER_APPOINTMENT = 2
USER_TZ = ZoneInfo("Asia/Kolkata")

# STT / TTS config
cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
render_secret_file = "/etc/secrets/flossy-476616-cf6c940eac95.json"
if os.path.exists(render_secret_file):
    cred_path = render_secret_file
if not cred_path or not os.path.exists(cred_path):
    raise RuntimeError(f"Missing GOOGLE_APPLICATION_CREDENTIALS file: {cred_path}")

gcp_credentials = service_account.Credentials.from_service_account_file(cred_path)
speech_client = speech.SpeechClient(credentials=gcp_credentials)
SAMPLE_RATE = 16000
LANGUAGE = "en-US"

app = FastAPI(title="FlossyAI Voice Agent")

voice_states: Dict[int, dict] = {}
text_states: Dict[str, dict] = {}

# RESPONSE SCHEMA
class FlossyAIResponse(BaseModel):
    intent: Literal["book_appointment", "cancel_appointment", "symptom", "smalltalk", "confirm_slot"]
    name: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    phone: Optional[str] = None
    symptom_message: Optional[str] = None
    message: str
    ready_for_booking: bool = False
    ready_for_cancellation: bool = False
    slot_confirmed: Optional[bool] = None

# AUTOCORRECT
AGGRESSIVE_DICT = sorted(set([
    "appointment","book","booking","cancel","cancellation","reschedule",
    "tooth","teeth","extraction","checkup","cleaning","root","canal",
    "dr","doctor","phone","number","tomorrow","today","morning",
    "afternoon","evening","noon","am","pm","urgent","pain","toothache",
    "yes","no","please","thanks","thank","okay","ok",
    "one","two","three","four","five","six","seven","eight","nine","ten",
    "eleven","twelve","8am","9am","schedule","slot","clinic","smile","artists","flossy","doctor"
] + [str(i) for i in range(0,60)]))

NUMBER_WORDS = {
    "one":"1","two":"2","three":"3","four":"4","five":"5","six":"6","seven":"7",
    "eight":"8","nine":"9","ten":"10","eleven":"11","twelve":"12"
}

def aggressive_autocorrect(text: str) -> str:
    if not text:
        return text
    quick_map = {
        r"\bsappointment\b":"appointment", r"\bmoring\b":"morning", r"\bteath\b":"teeth",
        r"\bdotor\b":"doctor", r"\bbokk\b":"book", r"\bscedule\b":"schedule",
        r"\bnumbr\b":"number"
    }
    s = text
    for pat, repl in quick_map.items():
        s = re.sub(pat, repl, s, flags=re.IGNORECASE)
    tokens = re.findall(r"\w+|\S", s)
    out = []
    for tok in tokens:
        if re.fullmatch(r"\W", tok):
            out.append(tok); continue
        low = tok.lower()
        if low in NUMBER_WORDS:
            out.append(NUMBER_WORDS[low]); continue
        if re.fullmatch(r"\d{1,2}(?::\d{2})?(am|pm)?", low):
            out.append(tok); continue
        matches = difflib.get_close_matches(low, AGGRESSIVE_DICT, n=1, cutoff=0.6)
        if matches:
            corr = matches[0]
            corr = corr.capitalize() if tok[0].isupper() else corr
            out.append(corr)
        else:
            out.append(tok)
    corrected = "".join(t if re.fullmatch(r"\w+", t) else t for t in out)
    return re.sub(r"\s+", " ", corrected).strip()

# NORMALIZATION
def normalize_relative_date(date_str: str) -> str:
    if not date_str:
        return date_str
    s = date_str.strip().lower()
    today = datetime.now(USER_TZ).date()
    if "today" in s:
        # If user explicitly requested today's morning/afternoon but it's already past that window, offer tomorrow instead.
        if any(token in s for token in ["morning","afternoon","evening","am","pm"]):
            now_user = datetime.now(USER_TZ)
            # If requested morning but current time is after 11:30, shift to tomorrow
            if "morning" in s and now_user.hour >= 12:
                return (today + timedelta(days=1)).strftime("%Y-%m-%d")
        return today.strftime("%Y-%m-%d")
    if "tomorrow" in s:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    return date_str

def normalize_vague_time(date_str: str, time_str: str, raw_text: Optional[str] = None) -> str:
    if time_str and time_str.strip() and not re.fullmatch(r"(morning|afternoon|evening|noon)", time_str.strip().lower()):
        return time_str
    raw_low = (raw_text or "").lower()
    # prefer explicit 'time_str' when it contains 'morning' etc.
    t = time_str or date_str or raw_low
    t_low = t.lower()
    if "morning" in t_low or "am" in t_low and not re.search(r"\d{1,2}", t_low):
        return "09:00 AM"
    if "afternoon" in t_low or "pm" in t_low and not re.search(r"\d{1,2}", t_low):
        return "02:00 PM"
    if "evening" in t_low:
        return "06:00 PM"
    if "noon" in t_low:
        return "12:00 PM"
    return time_str or ""

# STT
async def google_stt_stream(chunks: list) -> str:
    streaming_config = speech.StreamingRecognitionConfig(
        config=speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=SAMPLE_RATE,
            language_code=LANGUAGE,
            enable_automatic_punctuation=True
        ),
        interim_results=False
    )
    def request_gen():
        for ch in chunks:
            yield speech.StreamingRecognizeRequest(audio_content=ch)
    responses = speech_client.streaming_recognize(config=streaming_config, requests=request_gen())
    for response in responses:
        for result in response.results:
            if result.is_final:
                return result.alternatives[0].transcript
    return ""

# TTS
def tts_synthesize_wav(text: str) -> bytes:
    engine = pyttsx3.init()
    engine.setProperty("rate", 150)
    for v in engine.getProperty("voices"):
        if "female" in v.name.lower():
            engine.setProperty("voice", v.id); break
    fd, path = tempfile.mkstemp(suffix=".wav"); os.close(fd)
    engine.save_to_file(text, path); engine.runAndWait()
    with open(path, "rb") as f:
        audio = f.read()
    os.remove(path)
    return audio

async def stream_audio(ws: WebSocket, audio: bytes):
    chunk_size = 32 * 1024
    for i in range(0, len(audio), chunk_size):
        data = base64.b64encode(audio[i:i+chunk_size]).decode()
        await ws.send_text(json.dumps({"type":"audio_chunk","data":data}))
        await asyncio.sleep(0.003)
    await ws.send_text(json.dumps({"type":"audio_done"}))

# GEMINI
async def ask_gemini(prompt: str) -> Optional[dict]:
    try:
        resp = genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type":"application/json",
                "response_schema": FlossyAIResponse.model_json_schema()
            }
        )
        clean_text = resp.text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:].strip()
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3].strip()
        return json.loads(clean_text)
    except Exception as e:
        print("Gemini Parse Error:", e)
        return None

# SCHEDULING HELPERS
def is_slot_available(db: Session, slot_time: datetime) -> bool:
    slot_end = slot_time + timedelta(minutes=SLOT_DURATION_MINUTES)
    appointments_count = db.query(Appointment).filter(
        Appointment.status == "scheduled",
        Appointment.datetime < slot_end,
        (Appointment.datetime + timedelta(minutes=SLOT_DURATION_MINUTES)) > slot_time,
    ).count()
    return appointments_count < MAX_SLOTS_PER_APPOINTMENT

def _ceil_to_slot(dt: datetime, slot_minutes: int = SLOT_DURATION_MINUTES) -> datetime:
    if dt.minute % slot_minutes == 0:
        return dt.replace(second=0, microsecond=0)
    add = slot_minutes - (dt.minute % slot_minutes)
    dt = dt + timedelta(minutes=add)
    return dt.replace(second=0, microsecond=0)

def find_next_available_slot(db: Session, preferred_dt_user_tz: datetime) -> datetime:
    now_utc = datetime.now(timezone.utc)
    now_user = now_utc.astimezone(USER_TZ)
    preferred = preferred_dt_user_tz.replace(second=0, microsecond=0)
    preferred = _ceil_to_slot(preferred, SLOT_DURATION_MINUTES)

    if preferred <= now_user:
        preferred = now_user + timedelta(minutes=SLOT_DURATION_MINUTES)
        preferred = _ceil_to_slot(preferred, SLOT_DURATION_MINUTES)

    for _ in range(1000):
        if BUSINESS_START_HOUR <= preferred.hour < BUSINESS_END_HOUR:
            candidate_utc = preferred.astimezone(timezone.utc)
            if is_slot_available(db, candidate_utc):
                return candidate_utc
        preferred += timedelta(minutes=SLOT_DURATION_MINUTES)
        if preferred.hour >= BUSINESS_END_HOUR:
            preferred = (preferred + timedelta(days=1)).replace(hour=BUSINESS_START_HOUR, minute=0)
    return (now_utc + timedelta(days=1)).astimezone(timezone.utc)

def get_default_doctor(db: Session):
    doctor = db.query(User).filter(User.role == "dentist").first()
    if doctor:
        # if you want the email prefix as name
        name = doctor.email.split("@")[0].replace(".", " ").title()

        # OR if you want a hardcoded pretty name:
        name = "Dr. " + name
        return name

    return "Dr. Available Dentist"

# BOT UTIL
async def send_bot(ws: WebSocket, text: str):
    await ws.send_text(json.dumps({"type":"bot_text","text":text}))
    wav = await asyncio.get_running_loop().run_in_executor(None, tts_synthesize_wav, text)
    await stream_audio(ws, wav)

def check_doctor_conflict(db, doctor_name, dt_utc):
    conflict = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_name.ilike(doctor_name),
            Appointment.datetime == dt_utc,
            Appointment.status == "scheduled"
        )
        .first()
    )
    return conflict is not None

# BOOKING
def execute_booking(db: Session, st: dict, db_user_id: Optional[int] = None) -> Tuple[datetime, datetime]:
    now_utc = datetime.now(timezone.utc)
    try:
        date_str = normalize_relative_date(st.get("date", "") or "")
        time_str = normalize_vague_time(date_str, st.get("time", "") or "", st.get("raw_text"))
        raw = f"{date_str} {time_str}".strip()
        parsed = dtparser.parse(raw, fuzzy=False)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=USER_TZ)
        else:
            parsed = parsed.astimezone(USER_TZ)
        preferred_dt_user_tz = parsed
    except Exception as exc:
        preferred_dt_user_tz = (now_utc + timedelta(minutes=10)).astimezone(USER_TZ)
        print("execute_booking parse fallback:", exc)

    dt_final_utc = find_next_available_slot(db, preferred_dt_user_tz)

    patient = None
    if db_user_id:
        patient = db.query(Patient).filter(Patient.user_id == db_user_id).first()
    if not patient and st.get("phone"):
        patient = db.query(Patient).filter(Patient.phone == st.get("phone")).first()
    if not patient:
        patient = Patient(
            name=st.get("name") or "Unknown Patient",
            phone=st.get("phone") or "Unknown",
            user_id=db_user_id,
            contact_datetime=datetime.now(timezone.utc)
        )
        db.add(patient); db.commit(); db.refresh(patient)
    # 🔥 FIX: Make sure patient is linked to logged-in user
    if patient and patient.user_id is None and db_user_id is not None:
        patient.user_id = db_user_id
        db.commit()

    doctor_name = get_default_doctor(db)
    # ❌ Prevent double booking for same doctor
    if check_doctor_conflict(db, doctor_name, dt_final_utc):
        return None, None, f"{doctor_name} already has an appointment at that time."

    appt = Appointment(
        patient_id=patient.id,
        datetime=dt_final_utc,
        status="scheduled",
        doctor_name=doctor_name,
        reason=st.get("symptom_message")
    )

    db.add(appt); db.commit()

    return dt_final_utc, preferred_dt_user_tz

# VOICE HANDLER
async def handle_user_utterance(ws: WebSocket, text: str, db_user_id: Optional[int] = None, clerk_name: Optional[str] = None):
    cid = id(ws)
    db = SessionLocal()
    st = voice_states.get(cid, {})
    if clerk_name and "name" not in st:
        st["name"] = clerk_name
    user_name = st.get("name", "Patient")
    greetings = ["hi","hello","hey","hola","namaste","bonjour"]
    if "first" not in st:
        st["first"] = False; voice_states[cid] = st
        return await send_bot(ws, f"Hi {user_name}! Welcome to Smile Artists Dental Studio! How can I help you today?")
    if text.strip().lower() in greetings:
        return await send_bot(ws, f"Hello {user_name}! How can I assist you today?")

    corrected_text = aggressive_autocorrect(text)
    current_time_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    prompt = f"""
You are FlossyAI (VOICE MODE), the virtual dental assistant.
PATIENT_NAME: {user_name}
Rules:
- Name is known. NEVER ask for the user's name.
- Booking requires date, time, phone, symptom_message.
- Cancellation requires phone.
- Ask one-by-one: symptoms -> date -> time -> phone.
- If vague time given, set it into the "time" field as text.
ORIGINAL_USER_MESSAGE: "{text}"
AUTOCORRECTED_MESSAGE: "{corrected_text}"
CURRENT TIME: {current_time_utc}
STATE: {st}
"""
    ai = await ask_gemini(prompt)
    if not ai:
        return await send_bot(ws, "Sorry, I couldn't understand that. Could you repeat?")

    if ai.get("date") and "date" not in st:
        st["date"] = normalize_relative_date(ai["date"])
    if ai.get("time"):
        st["time"] = ai["time"]
    if ai.get("phone"):
        st["phone"] = ai["phone"]
    if ai.get("symptom_message"):
        st["symptom_message"] = ai["symptom_message"]
    st["raw_text"] = text
    voice_states[cid] = st

    if ai.get("ready_for_booking"):
        dt_final_utc, preferred_dt_user_tz = execute_booking(db, st, db_user_id)
        dt_local = dt_final_utc.astimezone(USER_TZ)
        formatted_local = dt_local.strftime("%A, %B %d at %I:%M %p %Z")
        time_changed = (dt_local.hour != preferred_dt_user_tz.hour) or (dt_local.minute != preferred_dt_user_tz.minute)
        reason_msg = ""
        if time_changed:
            preferred_time = preferred_dt_user_tz.strftime("%I:%M %p")
            booked_time = dt_local.strftime("%I:%M %p")
            reason_msg = f"We had to move your appointment to {booked_time} as the {preferred_time} slot was just filled. "
        voice_states[cid] = {}
        doctor_name = get_default_doctor(db)
        return await send_bot(ws, f"All set, {user_name}! Your appointment with {doctor_name} is booked for {formatted_local}. {reason_msg}We've noted your reason as: {st.get('symptom_message','')}.")
    if ai.get("ready_for_cancellation"):
        phone = st.get("phone")
        if not phone:
            return await send_bot(ws, "Could you please tell me your phone number?")
        p = db.query(Patient).filter(Patient.phone == phone).first()
        if not p:
            return await send_bot(ws, "I couldn't find any appointment under that number.")
        appt = db.query(Appointment).filter(Appointment.patient_id == p.id, Appointment.status == "scheduled").first()
        if not appt:
            return await send_bot(ws, "There is no appointment to cancel.")
        appt.status = "cancelled"; db.commit(); voice_states[cid] = {}
        return await send_bot(ws, "Your appointment has been cancelled.")
    return await send_bot(ws, ai.get("message", "How can I help you?"))

# TEXT HANDLER
async def handle_user_utterance_text(query: str, user: str = "default", db_user_id: Optional[int] = None, clerk_name: Optional[str] = None):
    db = SessionLocal()
    st = text_states.get(user, {})
    if clerk_name and "name" not in st:
        st["name"] = clerk_name
    current_time_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    greetings = ["hi","hello","hey","hola","namaste","bonjour"]
    first_msg = "first" not in st
    if first_msg and query.strip().lower() in greetings:
        st["first"] = False; name = st.get("name", clerk_name or "Patient")
        return f"Hi {name}! Welcome to Smile Artists Dental Studio! I am Flossy AI. How can I help you?"

    corrected_query = aggressive_autocorrect(query)
    prompt = f"""
You are FlossyAI (TEXT MODE), the virtual assistant for Smile Artists Dental Studio.
PATIENT_NAME: {st.get("name")}
Rules:
- Name is known. NEVER ask for it.
- Booking requires only: date, time, phone, symptom_message.
- Cancellation requires only: phone.
- Ask one-by-one: symptoms -> date -> time -> phone.
- Vague time should be placed in "time" (e.g., "tomorrow afternoon" -> time="afternoon").
ORIGINAL_USER: "{query}"
AUTOCORRECTED: "{corrected_query}"
CURRENT TIME: {current_time_utc}
STATE: {st}
"""
    ai = await ask_gemini(prompt)
    if not ai:
        return "Sorry, I couldn’t understand that."

    if ai.get("date") and "date" not in st:
        st["date"] = normalize_relative_date(ai["date"])
    if ai.get("time"):
        st["time"] = ai["time"]
    if ai.get("phone"):
        st["phone"] = ai["phone"]
    if ai.get("symptom_message"):
        st["symptom_message"] = ai["symptom_message"]
    st["raw_text"] = query
    text_states[user] = st

    if st.get("waiting_for_confirmation") and st.get("suggested_slot_utc"):
        user_raw = query.lower().strip()
        if ai.get("slot_confirmed") is True or user_raw in ["yes","yeah","yep","ok","okay"]:
            suggested_dt_utc = dtparser.parse(st["suggested_slot_utc"]).replace(tzinfo=timezone.utc)
            suggested_local = suggested_dt_utc.astimezone(USER_TZ)
            st["date"] = suggested_local.strftime("%Y-%m-%d")
            st["time"] = suggested_local.strftime("%I:%M %p")
            st["ready_for_booking"] = True
            st.pop("waiting_for_confirmation"); st.pop("suggested_slot_utc")
        elif ai.get("slot_confirmed") is False or user_raw in ["no","nope"]:
            st.pop("waiting_for_confirmation"); st.pop("suggested_slot_utc")
            text_states[user] = st
            return "No problem! What other day or time works better for you?"
        elif ai.get("date") or ai.get("time") or ai.get("intent") != "smalltalk":
            st.pop("waiting_for_confirmation"); st.pop("suggested_slot_utc")

    if st.get("date") and st.get("time") and not st.get("phone") and not st.get("ready_for_booking"):
        normalized_time = normalize_vague_time(st.get("date"), st.get("time"), st.get("raw_text"))
        raw_dt = f"{st['date']} {normalized_time}"
        preferred_dt_user_tz = None
        try:
            parsed = dtparser.parse(raw_dt, fuzzy=False)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=USER_TZ)
            else:
                parsed = parsed.astimezone(USER_TZ)
            preferred_dt_user_tz = parsed
        except:
            preferred_dt_user_tz = None

        if preferred_dt_user_tz:
            
            # ... (Existing preferred_dt_user_tz calculation) ...
            
            dt_final_utc = find_next_available_slot(db, preferred_dt_user_tz)
            dt_local = dt_final_utc.astimezone(USER_TZ)
            preferred_slotted = _ceil_to_slot(preferred_dt_user_tz)

            # Check for non-business hours/weekends
            is_weekend = preferred_slotted.weekday() >= 5
            is_outside_hours = not (BUSINESS_START_HOUR <= preferred_slotted.hour < BUSINESS_END_HOUR)
            
            # --- New Logic for Negotiation Message ---
            if dt_local.replace(tzinfo=None) != preferred_slotted.replace(tzinfo=None):
                suggested_time = dt_local.strftime("%I:%M %p")
                requested_time = preferred_slotted.strftime("%I:%M %p")
                
                reason_detail = f"The clinic is closed on weekends." if is_weekend else ""
                reason_detail = f"That time ({requested_time}) is outside our business hours." if is_outside_hours and not is_weekend else reason_detail
                reason_detail = f"The {requested_time} slot is currently full." if not reason_detail else reason_detail # Default to full if no other reason applies
                
                # Update state to wait for confirmation
                st["waiting_for_confirmation"] = True
                st["suggested_slot_utc"] = dt_final_utc.isoformat()
                st["original_request_time"] = requested_time
                text_states[user] = st
                
                return (
                    f"{reason_detail} The next opening is **{suggested_time}** on "
                    f"{dt_local.strftime('%A, %B %d')}. Does that work for you?"
                )
            # ... (rest of the block) ...
            else:
                st["original_request_time"] = preferred_slotted.strftime("%I:%M %p")
                text_states[user] = st
                return ai.get("message", "What is your phone number?")

        return ai.get("message", "I need a more specific date and time, please.")

    if ai.get("ready_for_booking") or st.get("ready_for_booking"):
        dt_final_utc, preferred_dt_user_tz_actual = execute_booking(db, st, db_user_id)
        dt_local = dt_final_utc.astimezone(USER_TZ)
        formatted = dt_local.strftime("%A, %B %d at %I:%M %p %Z")
        original_request = st.get("original_request_time")
        booked_time = dt_local.strftime("%I:%M %p")
        reason_msg = ""
        if original_request and original_request != booked_time:
            reason_msg = (
                f"Your original request for {original_request} was unavailable, "
                f"so we booked the nearest available slot at {booked_time}. "
            )
        text_states[user] = {}
        doctor_name = get_default_doctor(db)
        return (
            f"All set, {st.get('name','Patient')}! 🎉 Your appointment with {doctor_name} "
            f"is booked for {formatted}. {reason_msg}"
            f"We have recorded your reason as: {st.get('symptom_message','')}."
        )

    if ai.get("ready_for_cancellation"):
        phone = st.get("phone")
        if not phone:
            return "Please provide your phone number."
        p = db.query(Patient).filter(Patient.phone == phone).first()
        if not p:
            return "No appointments found for this phone number."
        appt = db.query(Appointment).filter(Appointment.patient_id == p.id, Appointment.status == "scheduled").first()
        if not appt:
            return "There is no appointment to cancel."
        appt.status = "cancelled"; db.commit(); text_states[user] = {}
        return "Your appointment has been cancelled 😊"

    return ai.get("message", "How can I help you?")

# WEBSOCKET ENDPOINT
@app.websocket("/ws/agent")
async def agent_ws_endpoint(ws: WebSocket):
    await ws.accept()
    cid = id(ws)
    voice_states[cid] = {}
    await send_bot(ws, "Hello! I'm FlossyAI. How can I assist you today?")
    buffer = []
    try:
        while True:
            data = json.loads(await ws.receive_text())
            if data.get("type") == "audio_chunk":
                buffer.append(base64.b64decode(data["data"]))
            elif data.get("type") == "audio_done":
                transcript = await google_stt_stream(buffer)
                buffer = []
                await ws.send_text(json.dumps({"type":"transcript","final":True,"text":transcript}))
                asyncio.create_task(handle_user_utterance(ws, transcript))
    except WebSocketDisconnect:
        voice_states.pop(cid, None)
