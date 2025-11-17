import os
import asyncio
import json
import base64
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal, Dict

# Structured output schema
from pydantic import BaseModel, Field

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import pyttsx3
from dateutil import parser as dtparser

# Google AI (Gemini)
from google.genai import Client

# Google Speech-to-Text
from google.cloud import speech
from google.oauth2 import service_account

# Database
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Patient, Appointment, Interaction

load_dotenv()

# --------------------------------------------
# GOOGLE SPEECH TO TEXT CONFIG
# --------------------------------------------
b64_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
if not b64_creds:
    raise RuntimeError("Missing GOOGLE_APPLICATION_CREDENTIALS_JSON env variable")

service_json = json.loads(base64.b64decode(b64_creds))
gcp_credentials = service_account.Credentials.from_service_account_info(service_json)

speech_client = speech.SpeechClient(credentials=gcp_credentials)
SAMPLE_RATE = 16000
LANGUAGE = "en-US"


# --------------------------------------------
# Pydantic Schema for Gemini Output
# --------------------------------------------

class FlossyAIResponse(BaseModel):
    intent: Literal["book_appointment", "cancel_appointment", "symptom", "smalltalk"]
    name: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    phone: Optional[str] = None
    symptom_message: Optional[str] = None
    message: str
    ready_for_booking: bool = False
    ready_for_cancellation: bool = False


# --------------------------------------------
# CONFIG
# --------------------------------------------

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

genai_client = Client(api_key=GEMINI_API_KEY)

BUSINESS_START_HOUR = 9
BUSINESS_END_HOUR = 17
SLOT_DURATION_MINUTES = 30
DEFAULT_DOCTOR_NAME = "Dr. Ava Sharma"

app = FastAPI(title="FlossyAI Voice Agent")

voice_states = {}
text_states = {}


# --------------------------------------------
# GOOGLE SPEECH RECOGNITION FUNCTION
# --------------------------------------------

async def google_stt_stream(chunks: list) -> str:
    """Send raw audio chunks to Google Speech-to-Text."""
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

    responses = speech_client.streaming_recognize(
        config=streaming_config,
        requests=request_gen()
    )

    for response in responses:
        for result in response.results:
            if result.is_final:
                return result.alternatives[0].transcript

    return ""


# --------------------------------------------
# TTS ENGINE
# --------------------------------------------

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
    chunk_size = 32 * 1024
    for i in range(0, len(audio), chunk_size):
        data = base64.b64encode(audio[i:i+chunk_size]).decode()
        await ws.send_text(json.dumps({"type": "audio_chunk", "data": data}))
        await asyncio.sleep(0.003)

    await ws.send_text(json.dumps({"type": "audio_done"}))


# --------------------------------------------
# GEMINI LOGIC
# --------------------------------------------

async def ask_gemini(prompt: str) -> Optional[dict]:
    try:
        resp = genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
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


# --------------------------------------------
# SLOT AVAILABILITY + BOOKING LOGIC
# --------------------------------------------

def is_slot_available(db, slot_time):
    slot_end = slot_time + timedelta(minutes=SLOT_DURATION_MINUTES)
    conflict = db.query(Appointment).filter(
        Appointment.status == "scheduled",
        Appointment.datetime < slot_end,
        (Appointment.datetime + timedelta(minutes=SLOT_DURATION_MINUTES)) > slot_time,
    ).first()

    return conflict is None


def find_next_available_slot(db, preferred_dt):
    now = datetime.now(timezone.utc)

    preferred_dt = preferred_dt.replace(second=0, microsecond=0)
    if preferred_dt.minute % 30 != 0:
        preferred_dt += timedelta(minutes=(30 - preferred_dt.minute % 30))

    while preferred_dt.weekday() >= 5:  # Skip weekends
        preferred_dt += timedelta(days=1)
        preferred_dt = preferred_dt.replace(hour=BUSINESS_START_HOUR, minute=0)

    for _ in range(1000):
        if BUSINESS_START_HOUR <= preferred_dt.hour < BUSINESS_END_HOUR and preferred_dt > now:
            if is_slot_available(db, preferred_dt):
                return preferred_dt

        preferred_dt += timedelta(minutes=30)
        if preferred_dt.hour >= BUSINESS_END_HOUR:
            preferred_dt += timedelta(days=1)
            preferred_dt = preferred_dt.replace(hour=BUSINESS_START_HOUR, minute=0)

    return now + timedelta(days=1)


def execute_booking(db, st, db_user_id=None):
    now = datetime.now(timezone.utc)

    try:
        parsed = dtparser.parse(f"{st['date']} {st['time']}")
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        preferred_dt = parsed
    except:
        preferred_dt = now + timedelta(minutes=10)

    dt_final = find_next_available_slot(db, preferred_dt)

    patient = db.query(Patient).filter(Patient.phone == st["phone"]).first()
    if not patient:
        patient = Patient(name=st["name"], phone=st["phone"], user_id=db_user_id)
        db.add(patient)
        db.commit()

    appt = Appointment(
        patient_id=patient.id,
        datetime=dt_final,
        status="scheduled",
        doctor_name=DEFAULT_DOCTOR_NAME
    )

    db.add(appt)
    db.commit()

    return dt_final


# --------------------------------------------
# SEND BOT MESSAGE + TTS
# --------------------------------------------

async def send_bot(ws, text):
    await ws.send_text(json.dumps({"type": "bot_text", "text": text}))
    wav = await asyncio.get_running_loop().run_in_executor(None, tts_synthesize_wav, text)
    await stream_audio(ws, wav)


# --------------------------------------------
# HANDLE USER UTTERANCE
# --------------------------------------------

async def handle_user_utterance(ws, text, db_user_id=None):
    cid = id(ws)
    db = SessionLocal()

    st = voice_states.get(cid, {})

    prompt = f"""
You are FlossyAI, a dental assistant. Fill the JSON schema strictly.
USER: "{text}"
STATE: {st}
"""

    ai = await ask_gemini(prompt)
    if not ai:
        return await send_bot(ws, "I couldn’t understand that, could you repeat?")

    for k in ["name", "date", "time", "phone", "symptom_message"]:
        if ai.get(k):
            st[k] = ai[k]

    voice_states[cid] = st

    if ai.get("ready_for_booking"):
        final_dt = execute_booking(db, st, db_user_id)
        voice_states[cid] = {}
        msg = final_dt.strftime("%A, %B %d at %I:%M %p UTC")
        return await send_bot(ws, f"Your appointment is confirmed for {msg}!")

    return await send_bot(ws, ai["message"])


# --------------------------------------------
# WEBSOCKET ENDPOINT WITH GOOGLE STT
# --------------------------------------------

@app.websocket("/ws/agent")
async def agent_ws_endpoint(ws: WebSocket):
    await ws.accept()
    print("🎤 Connected")

    cid = id(ws)
    voice_states[cid] = {}

    await send_bot(ws, "Hello! I'm FlossyAI. How can I assist you today?")

    buffer = []

    try:
        while True:
            data = json.loads(await ws.receive_text())

            if data["type"] == "audio_chunk":
                buffer.append(base64.b64decode(data["data"]))

            elif data["type"] == "audio_done":
                transcript = await google_stt_stream(buffer)
                buffer = []

                await ws.send_text(json.dumps({
                    "type": "transcript",
                    "final": True,
                    "text": transcript
                }))

                asyncio.create_task(handle_user_utterance(ws, transcript))

    except WebSocketDisconnect:
        print("🔌 Disconnected")
        voice_states.pop(cid, None)
