import os
import datetime
import asyncio
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, JobContext, WorkerOptions, cli
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Patient, Interaction
from livekit.plugins import elevenlabs, google
from livekit.plugins.silero import VAD

# Load environment variables
load_dotenv()

# --- ELEVENLABS CONFIG ---
ELEVENLABS_API_KEY = os.getenv("ELEVEN_API_KEY")  # corrected key name
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "Rachel")  # use readable default


class FlossyAgent(agents.Agent):
    async def on_start(self, session: AgentSession):
        print("✅ FlossyAI started successfully — beginning call sequence.")
        print("📞 FlossyAI is live and ready to make calls!")

        # Fetch most recent patient
        with SessionLocal() as db:
            patient = db.query(Patient).order_by(Patient.contact_datetime.desc()).first()
            if not patient:
                print("⚠️ No patient found to call.")
                return

            print(f"📲 Calling {patient.name} at {patient.phone}")
            await self.call_patient(session, db, patient)

    async def call_patient(self, session: AgentSession, db: Session, patient: Patient):
        """Simulate a voice call with a patient."""
        message = (
            f"Hello {patient.name}, this is FlossyAI from your dental clinic. "
            f"We hope you're recovering well after your recent procedure. "
            f"Are you experiencing any discomfort or pain?"
        )

        # Log interaction in DB
        interaction = Interaction(
            patient_id=patient.id,
            channel="voice",
            message=message,
            created_at=datetime.datetime.now(),
        )
        db.add(interaction)
        db.commit()

        print(f"🗣️ Speaking to {patient.name}...")
        await session.say(message)

        print(f"🗒️ Logged and completed simulated call to {patient.phone}")


# --- ENTRYPOINT ---
async def entrypoint(ctx: JobContext):
    await ctx.connect()

    # Configure ElevenLabs TTS
    tts = elevenlabs.TTS()
    tts.voice = VOICE_ID  # set the chosen voice

    # Configure agent behavior
    agent = FlossyAgent(
        instructions=(
            "You are FlossyAI, a friendly dental assistant who follows up with patients, "
            "helps with appointments, and checks their recovery in a caring tone."
        )
    )

    # Create AgentSession (no 'agent' in constructor!)
    session = AgentSession(
        vad=VAD.load(),
        stt=google.STT(),
        llm=google.LLM(),
        tts=tts,
    )

    # Start the session with your agent
    await session.start(agent=agent, room=ctx.room)


# --- LAUNCHER ---
if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
