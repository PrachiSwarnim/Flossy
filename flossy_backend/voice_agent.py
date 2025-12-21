import logging
import os
from datetime import datetime, timedelta
from typing import Annotated
from dotenv import load_dotenv
import json
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import deepgram, silero, elevenlabs, google
from database import SessionLocal
from models import User, Appointment, Patient
from sqlalchemy import and_

try:
    from rl_core import bandit, ACTIONS, PROMPT_VARIANTS, MODELS
    from utils import embed_with_client
    from llm_client import genai_client
    RL_AVAILABLE = True
except ImportError:
    logger.warning("RL modules not found. Defaulting to static prompt.")
    RL_AVAILABLE = False

load_dotenv()

logger = logging.getLogger("flossy_voice_agent")
logger.setLevel(logging.INFO)

class PhoneNormalizer:
    WORD_TO_DIGIT = {
        'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
        'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'zero': '0'
    }

    @staticmethod
    def normalize(text: str) -> str:
        if not text:
            return ""
        text = text.lower()

        def replace_triple(match):
            digit_word = match.group(1)
            digit = PhoneNormalizer.WORD_TO_DIGIT.get(digit_word, digit_word)
            if digit.isdigit():
                return digit * 3
            return match.group(0)
        
        text = re.sub(r'triple\s+(\w+)', replace_triple, text)
        text = re.sub(r'triple\s+(\d)', lambda m: m.group(1) * 3, text)

        def replace_double(match):
            digit_word = match.group(1)
            digit = PhoneNormalizer.WORD_TO_DIGIT.get(digit_word, digit_word)
            if digit.isdigit():
                return digit * 2
            return match.group(0)
        
        text = re.sub(r'double\s+(\w+)', replace_double, text)
        text = re.sub(r'double\s+(\d)', lambda m: m.group(1) * 2, text)
        
        def replace_single(match):
            digit_word = match.group(1)
            digit = PhoneNormalizer.WORD_TO_DIGIT.get(digit_word, digit_word)
            if digit.isdigit():
                return digit
            return match.group(0)
        
        text = re.sub(r'\b(\w+)\b', replace_single, text)
        text = re.sub(r'\b(\d)\b', lambda m: m.group(1), text)
        
        clean_number = "".join(filter(str.isdigit, text))
        return clean_number
class ReceptionistTools(llm.FunctionContext):
    def __init__(self, action_id: int = None):
        super().__init__()
        self.db = SessionLocal()
        self.action_id = action_id
    
    def __del__(self):
        self.db.close()
    
    @llm.ai_callable(description="Check if a specific date and time is available.")
    async def check_availability(
        self,
        date_str: Annotated[str, llm.TypeInfo(description="Date in YYYY-MM-DD format")],
        time_str: Annotated[str, llm.TypeInfo(description="Time in HH:MM format 24h")]
    ):
        logger.info(f"Checking availability for {date_str} at {time_str}")
        try:
            dt_req = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            slot_end = dt_req + timedelta(minutes=30)

            conflict = self.db.query(Appointment).filter(
                and_(
                    Appointment.datetime >= dt_req,
                    Appointment.datetime <= slot_end,
                    Appointment.status == "scheduled"
                )
            ).first()
            if conflict:
                return "That slot is booked. Ask for another time."
            return "That time slot is available."
        except Exception as e:
            return "I couldn't check the calendar."

    @llm.ai_callable(description="Finalize the booking and save it.")
    async def book_appointment(
        self,
        name: Annotated[str, llm.TypeInfo(description="Patient's full name.")],
        phone: Annotated[str, llm.TypeInfo(description="Patient's phone number.")],
        date_str: Annotated[str, llm.TypeInfo(description="Date in YYYY-MM-DD format")],
        time_str: Annotated[str, llm.TypeInfo(description="Time in HH:MM format 24h")],
        reason: Annotated[str, llm.TypeInfo(description="Reason for the appointment.")],
    ):
        clean_phone = PhoneNormalizer.normalize(phone)
        logger.info(f"Booking: {name} Raw: {phone} -> Clean: {clean_phone}")

        try:
            dt_req = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            dentist = self.db.query(User).filter(User.role == "dentist").first()
            doctor_name = "Dr.Available"

            if dentist:
                doctor_id = dentist.id
                if dentist.email:
                    name_part = dentist.email.split("@")[0].replace(".", " ").title()
                    doctor_name = f"Dr.{name_part}"
            
            patient = self.db.query(Patient).filter(Patient.phone == clean_phone).first()
            if not patient:
                patient = Patient(name=name, phone=clean_phone, contact_datetime=datetime.now())
                self.db.add(patient)
                self.db.commit()
                self.db.refresh(patient)
            
            appointment = Appointment(
                patient_id=patient.id,
                dentist_id=doctor_id,
                reason=reason,
                datetime=dt_req,
                status="scheduled",
                doctor_name=doctor_name,
            )
            self.db.add(appointment)
            self.db.commit()
            self.db.refresh(appointment)

            if "RL_AVAILABLE" in globals() and RL_AVAILABLE and self.action_id is not None:
                try:
                    dummy_ctx = np.zeroes(bandit.d)
                    bandit.update(self.action_id, dummy_ctx, reward=1.0)
                    logger.info(f"RL reward sent for action {self.action_id}")
                except Exception as e:
                    logger.error(f"Failed to update bandit model: {str(e)}")
            friendly_date = dt_req.strftime("%A, %B %d at %I:%M %p")
            return f"Appointment confirmed with {doctor_name} for {friendly_date}."
        except Exception as e:
            logger.error(f"Booking error: {e}")
            return "System error while saving appointment."

def select_system_prompt(user_text: str = ""):
    if not RL_AVAILABLE:
        return SYSTEM_PROMPT, None

    try:
        if user_text:
            emb = np.array(embed_with_client(genai_client, user_text), dtype=float)
        else:
            emb = np.zeros(bandit.d, dtype=float)
        
        if emb.shape[0] != bandit.d:
            emb = np.resize(emb, (bandit.d,))
        
        chosen_action_id, _ = bandit.choose(emb, eps=0.1)

        prompt_idx, _, _, _ = ACTIONS[chosen_action_id]

        selected_prompt = PROMPT_VARIANTS[prompt_idx]
        logger.info(f"Bandit selected actions {chosen_action_id} (Prompt Variant {prompt_idx})")

        return selected_prompt, chosen_action_id
    except Exception as e:
        logger.error(f"RL Selection failed: {e}. using default")
        return SYSTEM_PROMPT, None

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

SYSTEM_PROMPT = """
You are Flossy, the intelligent frontdesk receptionist, for Smile Artists Dental Studio.

**Your Goal:**
1. Greet the patient warmly.
2. Answer questions about pricing or symptoms using your Knowledge Base.
3. Help them book an appointment.

**Booking Rules:**
- ALWAYS check availability (`check_availability`) before confirming a time.
- If the slot is free, use `book_appointment` to save it.
- Ask for the patient's name and phone number if you don't have it.

**Tone:**
- Professional, empathetic, and concise (1-2 sentences).
- Do not make up appointment slots; check the real calendar.

[KNOWLEDGE BASE]
{KNOWLEDGE_BASE}
"""

async def entrypoint(ctx: JobContext):
    user_context_str = ""
    if ctx.job.metadata:
        try:
            meta = json.loads(ctx.job.metadata)
            user_context_str = meta.get("name", "")
        except: pass
    system_prompt, action_id = select_system_prompt(user_context_str)

    fnc_ctx = ReceptionistTools(action_id=action_id)

    initial_ctx = llm.ChatContext().append(
        role="system",
        text=system_prompt
    )

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(api_key=os.getenv["DEEPGRAM_API_KEY"]),
        llm=google.LLM(
            api_key=os.getenv("GOOGLE_API_KEY"),
            model="gemini-2.0-flash-exp"
        ),
        tts=elevenlabs.TTS(
            api_key=os.getenv("ELEVEN_API_KEY"),
            voice=elevenlabs.Voice(
                id=os.getenv("ELEVENLABS_VOICE_ID"),
                name="Flossy",
                category="premade"
            )
        ),
        chat_ctx=initial_ctx,
        fnc_ctx=fnc_ctx
    )

    agent.start(ctx.room, participant=ctx.room.local_participant)

    greeting = "Hello! Smile Artists Dental Studio. I am Flossy."
    if user_context_str:
        greeting=f"Hello {user_context_str}! Welcome to Smile Artists. I am Flossy."
    await agent.say(greeting, allow_interruptions=True)

def prewarm(proc: JobContext):
    proc.userdata["vad"] = silero.VAD.load()

if __name__=="__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))