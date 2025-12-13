import sys
import livekit.agents

print("--- LiveKit Agents Dir ---")
print(dir(livekit.agents))
print("--------------------------")

attempts = [
    "livekit.agents.pipeline",
    "livekit.agents.voice_pipeline",
    "livekit.agents.voice_assistant",
    "livekit.agents.llm"
]

for mod_name in attempts:
    try:
        print(f"Trying import {mod_name}...")
        mod = __import__(mod_name, fromlist=['VoicePipelineAgent'])
        if hasattr(mod, 'VoicePipelineAgent'):
            print(f"SUCCESS: Found VoicePipelineAgent in {mod_name}")
        else:
            print(f"Module {mod_name} exists but no VoicePipelineAgent")
            print(f"Contents: {dir(mod)}")
    except ImportError as e:
        print(f"ImportError for {mod_name}: {e}")

try:
    from livekit.agents import VoicePipelineAgent
    print("SUCCESS: Found VoicePipelineAgent in livekit.agents")
except ImportError:
    print("Not in livekit.agents")
