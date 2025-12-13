import logging
import os
from dotenv import load_dotenv
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,
    AgentServer,
    AgentSession,
    Agent,
    RoomInputOptions
)
from livekit.plugins import openai, google, silero
# from livekit.plugins import turn_detector

load_dotenv()

# -------------------------
# KNOWLEDGE BASE & PROMPT
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

SYSTEM_PROMPT = f"""
You are FlossyAI, a warm, helpful, and professional Patient Dental Concierge.

OBJECTIVE:
- Act as a smart front-desk assistant.
- Answer questions using the [KNOWLEDGE BASE] below.
- If the user asks for booking, guide them.

[KNOWLEDGE BASE]
{KNOWLEDGE_BASE}

RULES:
1. **Answering Questions**:
   - If user asks about Pricing/Post-op/Symptoms, USE THE KNOWLEDGE BASE.
   - Be concise but warm.
   - Example Pricing: "Our implants start at ₹25,000. It depends on the case. Would you like a consultation?"

2. **Booking Flow**:
   - If user says "Book cleaning", ask for preferred date and time.
   - (Note: Final booking is handled by the front-desk system, just gather details).

3. **Personality**:
   - Warm, empathetic, professional.
   - Keep responses short for voice conversation.
"""

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)

server = AgentServer()

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    # ctx.connect() is handled by AgentSession/AgentServer flow in v1.0 usually, or implied. 
    # The migration guide snippet does NOT show ctx.connect().
    # It shows session.start(room=ctx.room)

    # Groq via OpenAI Plugin
    groq_llm = openai.LLM(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile",
    )

    # Groq Whisper via OpenAI Plugin (as STT)
    groq_stt = openai.STT(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.getenv("GROQ_API_KEY"),
        model="whisper-large-v3",
    )

    session = AgentSession(
        stt=groq_stt,
        llm=groq_llm,
        tts=google.TTS(),
        vad=silero.VAD.load(),
    )

    await session.start(
        room=ctx.room,
        agent=Assistant(),
    )

    # Allow interruptions and say hello
    await session.generate_reply(instructions="Say 'Hi! I am Flossy, your dental assistant. How can I help?'")

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, load_threshold=2.0))
