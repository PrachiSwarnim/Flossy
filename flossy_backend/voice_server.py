import os
import json
import base64
import asyncio
import numpy as np
import uuid
import logging

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv

# --- CLIENT IMPORTS ---
from google.genai import Client, types  # Native Gemini SDK
from google.cloud import speech
from google.oauth2 import service_account

# --- DATABASE IMPORTS ---
from database import SessionLocal
from models import Appointment, Patient, User
from sqlalchemy import and_

# --- RL IMPORTS ---
try:
    from rl_core import bandit, ACTIONS, PROMPT_VARIANTS
    from utils import embed_with_client
    RL_AVAILABLE = True
except ImportError:
    logging.warning("⚠️ RL modules not found. Defaulting to static prompt.")
    RL_AVAILABLE = False

load_dotenv()
app = FastAPI()

# -------------------------
# CONFIG & CLIENTS
# -------------------------
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
gemini_client = Client(api_key=GEMINI_API_KEY)

# STT Config (Google Speech or Groq)
cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
if os.path.exists(cred_path):
    gcp_credentials = service_account.Credentials.from_service_account_file(cred_path)
    speech_client = speech.SpeechClient(credentials=gcp_credentials)
else:
    speech_client = None

# -------------------------
# KNOWLEDGE BASE & SYSTEM PROMPT
# -------------------------
KNOWLEDGE_BASE = """
[PRICING]
- Routine Check-Up: Rs. 500
- Scaling and Cleaning: starts at Rs. 1500
- Dental Implants: starts at Rs. 25000
- Root Canal Treatment: Rs. 4000 - Rs. 8000
- Braces/Invisalign: Starts at Rs. 35, 000

[SYMPTOMS]
- Toothache: Rinse with warm salt water, avoid sugary and acidic foods.
- Swollen gums: Gently brush and floss, use warm salt water rinse.
- Bleeding gums: Gently brush and floss, use warm salt water rinse.
- Bad breath: Brush and floss regularly, use mouthwash.
- Tooth sensitivity: Avoid sugary and acidic foods, use fluoride toothpaste.
- Jaw pain: Gently brush and floss, use warm salt water rinse.

[PREVENTIVE CARE]
- Brush teeth at least twice a day.
- Floss daily.
- Use mouthwash.
- Visit dentist every 6 months.
- Avoid sugary and acidic foods.
- Use fluoride toothpaste.

[DIAGNOSIS]
- Toothache: Tooth decay, gum disease, tooth fracture.
- Swollen gums: Gum disease, tooth decay, tooth infection.
- Bleeding gums: Gum disease, tooth decay, tooth infection.
- Bad breath: Tooth decay, gum disease, tooth infection.
- Tooth sensitivity: Tooth decay, gum disease, tooth infection.
- Jaw pain: Jaw fracture, tooth decay, gum disease.
"""

SYSTEM_PROMPT_DEFAULT = f"""
You are Flossy, the intelligent frontdesk receptionist for Smile Artists Dental Studio.

**Your Goal:**
1. Greet the patient warmly.
2. Answer questions about pricing or symptoms using your Knowledge Base.
3. Help them book an appointment.

**Booking Rules:**
- ALWAYS use the `check_availability` tool before confirming a time.
- If the slot is free, use the `book_appointment` tool to save it.
- Ask for the patient's name and phone number if you don't have it.

**Tone:**
- Professional, empathetic, and concise (1-2 sentences).
- Do not make up appointment slots; check the real calendar.

[KNOWLEDGE BASE]
{KNOWLEDGE_BASE}
"""

# -------------------------
# DATABASE TOOLS
# -------------------------
class PhoneNormalizer:
    @staticmethod
    def normalize(text: str) -> str:
        if not text: return ""
        return "".join(filter(str.isdigit, text))

def check_availability(date_str: str, time_str: str):
    """Checks if a dentist appointment slot is available. Format: YYYY-MM-DD HH:MM"""
    print(f"🔎 Checking: {date_str} {time_str}")
    db = SessionLocal()
    try:
        dt_req = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        slot_end = dt_req + timedelta(minutes=30)
        conflict = db.query(Appointment).filter(
            and_(
                Appointment.datetime >= dt_req,
                Appointment.datetime < slot_end,
                Appointment.status == "scheduled"
            )
        ).first()
        return "That slot is booked." if conflict else "That slot is available."
    except Exception as e:
        return f"Error checking slot: {e}"
    finally:
        db.close()

def book_appointment(name: str, phone: str, date_str: str, time_str: str, reason: str):
    """Books a dentist appointment."""
    clean_phone = PhoneNormalizer.normalize(phone)
    print(f"📝 Booking: {name} on {date_str} at {time_str}")
    db = SessionLocal()
    try:
        dt_req = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        dentist = db.query(User).filter(User.role == "dentist").first()
        doctor_name = "Dr. Available"
        
        patient = db.query(Patient).filter(Patient.phone == clean_phone).first()
        if not patient:
            patient = Patient(name=name, phone=clean_phone, contact_datetime=datetime.now())
            db.add(patient); db.commit(); db.refresh(patient)
            
        appt = Appointment(
            patient_id=patient.id, 
            doctor_id=dentist.id if dentist else None,
            datetime=dt_req, status="scheduled", doctor_name=doctor_name, reason=reason
        )
        db.add(appt); db.commit()
        return f"Booked for {dt_req.strftime('%A at %I:%M %p')}."
    except Exception as e:
        return f"Booking Error: {str(e)}"
    finally:
        db.close()

# List of tools for Gemini
my_tools = [check_availability, book_appointment]

# -------------------------
# RL & PROMPT LOGIC
# -------------------------
def select_prompt(user_text: str = ""):
    if not RL_AVAILABLE: return SYSTEM_PROMPT_DEFAULT, None
    try:
        emb = np.resize(np.array(embed_with_client(gemini_client, user_text or ""), dtype=float), (bandit.d,))
        cid, _ = bandit.choose(emb, eps=0.1)
        base = PROMPT_VARIANTS[ACTIONS[cid][0]]
        return f"{base}\n\n{KNOWLEDGE_BASE}", cid
    except: return SYSTEM_PROMPT_DEFAULT, None

def reward_rl(action_id):
    if RL_AVAILABLE and action_id: bandit.update(action_id, np.zeros(bandit.d), reward=1.0)

# -------------------------
# HELPER: GOOGLE STT
# -------------------------
async def google_stt_stream(audio_chunks):
    if not speech_client: return ""
    content = b"".join(audio_chunks)
    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=48000, # Adjust to match your mic/frontend
        language_code="en-US"
    )
    try:
        response = speech_client.recognize(config=config, audio=audio)
        if response.results:
            return response.results[0].alternatives[0].transcript
    except Exception as e:
        print(f"STT Error: {e}")
    return ""

# -------------------------
# WEBSOCKET ENDPOINT (The "Orb" Connector)
# -------------------------
@app.websocket("/ws/agent")
async def agent_ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(f"INFO: {websocket.client.host} - 'WebSocket /ws/agent' [accepted]")

    # 1. Send Initial Greeting
    await websocket.send_json({"type": "text", "content": "Hello! I'm Flossy. How can I help?"})

    # Buffer for audio chunks
    audio_buffer = []

    try:
        while True:
            # 2. Receive Message (Audio Bytes or Text)
            message = await websocket.receive()

            # --- CASE A: AUDIO STREAM ---
            if "bytes" in message:
                # In a real app, you'd stream this to Google STT. 
                # For simplicity here, we assume the frontend sends text or we accumulate.
                # If you use the MediaRecorder frontend, you might need a proper streaming STT service here.
                # For now, let's print size to confirm connection.
                # print(f"🎤 Received {len(message['bytes'])} bytes")
                pass

            # --- CASE B: TEXT COMMANDS (from STT or UI) ---
            elif "text" in message:
                try:
                    data = json.loads(message["text"])
                    
                    # If frontend sends a transcript (e.g. from browser built-in STT)
                    if data.get("type") == "transcript" or data.get("text"):
                        user_text = data.get("text")
                        print(f"🗣️ User: {user_text}")

                        # 1. Select Prompt (RL)
                        system_prompt, action_id = select_prompt(user_text)

                        # 2. Call Gemini with Tools
                        # We use a persistent chat session would be better, but one-off for now
                        chat = gemini_client.chats.create(
                            model="gemini-2.0-flash-exp",
                            config=types.GenerateContentConfig(
                                tools=my_tools, 
                                system_instruction=system_prompt
                            )
                        )
                        response = chat.send_message(user_text)
                        
                        # 3. Handle Function Calls (Automatic in Gemini SDK usually, but let's be safe)
                        # If Gemini returns text:
                        ai_reply = response.text or "I'm checking..."
                        
                        # Note: The native SDK handles tool execution automatically if configured,
                        # but often you need to loop it. For this snippet, we assume simple text response.
                        # If response has function calls, the SDK 'automatic_function_calling' feature helps.
                        
                        print(f"🤖 Flossy: {ai_reply}")

                        # 4. Send back to Frontend
                        await websocket.send_json({"type": "text", "content": ai_reply})

                        # 5. Reward RL
                        if "booked" in ai_reply.lower() and action_id:
                            reward_rl(action_id)

                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        print("INFO: Client disconnected")
    except Exception as e:
        print(f"❌ Error: {e}")
        try:
            await websocket.close()
        except: pass