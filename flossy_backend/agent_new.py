import os
import json
import asyncio
from datetime import datetime, timedelta
import dateutil.parser
from dotenv import load_dotenv

from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.voice import VoiceAssistant
from livekit.agents.llm import FunctionContext, ai_callable

from livekit.plugins import deepgram, openai, silero
from database import SessionLocal
from models import User, Patient, Appointment

load_dotenv()

# Knowledge Base
KNOWLEDGE_BASE = """
[PRICING]
- Routine Check-up: ₹500
- Scaling & Cleaning: ₹1,500+
- Dental Implants: ₹25,000+
- Root Canal: ₹4,000-8,000
- Braces/Invisalign: ₹35,000+

[POST-OP CARE]
- No vigorous rinsing for 24 hours
- Apply ice for swelling
- Soft diet for 24 hours

[SYMPTOMS]
- Toothache: Rinse with salt water, book ASAP
- Bleeding Gums: Book cleaning
- Knocked-out Tooth: Keep in milk, come within 1 hour
"""

SYSTEM_PROMPT = f"""You are FlossyAI, a dental receptionist at Smile Artists Dental Studio.

KNOWLEDGE BASE:
{KNOWLEDGE_BASE}

RULES:
1. Be warm, professional, and concise
2. Answer questions using the knowledge base
3. For booking: collect date, time, phone, reason
4. Once you have all details, call book_appointment tool
5. After successful booking, say "All set! Your appointment is booked."
"""

# Booking Tool
class AssistantFnc(FunctionContext):
    def __init__(self, room, participant):
        super().__init__()
        self.room = room
        self.participant = participant

    @ai_callable(description="Book appointment with date, time, phone, reason")
    async def book_appointment(self, date: str, time: str, phone: str, reason: str):
        print(f"🔧 Booking: {date} {time} - {reason}")
        
        try:
            metadata = json.loads(self.participant.metadata) if self.participant.metadata else {}
            email = metadata.get("email")
            
            if not email:
                return "Please sign up first to book appointments."
            
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.email == email).first()
                if not user:
                    return "User not found."
                
                patient = db.query(Patient).filter(Patient.user_id == user.id).first()
                if not patient:
                    return "Patient profile not found."
                
                # Parse datetime
                try:
                    dt_str = f"{date} {time}"
                    appt_dt = dateutil.parser.parse(dt_str)
                except:
                    appt_dt = datetime.now() + timedelta(days=1)
                
                # Create appointment
                appt = Appointment(
                    patient_id=patient.id,
                    datetime=appt_dt,
                    status="scheduled",
                    doctor_name="Dr. Smith",
                    reason=reason
                )
                db.add(appt)
                db.commit()
                
                await self.room.local_participant.publish_data("APPOINTMENT_BOOKED")
                return "Success! Appointment confirmed."
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"Booking error: {e}")
            return "Sorry, booking failed. Please try again."

# Main entrypoint
async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    print("📞 Connected to LiveKit")
    
    participant = await ctx.wait_for_participant()
    metadata = json.loads(participant.metadata) if participant.metadata else {}
    email = metadata.get("email")
    user_name = participant.name or "Guest"
    
    print(f"👤 User: {user_name} ({email})")
    
    # Setup tools
    fnc_ctx = AssistantFnc(ctx.room, participant) if email else None
    
    # Create assistant (simplified pattern like AssemblyAI example)
    assistant = VoiceAssistant(
        vad=silero.VAD.load(),
        stt=deepgram.STT(),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=deepgram.TTS(),
        chat_ctx=llm.ChatContext(messages=[
            llm.ChatMessage(role="system", content=SYSTEM_PROMPT)
        ]),
        fnc_ctx=fnc_ctx
    )
    
    assistant.start(ctx.room, participant)
    
    # Greeting
    greeting = f"Hi {user_name}! I'm Flossy, your dental assistant. How can I help you today?"
    await assistant.say(greeting, allow_interruptions=True)
    
    print("✅ Assistant started")

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))