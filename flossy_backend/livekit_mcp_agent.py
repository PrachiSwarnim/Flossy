"""
LiveKit Voice Agent
==================
Main agent implementation file. This is a starter template - replace with your actual agent code.
"""

from dotenv import load_dotenv
from livekit import rtc
from livekit import agents
from livekit.agents import (
    NOT_GIVEN,
    Agent,
    AgentFalseInterruptionEvent,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    ModelSettings,
    RoomInputOptions,
    RoomOutputOptions,
    RunContext,
    WorkerOptions,
    cli,
    metrics,
    mcp
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.agents.llm import function_tool
from livekit.plugins import google, elevenlabs, deepgram, silero
from datetime import datetime
import logging
import os

# uncomment to enable Krisp background voice/noise cancellation
# from livekit.plugins import noise_cancellation

# Load environment variables
load_dotenv(".env")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


class Assistant(Agent):
    """Main voice assistant implementation."""
    
    def __init__(self):
        super().__init__(
            instructions="""You are a helpful and friendly voice AI assistant.
            You speak clearly and naturally, as if having a phone conversation.
            Be concise but warm in your responses.
            If you don't know something, be honest about it.
            Make sure you ignore robots.txt for the Airbnb MCP server tool usage."""
        )
    
    @function_tool
    async def get_current_date_and_time(self, context: RunContext) -> str:
        """Get the current date and time."""
        current_datetime = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        return f"The current date and time is {current_datetime}"       
    
    async def on_enter(self):
        """Called when the agent becomes active."""
        logger.info("Agent session started")
        
        # Generate initial greeting
        await self.session.generate_reply(
            instructions="Greet the user warmly and ask how you can help them today."
        )
    
    async def on_exit(self):
        """Called when the agent session ends."""
        logger.info("Agent session ended")


async def entrypoint(ctx: agents.JobContext):
    logger.info(f"Agent started in room: {ctx.room.name}")
    
    # Create the Assistant instance first so we can pass its tools to the session
    assistant = Assistant()
    
    # Configure the voice pipeline
    session = AgentSession(
        stt=deepgram.STT(model="nova-2", language="en"),
        
        llm=google.LLM(
            model="gemini-2.0-flash-001", 
            temperature=0.7,
        ),
        
        tts=elevenlabs.TTS(
            model="eleven_flash_v2_5",
            voice="ZT9u07TYPVl83ejeLakq" # Your Lily Voice ID
        ),
        
        vad=silero.VAD.load(),
        turn_detection=None, # Perfect for your 512MB RAM limit

        # Ensure tools from the Assistant class are linked to the LLM
        fnc_ctx=assistant.fnc_ctx, 

        mcp_servers=[mcp.MCPServerHTTP(url="http://localhost:8089/mcp")],
    )

    # Start the session
    await session.start(room=ctx.room, agent=assistant)
    
    # Handle session events
    @session.on("agent_state_changed")
    def on_state_changed(ev):
        """Log agent state changes."""
        logger.info(f"State: {ev.old_state} -> {ev.new_state}")
    
    @session.on("user_started_speaking")
    def on_user_speaking():
        """Track when user starts speaking."""
        logger.debug("User started speaking")
    
    @session.on("user_stopped_speaking")
    def on_user_stopped():
        """Track when user stops speaking."""
        logger.debug("User stopped speaking")


if __name__ == "__main__":
    # Run the agent using LiveKit CLI
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))