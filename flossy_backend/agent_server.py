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
from app.core.database import SessionLocal
from app.models import Appointment, Patient, User
from sqlalchemy import and_

# --- RL IMPORTS ---
try:
    from rl_core import bandit, ACTIONS, PROMPT_VARIANTS
    from app.core.utils import embed_with_client
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

voice_states: dict = {}

# -------------------------
# STT (Groq Whisper)
# -------------------------
async def groq_stt(audio_chunks: list) -> str:
    """Uses Groq Whisper for fast, free speech-to-text."""
    from app.services.llm_client import groq_client
    import tempfile
    
    if not groq_client:
        print("❌ Groq client is None!")
        return ""
    
    full_audio = b"".join(audio_chunks)
    if len(full_audio) < 100:
        return ""

    # WebM files need a header (the first ~1kB of the stream) to be valid.
    # We ensure we have a .webm extension so Groq knows how to parse it.
    tmp_path = os.path.join(tempfile.gettempdir(), f"voice_{uuid.uuid4()}.webm")
    try:
        with open(tmp_path, "wb") as f:
            f.write(full_audio)
        
        with open(tmp_path, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                file=("speech.webm", audio_file.read()),
                model="whisper-large-v3",
                response_format="text",
                language="en"
            )
        return str(transcription).strip()
    except Exception as e:
        print(f"❌ Groq STT Error: {e}")
        return ""
    finally:
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass

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
4. **Patient Lookup:** If a user asks to look up a patient or provide details about a patient, use the `lookup_patient` tool.

**Booking Rules:**
- ALWAYS use the `check_availability` tool before confirming a time.
- If the slot is free, use the `book_appointment` tool to save it.
- Ask for the patient's name and phone number if you don't have it.

**Patient Record Rules:**
- If someone asks for a patient record, ask for their name or phone number if not provided.
- Use `lookup_patient` to find the record.
- If multiple records are found, ask for clarification.

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

def lookup_patient(query: str):
    """Looks up a patient by name or phone number."""
    print(f"🔎 Looking up patient: {query}")
    db = SessionLocal()
    try:
        # Simple ilike search on name or phone
        patients = db.query(Patient).filter(
            (Patient.name.ilike(f"%{query}%")) | 
            (Patient.phone.ilike(f"%{query}%"))
        ).all()
        
        if not patients:
            return "No patient found with that name or phone number."
        
        res = []
        for p in patients:
            res.append(f"Name: {p.name}, Phone: {p.phone}, Age: {p.age or 'N/A'}")
        
        return "\n".join(res)
    except Exception as e:
        return f"Error looking up patient: {e}"
    finally:
        db.close()

# List of tools for Gemini
my_tools = [check_availability, book_appointment, lookup_patient]

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

async def send_bot(ws: WebSocket, text: str):
    """Sends text to frontend and streams TTS audio via WebSocket."""
    # 1. Update Status
    await ws.send_json({"type": "status", "content": "Speaking..."})
    
    # 2. Send Text (Subtitles)
    await ws.send_json({"type": "text", "content": text})
    
    # 3. Generate and Stream Audio
    try:
        from app.services.tts import stream_text_to_speech
        print(f"🎙️ Streaming TTS for: {text[:30]}...")
        for chunk in stream_text_to_speech(text):
            if chunk:
                await ws.send_bytes(chunk)
    except Exception as e:
        print(f"❌ TTS Streaming Error: {e}")
    
    # 4. Back to Listening
    await ws.send_json({"type": "status", "content": "Listening..."})

async def process_conversation_turn(text: str, st: dict, mode: str = "VOICE", ws: WebSocket = None):
    """Handles one turn of conversation using Gemini with Tools, with Groq fallback."""
    from app.services.llm_client import genai_client, groq_client
    from app.core.utils import ai_generate

    if ws:
        await ws.send_json({"type": "status", "content": "Thinking..."})
    
    # 1. Select Prompt
    system_prompt, action_id = select_prompt(text)
    
    # 2. Call Gemini
    try:
        chat = genai_client.chats.create(
            model="gemini-2.0-flash-001",
            config=types.GenerateContentConfig(
                tools=my_tools, 
                system_instruction=system_prompt
            )
        )
        response = chat.send_message(text)
        ai_reply = response.text or "I'm checking..."
        
        if "booked" in ai_reply.lower() and action_id:
            reward_rl(action_id)
            
        st["last_ai_reply"] = ai_reply
        return ai_reply, st

    except Exception as e:
        err_msg = str(e)
        if "RESOURCE_EXHAUSTED" in err_msg or "429" in err_msg:
             print("⚠️ Gemini Rate Limit Hit. Falling back to Groq/Llama...")
             fallback_prompt = f"{system_prompt}\n\nUSER MESSAGE: {text}\n\nREPLY CONCISELY:"
             ai_reply = ai_generate(fallback_prompt)
             return ai_reply, st
        
        print(f"❌ Gemini Error: {e}")
        return "I'm sorry, I'm having trouble thinking right now.", st

# -------------------------
# WEBSOCKET ENDPOINT (The "Orb" Connector)
# -------------------------
# In flossy_backend/agent_server.py

@app.websocket("/ws/agent")
async def agent_ws_endpoint(ws: WebSocket):
    await ws.accept()
    cid = f"{ws.client.host}:{ws.client.port}"
    print(f"INFO: {cid} - 'WebSocket /ws/agent' [accepted]")
    
    voice_states[cid] = {}
    
    # 1. Send Initial Greeting and Connection Status
    await ws.send_json({"type": "status", "content": "Connected"})
    
    greeting = "Hello! I'm Flossy, your dental assistant from Smile Artists Dental Studio. How can I help you today?"
    await send_bot(ws, greeting)
    
    # Audio buffer and persistent webm header
    audio_buffer = bytearray()
    webm_header = None
    
    # COUNTER: We will try to process audio every ~10 chunks (approx 2-3 seconds)
    chunk_count = 0
    PROCESS_EVERY_N_CHUNKS = 10 

    try:
        while True:
            # 2. Receive Data
            message = await ws.receive()

            # --- CASE A: BINARY AUDIO ---
            if "bytes" in message:
                chunk = message["bytes"]
                audio_buffer.extend(chunk)
                
                # Capture the very first chunk's start as the WebM header 
                # Wait until we have a substantial chunk to be sure it's the header
                if webm_header is None and len(audio_buffer) >= 1000:
                    webm_header = bytes(audio_buffer[:1000])
                    print(f"💾 Captured WebM Header ({len(webm_header)} bytes)")
                
                chunk_count += 1
                
                # 3. CHECKPOINT: Process audio
                if chunk_count >= PROCESS_EVERY_N_CHUNKS:
                    if webm_header is None:
                        # Safety fallback if we haven't hit 1000 bytes yet
                        audio_buffer.clear()
                        chunk_count = 0
                        continue

                    # Prepend ONLY the pure header to the accumulated buffer
                    to_process = webm_header + bytes(audio_buffer)
                    
                    # Log size but skip if too small
                    if len(audio_buffer) > 2000:
                        print(f"👂 Processing {len(to_process)} bytes of speech...")
                        transcript = await groq_stt([to_process])
                        
                        # 4. DID THE USER SPEAK?
                        if transcript and transcript.strip() and len(transcript) > 2:
                            # MODERATED Filter: Only block obvious non-speech noise
                            lower_transcript = transcript.lower().strip().strip(".,?!")
                            hallucinations = [
                                "thanks for watching", "subtitle by", "like and subscribe", 
                                "the end", "thanks for your time", "watching"
                            ]
                            
                            is_hallucination = any(h in lower_transcript for h in hallucinations)
                            
                            # If it's very short and looks like garbage, filter it
                            if len(lower_transcript) < 3 and lower_transcript not in ["hi", "no", "yes"]:
                                is_hallucination = True

                            if is_hallucination:
                                print(f"🚫 Filtered Noise: {transcript}")
                            else:
                                print(f"🗣️ User Said: {transcript}")
                                await ws.send_json({"type": "text", "content": f"You: {transcript}"})
                                
                                # Get AI Response
                                response_text, new_state = await process_conversation_turn(
                                    text=transcript, 
                                    st=voice_states.get(cid, {}),
                                    mode="VOICE",
                                    ws=ws
                                )
                                voice_states[cid] = new_state
                                
                                # Speak Response
                                print(f"🤖 Flossy Replying: {response_text}")
                                await send_bot(ws, response_text)
                    
                    # Reset buffer. We KEEP the webm_header for the next window.
                    audio_buffer.clear()
                    chunk_count = 0

            # --- CASE B: TEXT JSON ---
            elif "text" in message:
                try:
                    data = json.loads(message["text"])
                    if data.get("type") == "transcript":
                         # Handle manual text input if needed
                         pass
                except: pass

    except WebSocketDisconnect:
        print("INFO: Client disconnected")
        voice_states.pop(cid, None)
    except Exception as e:
        # Ignore the "receive after disconnect" error
        if "disconnect" not in str(e).lower():
            print(f"❌ Error: {e}")
        try:
            await ws.close()
        except: pass