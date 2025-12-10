import os
import datetime
import httpx
import asyncio
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Patient, Interaction

load_dotenv()

# --- ELEVENLABS CONFIG ---
ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech"
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # default fallback voice ID

# --- LIVEKIT CONFIG ---
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")


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
        message = (
            f"Hello {patient.name}, this is FlossyAI from your dental clinic. "
            f"We hope you're recovering well after your recent procedure. "
            f"Are you experiencing any discomfort or pain?"
        )

        # Log interaction
        interaction = Interaction(
            patient_id=patient.id,
            channel="voice",
            message=message,
            created_at=datetime.datetime.now(),
        )
        db.add(interaction)
        db.commit()

        # Generate speech via ElevenLabs
        audio = await self.synthesize_speech(message)
        if audio:
            print(f"🔊 Voice generated for {patient.name}.")
        else:
            print("⚠️ Failed to generate voice.")

        print(f"[Simulating call to {patient.phone}]")
        print(f"Message spoken: {message}")

    async def synthesize_speech(self, text: str):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ELEVENLABS_TTS_URL}/{VOICE_ID}",
                headers={
                    "xi-api-key": ELEVENLABS_API_KEY,
                    "Content-Type": "application/json",
                },
                json={"text": text, "model_id": "eleven_multilingual_v2"},
            )
            if response.status_code == 200:
                return response.content
            else:
                print("ElevenLabs error:", response.text)
                return None


# Entry point for LiveKit Agent Worker
async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()  # connects to the LiveKit room/session

    session = AgentSession(
        llm=None,  # Optional: you can integrate GPT or other LLMs here
        agent=FlossyAgent(instructions="You are FlossyAI, a friendly dental assistant who follows up with patients after procedures.")
    )

    await session.start(room=ctx.room, agent=session.agent)


if __name__ == "__main__":
    agents.run(entrypoint)
