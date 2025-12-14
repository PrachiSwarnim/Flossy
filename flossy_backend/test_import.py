try:
    from livekit.agents.voice import VoiceAgent
    print("✅ Found VoiceAgent in livekit.agents.voice")
except ImportError:
    print("❌ No VoiceAgent in livekit.agents.voice")

try:
    from livekit.agents import VoicePipelineAgent
    print("✅ Found VoicePipelineAgent in livekit.agents")
except ImportError:
    print("❌ No VoicePipelineAgent in root")