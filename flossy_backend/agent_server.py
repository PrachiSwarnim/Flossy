# agent_server.py
import os
import asyncio
import json
import base64
import tempfile
import re
import difflib
import uuid
import numpy as np

from datetime import datetime, timedelta, timezone
from typing import Optional, Literal, Dict, Tuple
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

import pyttsx3
from dateutil import parser as dtparser

# Google APIs
from google.cloud import speech
from google.oauth2 import service_account

# Local DB models & session
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Patient, Appointment, Interaction, User, LLMInteraction

# RL + LLM helpers
from rl_core import bandit, ACTIONS, PROMPT_VARIANTS, MODELS
from utils import ai_generate, embed_with_client, cos_sim
from llm_client import genai_client

# symptom KB
from symptom_kb import get_symptom_kb

load_dotenv()

# -------------------------
# CONFIG
# -------------------------
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY")

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

# -------------------------
# RESPONSE SCHEMA
# -------------------------
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

# -------------------------
# AUTOCORRECT
# -------------------------
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

# -------------------------
# RETRY WRAPPER FOR GENAI (Prevents 503 Model Overload Crashes)
# -------------------------
async def safe_ai_generate(prompt, temperature, model, client):
    """Retries Gemini calls to avoid 503 errors and returns a fallback gracefully."""
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            return ai_generate(
                prompt,
                temperature=temperature,
                model=model,
                client_override=client,
            )
        except Exception as e:
            err_msg = str(e)
            print(f"[Gemini Retry] Attempt {attempt} failed: {err_msg}")

            # Only retry for transient service errors
            if "503" not in err_msg and "UNAVAILABLE" not in err_msg and "429" not in err_msg and "RESOURCE_EXHAUSTED" not in err_msg:
                raise

            if attempt == max_attempts:
                # return a JSON-like fallback so json.loads won't crash upstream
                # keep same schema shape but minimal
                fallback = {
                    "intent": "smalltalk",
                    "message": "FlossyAI is currently overloaded with requests. Please try again in a few moments.",
                    "ready_for_booking": False,
                    "ready_for_cancellation": False,
                    "slot_confirmed": None
                }
                return json.dumps(fallback)

            await asyncio.sleep(2.0)

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

# -------------------------
# NORMALIZATION HELPERS
# -------------------------
def normalize_relative_date(date_str: str) -> str:
    if not date_str:
        return date_str
    s = date_str.strip().lower()
    today = datetime.now(USER_TZ).date()
    if "today" in s:
        if any(token in s for token in ["morning","afternoon","evening","am","pm"]):
            now_user = datetime.now(USER_TZ)
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
    t = time_str or date_str or raw_low
    t_low = t.lower()
    if "morning" in t_low or ("am" in t_low and not re.search(r"\d{1,2}", t_low)):
        return "09:00 AM"
    if "afternoon" in t_low or ("pm" in t_low and not re.search(r"\d{1,2}", t_low)):
        return "02:00 PM"
    if "evening" in t_low:
        return "06:00 PM"
    if "noon" in t_low:
        return "12:00 PM"
    return time_str or ""

# -------------------------
# STT
# -------------------------
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

# -------------------------
# TTS
# -------------------------
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

# -------------------------
# SIMPLE GEMINI JSON PARSER (kept for non-RL paths)
# -------------------------
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

# -------------------------
# SCHEDULING HELPERS
# -------------------------
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
        name = doctor.email.split("@")[0].replace(".", " ").title()
        name = "Dr. " + name
        return name
    return "Dr. Available Dentist"

# -------------------------
# BOT UTIL
# -------------------------
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


# -------------------------
# BOOKING
# -------------------------
def execute_booking(db: Session, st: dict, db_user_id: Optional[int] = None) -> Tuple[Optional[datetime], Optional[datetime]]:
    now_utc = datetime.now(timezone.utc)
    preferred_dt_user_tz = None
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

    if patient and patient.user_id is None and db_user_id is not None:
        patient.user_id = db_user_id
        db.commit()

    doctor_name = get_default_doctor(db)
    if check_doctor_conflict(db, doctor_name, dt_final_utc):
        return None, None

    appt = Appointment(
        patient_id=patient.id,
        datetime=dt_final_utc,
        status="scheduled",
        doctor_name=doctor_name,
        reason=st.get("symptom_message")
    )

    db.add(appt); db.commit()
    return dt_final_utc, preferred_dt_user_tz

# -------------------------
# VOICE HANDLER (RL-enabled)
# -------------------------
async def handle_user_utterance(ws: WebSocket, text: str, db_user_id: Optional[int] = None, clerk_name: Optional[str] = None):
    cid = id(ws)
    db = SessionLocal()
    st = voice_states.get(cid, {})

    if clerk_name and "name" not in st:
        st["name"] = clerk_name

    user_name = st.get("name", "Patient")
    greetings = ["hi","hello","hey","hola","namaste","bonjour"]

    if "first" not in st:
        st["first"] = False
        voice_states[cid] = st
        return await send_bot(ws, f"Hi {user_name}! Welcome to Smile Artists Dental Studio! How can I help you today?")

    if text.strip().lower() in greetings:
        return await send_bot(ws, f"Hello {user_name}! How can I assist you today?")

    # AUTOCORRECT
    corrected_text = aggressive_autocorrect(text)

    # EMBEDDING FOR RL CONTEXT
    query_emb = np.array(embed_with_client(genai_client, corrected_text), dtype=float)

    # Resize to expected bandit dim
    x_context = query_emb
    if x_context.shape[0] != bandit.d:
        if x_context.shape[0] > bandit.d:
            x_context = x_context[: bandit.d]
        else:
            pad = np.zeros(bandit.d - x_context.shape[0], dtype=float)
            x_context = np.concatenate([x_context, pad])

    # RL action selection
    chosen_action_id, _ = bandit.choose(x_context, eps=0.1)
    prompt_idx, temp, ctx_size, model_idx = ACTIONS[chosen_action_id]
    chosen_prompt_template = PROMPT_VARIANTS[prompt_idx]
    chosen_model = MODELS[model_idx]

    # Build prompt (voice-specific extension)
    current_time_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    voice_extension = f"""
VOICE_MODE: True
PATIENT_NAME: {user_name}
CURRENT_TIME: {current_time_utc}
STATE: {st}
ORIGINAL_MESSAGE: "{text}"
AUTOCORRECTED_MESSAGE: "{corrected_text}"
"""
    # base prompt (keeps chosen template and voice extension)
    prompt = chosen_prompt_template + voice_extension

    # ----- STRICT JSON ENFORCED *VOICE* PROMPT -----
    prompt = f"""
You are FlossyAI, a strict JSON-only dental appointment assistant.

You MUST respond ONLY in valid JSON.
NO markdown.
NO backticks.
NO conversational text outside JSON.

Your output MUST match this schema exactly:
{FlossyAIResponse.model_json_schema()}

RULES:
- Detect the patient’s intent from speech.
- Allowed intents: book_appointment, cancel_appointment, symptom, smalltalk, confirm_slot
- Extract entities: name, date, time, phone, symptom_message.
- Interpret vague phrases:
      "tomorrow morning" → date = tomorrow (IST)
                           time = "09:00 AM"
- Never assume existing appointments.
- Never confirm bookings unless the user's JSON intent includes ready_for_booking=true.
- Use STATE to fill missing fields (if user already gave them earlier).
- If required fields are missing → ask via `message`.
- Respond ONLY with valid JSON according to the schema above.
- Before ready_for_booking=true, ALWAYS request the patient's phone number via message.


----

{chosen_prompt_template}

MODE: VOICE
PATIENT_NAME: "{user_name}"
CURRENT_TIME: "{current_time_utc}"
STATE: {json.dumps(st)}
ORIGINAL_TEXT: "{text}"
AUTOCORRECTED_TEXT: "{corrected_text}"
"""

    # Generate using RL-chosen model + temp (with retries)
    raw = await safe_ai_generate(prompt, temperature=temp, model=chosen_model, client=genai_client)
    try:
        ai = json.loads(raw)
    except Exception:
        ai = None

    if not ai:
        return await send_bot(ws, "Sorry, I couldn't understand that. Could you repeat?")

    # Update dialogue state
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

    # RL metrics (for nightly training)
    answer_text = ai.get("message", "")
    answer_vec = np.array(embed_with_client(genai_client, answer_text), dtype=float)
    context_vec = np.array(embed_with_client(genai_client, prompt), dtype=float)

    semantic_similarity = cos_sim(x_context[:answer_vec.shape[0]], answer_vec) if x_context.size and answer_vec.size else 0.0
    groundedness = cos_sim(answer_vec, context_vec) if answer_vec.size and context_vec.size else 0.0

    # Log interaction for nightly audit / RL update
    request_id = str(uuid.uuid4())
    interaction = LLMInteraction(
        request_id=request_id,
        doctor_id="VOICE_AGENT",
        query=text,
        response=answer_text,
        context_used=prompt,
        semantic_similarity=semantic_similarity,
        groundedness=groundedness,
        prompt_variant=prompt_idx,
        action_id=chosen_action_id,
        temp_used=temp,
        model_used=chosen_model,
        ctx_size_used=ctx_size,
        timestamp=datetime.utcnow()
    )
    db.add(interaction)
    db.commit()

    # Booking / cancellation logic
    if ai.get("ready_for_booking"):
        dt_final_utc, preferred_dt_user_tz = execute_booking(db, st, db_user_id)
        if not dt_final_utc:
            return await send_bot(ws, "Sorry, couldn't find an available slot. Try another time.")
        dt_local = dt_final_utc.astimezone(USER_TZ)
        formatted_local = dt_local.strftime("%A, %B %d at %I:%M %p %Z")
        voice_states[cid] = {}
        doctor_name = get_default_doctor(db)
        return await send_bot(ws, f"All set, {user_name}! Your appointment with {doctor_name} is booked for {formatted_local}. We've noted your reason as: {st.get('symptom_message','')}.")

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
        appt.status = "cancelled"
        db.commit()
        voice_states[cid] = {}
        return await send_bot(ws, "Your appointment has been cancelled.")

    # Default reply
    return await send_bot(ws, answer_text)

# -------------------------
# TEXT HANDLER (RL-enabled)
# -------------------------
# -------------------------
# TEXT HANDLER (RL-enabled)
# -------------------------
async def handle_user_utterance_text(query: str, user: str = "default",
                                     db_user_id: Optional[int] = None,
                                     clerk_name: Optional[str] = None):

    db = SessionLocal()
    st = text_states.get(user, {})

    # Set patient name from Clerk
    if clerk_name and "name" not in st:
        st["name"] = clerk_name

    # Greetings (first-turn)
    greetings = ["hi", "hello", "hey", "hola", "namaste", "bonjour"]
    if "first" not in st and query.strip().lower() in greetings:
        st["first"] = False
        name = st.get("name", clerk_name or "Patient")
        text_states[user] = st
        return f"Hi {name}! I am Flossy AI. How can I help you today?"

    # Autocorrect
    corrected_query = aggressive_autocorrect(query)

    # RL embedding
    query_emb = np.array(embed_with_client(genai_client, corrected_query), dtype=float)
    x_context = query_emb
    if x_context.shape[0] != bandit.d:
        if x_context.shape[0] > bandit.d:
            x_context = x_context[:bandit.d]
        else:
            pad = np.zeros(bandit.d - x_context.shape[0], dtype=float)
            x_context = np.concatenate([x_context, pad])

    # RL action selection
    chosen_action_id, _ = bandit.choose(x_context, eps=0.1)
    prompt_idx, temp, ctx_size, model_idx = ACTIONS[chosen_action_id]
    chosen_prompt = PROMPT_VARIANTS[prompt_idx]
    chosen_model = MODELS[model_idx]

    # Build strict JSON prompt (TEXT MODE)
    current_time_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Knowledge Base (injected)
    knowledge_base = """
    [PRICING]
    - Routine Check-up: ₹500
    - Scaling & Cleaning: starts at ₹1,500
    - Dental Implants: starts at ₹25,000
    - Root Canal: ₹4,000 - ₹8,000
    - Braces/Invisalign: Starts at ₹35,000

    [POST-OP CARE]
    - General: Do not rinse vigorously for 24 hours. No straws (leads to dry socket).
    - Swelling: Aply ice pack (10 mins on, 10 mins off).
    - Pain: Take prescribed analgesics. If pain persists >2 days, contact us.
    - Diet: Soft cold diet for 24 hours (ice cream, yogurt). Avoid spicy/hot food.

    [SYMPTOMS]
    - Toothache: Rinse with warm salt water. Floss gently. Avoid extreme heat/cold. Book ASAP.
    - Bleeding Gums: Indicates gingivitis. Resume gentle brushing/flossing. Book cleaning.
    - Knocked-out Tooth: Keep tooth in milk or saliva. Come directly to clinic within 1 hour.
    """

    prompt = f"""
You are FlossyAI, a warm, helpful, and professional Patient Dental Concierge.

You MUST respond ONLY in valid JSON.
NO markdown.
NO backticks.
NO conversational text outside JSON.

Your response MUST follow this schema exactly:
{FlossyAIResponse.model_json_schema()}

OBJECTIVE:
- Act as a smart front-desk assistant.
- Answer questions using the [KNOWLEDGE BASE] below.
- If the user asks for booking, guide them.

[KNOWLEDGE BASE]
{knowledge_base}

RULES:
1. **Intent Detection**:
   - `book_appointment`: User wants to book.
   - `cancel_appointment`: User wants to cancel.
   - `symptom`: User mentions pain/issue.
   - `smalltalk`: Greetings, pricing questions, general help.
   - `confirm_slot`: User agreed to a time.

2. **Answering Questions**:
   - If user asks about Pricing/Post-op/Symptoms, USE THE KNOWLEDGE BASE.
   - Put your helpful answer in the `message` field.
   - Be concise but warm.
   - Example Pricing: "Our implants start at ₹25,000. It depends on the case. Would you like a consultation?"

3. **Booking Flow**:
   - If user says "Book cleaning", intent=`book_appointment`.
   - Before `ready_for_booking=true`, YOU MUST HAVE:
     - `date`: Explicit or relative (tomorrow).
     - `time`: Explicit or vague (morning).
     - `phone`: User's contact number.
   - If missing, ask for it in `message`.

4. **Response Format**:
   - Respond ONLY in JSON.

----

MODE: TEXT
PATIENT_NAME: "{st.get('name', 'Patient')}"
CURRENT_TIME: "{current_time_utc}"
STATE: {json.dumps(st)}
ORIGINAL_TEXT: "{query}"
AUTOCORRECTED_TEXT: "{corrected_query}"
"""

    # Generate response
    raw = await safe_ai_generate(prompt, temperature=temp,
                                 model=chosen_model, client=genai_client)
    try:
        ai = json.loads(raw)
    except Exception:
        ai = None

    if not ai:
        return "Sorry, I couldn’t understand that."

    # Update state
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

    # RL Metrics Logging
    answer_text = ai.get("message", "")
    answer_vec = np.array(embed_with_client(genai_client, answer_text), dtype=float)
    ctx_vec = np.array(embed_with_client(genai_client, prompt), dtype=float)

    semantic_similarity = cos_sim(x_context[:answer_vec.shape[0]], answer_vec) if answer_vec.size else 0.0
    groundedness = cos_sim(answer_vec, ctx_vec) if answer_vec.size else 0.0

    interaction = LLMInteraction(
        request_id=str(uuid.uuid4()),
        doctor_id="TEXT_AGENT",
        query=query,
        response=answer_text,
        context_used=prompt,
        semantic_similarity=semantic_similarity,
        groundedness=groundedness,
        prompt_variant=prompt_idx,
        action_id=chosen_action_id,
        temp_used=temp,
        model_used=chosen_model,
        ctx_size_used=ctx_size,
        timestamp=datetime.utcnow()
    )
    db.add(interaction)
    db.commit()

    # Booking logic (unchanged)
    if st.get("date") and st.get("time") and not st.get("phone") and not st.get("ready_for_booking"):
        return ai.get("message", "What is your phone number?")

    if ai.get("ready_for_booking") or st.get("ready_for_booking"):
        dt_final_utc, _ = execute_booking(db, st, db_user_id)
        if not dt_final_utc:
            return "Sorry, couldn't book that slot."
        dt_local = dt_final_utc.astimezone(USER_TZ)
        formatted = dt_local.strftime("%A, %B %d at %I:%M %p %Z")
        text_states[user] = {}
        doctor_name = get_default_doctor(db)
        return (
            f"All set, {st.get('name','Patient')}! 🎉 Your appointment with {doctor_name} "
            f"is booked for {formatted}. We've recorded your reason as: {st.get('symptom_message','')}."
        )

    if ai.get("ready_for_cancellation"):
        phone = st.get("phone")
        if not phone:
            return "Please provide your phone number."
        p = db.query(Patient).filter(Patient.phone == phone).first()
        if not p:
            return "No appointments found for this phone number."
        appt = db.query(Appointment).filter(Appointment.patient_id == p.id,
                                            Appointment.status == "scheduled").first()
        if not appt:
            return "There is no appointment to cancel."
        appt.status = "cancelled"
        db.commit()
        text_states[user] = {}
        return "Your appointment has been cancelled 😊"

    return answer_text

# -------------------------
# Helper to handle and store symptoms
# -------------------------
async def handle_and_store_symptoms(db: Session, patient_id: int, message_text: str):
    kb = get_symptom_kb(db)
    result = await kb.process_text(message_text)
    summary = ", ".join([r["display"] for r in result.get("extracted", [])])
    interaction = Interaction(
        patient_id=patient_id,
        channel="text",
        message=message_text,
        created_at=datetime.utcnow()
    )
    db.add(interaction)
    db.commit()
    return result

# -------------------------
# WEBSOCKET ENDPOINT
# -------------------------
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
                # create task so websocket loop isn't blocked by long processing
                asyncio.create_task(handle_user_utterance(ws, transcript))
    except WebSocketDisconnect:
        voice_states.pop(cid, None)
