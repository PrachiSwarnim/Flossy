"""
LiveKit Voice Agent - Flossy Clinical AI
=======================================
Implementation of the Hands-Free Dentist Assistant.
Replaced older implementation to follow the AgentSession pattern 
and resolve import errors.
"""

import logging
import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Database & Models
from database import SessionLocal
from models import Appointment, Patient, User, Interaction, Prescription
from sqlalchemy import and_

# LiveKit & Agents
from livekit import agents, rtc
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RoomOutputOptions,
    RunContext,
    WorkerOptions,
    cli,
    mcp
)
# Specialized Dental Plugins
from livekit.plugins import google, elevenlabs, deepgram, silero, openai
from livekit.agents.llm import function_tool
# from livekit.rtc import AutoSubscribe

import asyncio
import socket

# Force IPv6 preference
asyncio.get_event_loop_policy().get_event_loop()

# Explicitly allow IPv6
socket.setdefaulttimeout(20)

from aiohttp import ClientSession, TCPConnector
import socket

connector = TCPConnector(
    family=socket.AF_INET6,   # 👈 force IPv6
    ssl=True,
    ttl_dns_cache=300,
)

session = ClientSession(connector=connector)

from livekit.agents import WorkerOptions, Worker

Worker.run(
    WorkerOptions(
        ws_url="wss://flossy-pmhj3sdw.livekit.cloud",
        api_key=os.environ["LIVEKIT_API_KEY"],
        api_secret=os.environ["LIVEKIT_API_SECRET"],
        http_session=session,  # 👈 THIS
    )
)

# Load environment variables
load_dotenv(".env")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- UTILS ---
class PhoneNormalizer:
    @staticmethod
    def normalize(text: str) -> str:
        """Strips all non-digit characters for database consistency."""
        if not text: return ""
        return "".join(filter(str.isdigit, text))

# --- DENTAL KNOWLEDGE BASE ---
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

def prewarm(proc: JobProcess):
    """Pre-loads the VAD model to the worker process memory."""
    proc.userdata["vad"] = silero.VAD.load()

class FlossyAssistant(Agent):
    """Dental Assistant for Smile Artists Dental Studio."""
    
    def __init__(self):
        self.broadcast_callback = None
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        super().__init__(
            instructions=f"""You are Flossy, the Clinical & Frontdesk Assistant for Smile Artists Dental Studio.
            Today's date is {current_date}.

            **Your Dual Roles:**
            
            1. **For Patients (Receptionist):**
               - Greet warmly, answer pricing/symptom questions using [KNOWLEDGE BASE].
               - Gather Name, Phone, and Reason to book appointments.
               - ALWAYS use `check_availability` before `book_appointment`.

            2. **For Dentists (Clinical Assistant):**
               - Help dentists during procedures hands-free.
               - **Query History:** Use `get_patient_summary` to read back previous visit reasons or medications.
               - **Charting:** Use `record_clinical_note` to dictate observations or procedure notes.
               - **Prescriptions:** Use `create_prescription_voice` when a dentist dictates a prescription.

            **Tone:**
            - Calm, professional, and efficient.
            - Keep responses short (1-2 sentences) so the dentist can keep working.

            [KNOWLEDGE BASE]
            {KNOWLEDGE_BASE}"""
        )

    async def on_enter(self):
        logger.info("📡 Flossy session started")

        self.session.generate_reply(
            instructions=(
                "Greet the patient or dentist warmly and ask how "
                "Smile Artists Dental Studio can help them today."
            )
        )

    @function_tool
    async def check_availability(self, context: RunContext, date_str: str, time_str: str) -> str:
        """Checks if a dentist appointment slot is available. Format: YYYY-MM-DD HH:MM"""
        logger.info(f"🔎 Checking slot: {date_str} {time_str}")
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
            return "That slot is already booked. Please ask for another time." if conflict else "That slot is available."
        except Exception as e:
            logger.error(f"Availability check error: {e}")
            return "I'm having trouble checking the calendar right now."
        finally:
            db.close()

    @function_tool
    async def book_appointment(self, context: RunContext, name: str, phone: str, date_str: str, time_str: str, reason: str) -> str:
        """Books the dental appointment into the database."""
        clean_phone = PhoneNormalizer.normalize(phone)
        if len(clean_phone) < 10:
            return "The phone number seems incomplete. Could you please provide the full 10-digit number?"

        db = SessionLocal()
        try:
            dt_req = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            dentist = db.query(User).filter(User.role == "dentist").first()
            doctor_name = "Dr. Available"
            if dentist and dentist.email:
                doctor_name = f"Dr. {dentist.email.split('@')[0].title().replace('.', ' ')}"
            
            patient = db.query(Patient).filter(Patient.phone == clean_phone).first()
            if not patient:
                patient = Patient(name=name, phone=clean_phone, contact_datetime=datetime.now(), source="voice")
                db.add(patient)
                db.commit()
                db.refresh(patient)
            
            appt = Appointment(
                patient_id=patient.id,
                doctor_id=dentist.id if dentist else None,
                datetime=dt_req,
                status="scheduled",
                doctor_name=doctor_name,
                reason=reason
            )
            db.add(appt)
            db.commit()

            if self.broadcast_callback:
                await self.broadcast_callback("REFRESH_DASHBOARD")
            
            friendly_time = dt_req.strftime("%A, %B %d at %I:%M %p")
            return f"Perfect, {name}. I've successfully scheduled your appointment for {reason} on {friendly_time}."
        except Exception as e:
            logger.error(f"Booking error: {e}")
            return "I encountered an error while trying to save the appointment."
        finally:
            db.close()

    @function_tool
    async def get_patient_summary(self, context: RunContext, patient_name: str) -> str:
        """Retrieves a summary of the patient's history."""
        logger.info(f"🔍 Fetching summary for: {patient_name}")
        db = SessionLocal()
        try:
            patient = db.query(Patient).filter(Patient.name.ilike(f"%{patient_name}%")).first()
            if not patient:
                return f"I couldn't find a record for a patient named {patient_name}."
            
            last_appt = db.query(Appointment).filter(Appointment.patient_id == patient.id, Appointment.status == "completed").order_by(Appointment.datetime.desc()).first()
            prescriptions = db.query(Prescription).filter(Prescription.patient_id == patient.id).limit(3).all()
            
            summary = f"Summary for {patient.name}: "
            if last_appt:
                summary += f"Last visit was on {last_appt.datetime.strftime('%Y-%m-%d')} for {last_appt.reason}. "
            
            if prescriptions:
                meds = ", ".join([p.details for p in prescriptions])
                summary += f"Recent prescriptions: {meds}."
            return summary
        except Exception as e:
            logger.error(f"Summary fetch error: {e}")
            return "I'm having trouble accessing the medical records."
        finally:
            db.close()

    @function_tool
    async def record_clinical_note(self, context: RunContext, patient_name: str, note: str) -> str:
        """Saves a clinical note for a patient dictated by the dentist."""
        db = SessionLocal()
        try:
            patient = db.query(Patient).filter(Patient.name.ilike(f"%{patient_name}%")).first()
            if not patient:
                return f"I couldn't find a patient named {patient_name} to save this note for."
            
            new_interaction = Interaction(
                patient_id=patient.id,
                channel="voice_note",
                message=f"Clinical Dictation: {note}",
                created_at=datetime.now()
            )
            db.add(new_interaction)
            db.commit()

            if self.broadcast_callback:
                await self.broadcast_callback("REFRESH_DASHBOARD")

            return f"Note recorded for {patient.name}: '{note}'"
        except Exception as e:
            logger.error(f"Note recording error: {e}")
            return "I failed to save that note."
        finally:
            db.close()

    @function_tool
    async def create_prescription_voice(self, context: RunContext, patient_name: str, med_details: str) -> str:
        """Drafts a medical prescription dictated by the dentist."""
        db = SessionLocal()
        try:
            patient = db.query(Patient).filter(Patient.name.ilike(f"%{patient_name}%")).first()
            if not patient:
                return f"I couldn't find a patient named {patient_name} to issue a prescription."
            
            dentist = db.query(User).filter(User.role == "dentist").first()
            new_presc = Prescription(
                patient_id=patient.id,
                doctor_id=dentist.id if dentist else None,
                details=med_details,
                created_at=datetime.now()
            )
            db.add(new_presc)
            db.commit()

            if self.broadcast_callback:
                await self.broadcast_callback("REFRESH_DASHBOARD")

            return f"Prescription for {med_details} has been drafted for {patient.name}."
        except Exception as e:
            logger.error(f"Prescription creation error: {e}")
            return "I ran into an issue while drafting the prescription."
        finally:
            db.close()


async def entrypoint(ctx: agents.JobContext):
    """Main execution loop for the LiveKit Worker."""
    logger.info(f"Agent starting in room: {ctx.room.name}")

    assistant_instance = FlossyAssistant()

    async def broadcast(msg: str):
        # logger.info(f"📡 Broadcasting to room: {msg}")
        await ctx.room.local_participant.publish_data(msg.encode("utf-8"))

    assistant_instance.broadcast_callback = broadcast

    session = AgentSession(
        stt=deepgram.STT(model="nova-2", language="en"),
        llm=openai.LLM(
            model="llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
            temperature=0.3,
        ),
        tts=elevenlabs.TTS(
            api_key=os.getenv("ELEVEN_API_KEY"),
            voice_id=os.getenv("ELEVENLABS_VOICE_ID"),
            model="eleven_flash_v2",
        ),

        vad=silero.VAD.load(),
        turn_detection=None,
        mcp_servers=[mcp.MCPServerHTTP(url="http://localhost:8000/mcp")],
    )

    # --- Session Events ---
    @session.on("agent_state_changed")
    def on_state_changed(ev):
        logger.info(f"State: {ev.old_state} -> {ev.new_state}")
    
    @session.on("user_started_speaking")
    def on_user_speaking():
        logger.debug("User started speaking")
    
    @session.on("user_stopped_speaking")
    def on_user_stopped():
        logger.debug("User stopped speaking")

    await session.start(
        room=ctx.room,
        agent=assistant_instance,
        room_output_options=RoomOutputOptions(transcription_enabled=True),
    )

    logger.info("✅ Agent running")

    # Keep the agent alive while connected
    while ctx.room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
        await asyncio.sleep(1)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
