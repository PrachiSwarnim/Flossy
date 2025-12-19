import os
import json
import asyncio
from datetime import datetime, timedelta
import dateutil.parser
from dotenv import load_dotenv

from livekit import agents, rtc
from livekit.agents import AgentServer, AgentSession, Agent, room_io, mcp
from livekit.plugins import openai, noise_cancellation, tavus
from livekit.agents.llm import FunctionContext, ai_callable

from database import SessionLocal
from models import User, Patient, Appointment

load_dotenv(".env.local")

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
                
                await self.room.local_participant.publish_data(b"APPOINTMENT_BOOKED")
                return "Success! Appointment confirmed."
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"Booking error: {e}")
            return "Sorry, booking failed. Please try again."

class FlossyAssistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=f"""You are FlossyAI, a dental receptionist at Smile Artists Dental Studio.

KNOWLEDGE BASE:
{KNOWLEDGE_BASE}

RULES:
1. Be warm, professional, and concise
2. Answer questions using the knowledge base
3. For booking: collect date, time, phone, reason
4. Once you have all details, call book_appointment tool
5. After successful booking, say "All set! Your appointment is booked."
""",
        )

server = AgentServer()

@server.rtc_session()
async def my_agent(ctx: agents.JobContext):
    # Connect and get participant info
    await ctx.connect(auto_subscribe=agents.AutoSubscribe.AUDIO_ONLY)
    print("📞 Connected to LiveKit")
    
    participant = await ctx.wait_for_participant()
    metadata = json.loads(participant.metadata) if participant.metadata else {}
    email = metadata.get("email")
    user_name = participant.name or "Guest"
    
    print(f"👤 User: {user_name} ({email})")
    
    # Setup function context if user is authenticated
    fnc_ctx = AssistantFnc(ctx.room, participant) if email else None
    
    # Create session with OpenAI Realtime model and MCP servers
    mcp_url = os.getenv("N8N_MCP_SERVER_URL") or os.getenv("N8N_MCP_URL")
    mcp_servers = []
    if mcp_url:
        print(f"🔗 Connecting to MCP Server: {mcp_url}")
        mcp_servers.append(mcp.MCPServerHTTP(url=mcp_url))

    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            voice="coral",
            instructions=f"""You are FlossyAI, a dental receptionist at Smile Artists Dental Studio.

KNOWLEDGE BASE:
{KNOWLEDGE_BASE}

RULES:
1. Be warm, professional, and concise
2. Answer questions using the knowledge base
3. For booking: collect date, time, phone, reason
4. Once you have all details, call book_appointment tool
5. After successful booking, say "All set! Your appointment is booked."
6. You also have access to external tools via MCP (like Google Calendar). Use them if requested.
"""
        ),
        fnc_ctx=fnc_ctx,
        mcp_servers=mcp_servers,
    )
    
    # Initialize Tavus Avatar if credentials are provided
    replica_id = os.getenv("REPLICA_ID")
    persona_id = os.getenv("PERSONA_ID")
    tavus_api_key = os.getenv("TAVUS_API_KEY")

    if replica_id and persona_id and tavus_api_key:
        print(f"🎭 Starting Tavus Avatar: {replica_id}")
        avatar = tavus.AvatarSession(
            replica_id=replica_id,
            persona_id=persona_id,
            api_key=tavus_api_key,
        )
        await avatar.start(session, room=ctx.room)
    else:
        print("⚠️ Tavus credentials missing. Running voice-only.")

    await session.start(
        room=ctx.room,
        agent=FlossyAssistant(),
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony()
                if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                else noise_cancellation.BVC(),
            ),
        ),
    )
    
    # Generate greeting
    await session.generate_reply(
        instructions=f"Greet the user by name ({user_name}) and offer your assistance. Start by speaking in English."
    )
    
    print("✅ Assistant started")

if __name__ == "__main__":
    agents.cli.run_app(server)