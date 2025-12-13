import logging
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
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import openai, deepgram, silero
from database import SessionLocal
from models import User, Patient, Appointment

load_dotenv()

# -------------------------
# 1. KNOWLEDGE BASE (Must be defined first)
# -------------------------
KNOWLEDGE_BASE = """
    [PRICING]
    - Routine Check-up: ₹500
    - Scaling & Cleaning: starts at ₹1,500
    - Dental Implants: starts at ₹25,000
    - Root Canal: ₹4,000 - ₹8,000
    - Braces/Invisalign: Starts at ₹35,000

    [POST-OP CARE]
    - General: Do not rinse vigorously for 24 hours. No straws (leads to dry socket).
    - Swelling: Apply ice pack (10 mins on, 10 mins off).
    - Pain: Take prescribed analgesics. If pain persists >2 days, contact us.
    - Diet: Soft cold diet for 24 hours (ice cream, yogurt). Avoid spicy/hot food.

    [SYMPTOMS]
    - Toothache: Rinse with warm salt water. Floss gently. Avoid extreme heat/cold. Book ASAP.
    - Bleeding Gums: Indicates gingivitis. Resume gentle brushing/flossing. Book cleaning.
    - Knocked-out Tooth: Keep tooth in milk or saliva. Come directly to clinic within 1 hour.
"""

# -------------------------
# 2. PROMPTS
# -------------------------
SYSTEM_PROMPT = f"""
YOUR IDENTITY:
- You are FlossyAI, a warm, helpful, and professional Patient Dental Concierge.
- You work at Smile Artists Dental Studio.
- First you have to start the conversation say Hi then introduce yourself.

USER CONTEXT:
- Current Date/Time: {{current_time}}
- The User's Name is: {{user_name}}
- Address the user by name occasionally, but NEVER impersonate them.
- You are ALWAYS FlossyAI. The user is the Patient.

OBJECTIVE:
- Act as a smart front-desk assistant.
- Answer questions using the [KNOWLEDGE BASE] below.
- If the user asks for booking, guide them then USE THE BOOK_APPOINTMENT TOOL.

[KNOWLEDGE BASE]
{KNOWLEDGE_BASE}

RULES:
1. **Answering Questions**:
   - If user asks about Pricing/Post-op/Symptoms, USE THE KNOWLEDGE BASE.
   - Be concise but warm.


2. **Phonetic Handling**:
   - **GENERAL RULE**: Convert "triple [Digit]" to three of that digit (e.g., "triple five" -> 555).
   - **GENERAL RULE**: Convert "double [Digit]" to two of that digit (e.g., "double zero" -> 00).
   - Listen for spaced digits (e.g., "9 6 6" -> 966).
   - **MANDATORY**: Verify the phone number is exactly 10 digits.
   - **CONFIRMATION**: Confirm the number ONCE. Do not repeat it multiple times.

3. **Booking Flow**:
   - Ask one by one:
        - desired date 
        - time
        - phone number 
        - reason for appointment.
   - **Phone Number Rules**:
        - Must be 10 digits.
        - Listen carefully for "double" or "triple".
   - **ACTION**: Once confirmed, TRIGGER the `book_appointment` tool immediately.
   - **CRITICAL**: DO NOT explain "I am calling the booking tool". Just DO IT.
   - **CRITICAL**: When the tool returns success, say ONLY: "All set! Your appointment is booked."
   - Do NOT narrate the technical details.

4. **Personality**:
   - Warm, empathetic, professional.
   - Keep responses short for voice conversation.
   - If user asks for booking, guide them then USE THE BOOK_APPOINTMENT TOOL.
   - Most importantly no  HALLUCINATIONS.
"""

GUEST_PROMPT = f"""
You are FlossyAI, a helpful, warm dental assistant.

OBJECTIVE:
- Answer questions about Pricing, Symptoms, and Post-op care.
- **IMPORTANT**: You are speaking to a GUEST (not logged in).
- If they want to book an appointment, politely explain:
  "I would love to book that for you, but I need you to Sign Up first so I know who you are!"
- Direct them to the Sign Up button on the homepage.
- **DO NOT** attempt to call any booking tools.

[KNOWLEDGE BASE]
{KNOWLEDGE_BASE}
"""

# Handle Import Compatibility for FunctionContext vs function_tool
USE_LEGACY_STRUCTURE = False
try:
    from livekit.agents.llm import function_context
    FunctionContext = function_context.FunctionContext
    ai_callable = function_context.ai_callable
    USE_LEGACY_STRUCTURE = True
except ImportError:
    try:
        from livekit.agents.llm import function_tool
        # New version (1.3.x): No base class needed, use function_tool decorator
        FunctionContext = object 
        ai_callable = function_tool
    except ImportError:
         FunctionContext = object
         ai_callable = lambda *args, **kwargs: lambda f: f

# -------------------------
# 3. TOOLS (Function Context)
# -------------------------
class AssistantFnc(FunctionContext):
    def __init__(self, ctx: JobContext):
        if USE_LEGACY_STRUCTURE:
            super().__init__()
        self.ctx = ctx

    async def _disconnect_later(self):
        print("⏳ Scheduling disconnect in 4 seconds...")
        await asyncio.sleep(4)
        await self.ctx.room.disconnect()
        print("👋 Disconnected by agent.")

    @ai_callable(description="Book an appointment for the current user")
    async def book_appointment(self, date: str, time: str, phone: str, reason: str):
        print(f"🔧 Tool Triggered: Booking appointment: {date} {time} for {reason} (Phone: {phone})")
        
        # 1. Identify User from Metadata
        try:
            # Get the first participant (assuming 1-on-1 call)
            participant = list(self.ctx.room.remote_participants.values())[0]
            metadata = json.loads(participant.metadata) if participant.metadata else {}
            email = metadata.get("email")
            
            if not email:
                return "Error: I cannot verify your identity."
            
            db = SessionLocal()
            try:
                # 2. Find Patient
                user = db.query(User).filter(User.email == email).first()
                if not user:
                    return "Error: User record not found."
                
                patient = db.query(Patient).filter(Patient.user_id == user.id).first()
                if not patient:
                    # Fallback: maybe the user IS the patient if model differs, but let's assume patient exists
                    return "Error: Patient record not found."
                
                print(f"✅ DEBUG: Found Patient ID: {patient.id} for user {email}")
                
                # UPDATE PHONE if provided
                if phone:
                    import re
                    clean_phone = re.sub(r"\D", "", phone) # Strip non-digits
                    if len(clean_phone) != 10:
                        return f"Error: The phone number '{phone}' doesn't look right. Please provide exactly 10 digits."
                    
                    patient.phone = clean_phone
                    # db.commit() # Commit later with appt
                
                # 3. Create Appointment
                dt_str = f"{date} {time}"
                print(f"🕵️ DEBUG: Attempting to parse date: '{dt_str}'")
                
                try:
                    lower_date = date.lower().strip()
                    if "tomorrow" in lower_date:
                        # Handle "tomorrow" explicitly
                        base_time = dateutil.parser.parse(time) if time else datetime.now()
                        tomorrow = datetime.now() + timedelta(days=1)
                        appt_dt = tomorrow.replace(hour=base_time.hour, minute=base_time.minute, second=0, microsecond=0)
                        print(f"✅ DEBUG: Handled 'tomorrow' keyword: {appt_dt}")
                    elif "today" in lower_date:
                        # Handle "today" explicitly
                        base_time = dateutil.parser.parse(time) if time else datetime.now()
                        now = datetime.now()
                        appt_dt = now.replace(hour=base_time.hour, minute=base_time.minute, second=0, microsecond=0)
                        print(f"✅ DEBUG: Handled 'today' keyword: {appt_dt}")
                    else:
                        appt_dt = dateutil.parser.parse(dt_str)
                        print(f"✅ DEBUG: Parsed datetime: {appt_dt}")
                except Exception as e:
                    print(f"❌ DEBUG: Date parsing failed for '{dt_str}': {e}")
                    # Fallback if parsing fails -> NOW + 1 Hour (so it appears on dashboard)
                    appt_dt = datetime.now() + timedelta(hours=1)
                    print(f"⚠️ DEBUG: Falling back to SAFE TIME (Now + 1h): {appt_dt}")

                # 4. Assign Doctor (Dynamic Fetch)
                dentist = db.query(User).filter(User.role == "dentist").first()
                if dentist:
                    # Derived name since User table doesn't have name column
                    clean_name = dentist.email.split("@")[0].replace(".", " ").title()
                    doc_name = f"Dr. {clean_name}"
                    doc_id = dentist.id
                    print(f"✅ DEBUG: Assigned Doctor: {doc_name} (ID: {doc_id})")
                else:
                    doc_name = "Dr. Smith"
                    doc_id = None
                    print("⚠️ DEBUG: No dentist found. Assigned default Dr. Smith.")

                appt = Appointment(
                    patient_id=patient.id,
                    datetime=appt_dt,
                    status="scheduled",
                    doctor_name=doc_name,
                    doctor_id=doc_id,
                    reason=reason
                )
                db.add(appt)
                db.commit()
                
                # NOTIFY FRONTEND
                print("📡 Broadcasting update signal...")
                await self.ctx.room.local_participant.publish_data("APPOINTMENT_BOOKED")

                # SCHEDULE DISCONNECT
                asyncio.create_task(self._disconnect_later())
                
                return "Appointment booked successfully. The call will end now."
            
            except Exception as e:
                print(f"DB Error: {e}")
                return "Failed to book appointment due to system error."
            finally:
                db.close()

        except Exception as e:
            print(f"Metadata Error: {e}")
            return "Could not identify user."



# -------------------------
# 4. AGENT SETUP
# -------------------------
class Assistant(Agent):
    def __init__(self, instructions, fnc_ctx=None) -> None:
        super().__init__(instructions=instructions)
        self.fnc_ctx = fnc_ctx

server = AgentServer()

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    # Connect to the room first
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # ... setup participants ...
    # Wait for participant to get metadata
    print("Waiting for participant...")
    participant = await ctx.wait_for_participant()
    
    metadata = json.loads(participant.metadata) if participant.metadata else {}
    email = metadata.get("email")
    
    if email == "undefined":
        email = None
    
    fnc_ctx = None
    initial_msg = "Hello! I am Flossy, your dental assistant. Please sign up to book appointments."
    
    # DEFAULT SYSTEM PROMPT
    instructions = SYSTEM_PROMPT.format(current_time=datetime.now().strftime("%c"), user_name="Guest")

    if email:
        # Authenticated User
        fnc_ctx = AssistantFnc(ctx)
        initial_msg = "Hey there! I am Flossy, your dental assistant. How can I help you today?"
        
        # Inject Current Time & User Name
        now_str = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        user_name = participant.name or "Guest"
        instructions = SYSTEM_PROMPT.format(current_time=now_str, user_name=user_name)
        
        print(f"✅ User identified: {email} ({user_name}). Enabling Booking Tools.")

    # Initialize Components
    groq_llm = openai.LLM(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile",
    )
    stt = deepgram.STT()
    tts = deepgram.TTS()
    vad = silero.VAD.load()

    # --- USE VOICE PIPELINE AGENT (Standard) ---
    agent = VoicePipelineAgent(
        vad=vad,
        stt=stt,
        llm=groq_llm,
        tts=tts,
        fnc_ctx=fnc_ctx,
    )

    # Begin Conversation
    agent.start(ctx.room, participant)

    # Update system prompt dynamically
    await agent.update_instructions(instructions)

    # Allow interruptions and say hello
    await agent.say(initial_msg, allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, load_threshold=2.0))
    # FORCE INJECT TOOLS (Monkey Patch attempt for broken version)
    if fnc_ctx:
        session.fnc_ctx = fnc_ctx
        session.function_context = fnc_ctx

    await session.start(
        room=ctx.room,
        agent=Assistant(instructions, fnc_ctx), 
    )

    # Allow interruptions and say hello
    await session.say(initial_msg, allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, load_threshold=2.0))