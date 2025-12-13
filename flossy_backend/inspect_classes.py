import inspect
import sys

def print_signature(cls, name):
    try:
        sig = inspect.signature(cls.__init__)
        print(f"DEBUG: {name} init args: {sig}")
    except Exception as e:
        print(f"DEBUG: Could not inspect {name}: {e}")

try:
    from livekit.agents import AgentSession
    print_signature(AgentSession, "AgentSession")
except ImportError:
    print("DEBUG: AgentSession not found in livekit.agents")

try:
    import livekit.plugins.openai as openai
    print_signature(openai.LLM, "openai.LLM")
except ImportError:
    print("DEBUG: openai plugin not found")

# Check for VoicePipelineAgent locations
locations = [
    "livekit.agents.pipeline",
    "livekit.agents.voice_pipeline",
    "livekit.agents"
]

found_vpa = False
for loc in locations:
    try:
        module = __import__(loc, fromlist=['VoicePipelineAgent'])
        if hasattr(module, 'VoicePipelineAgent'):
            print(f"DEBUG: Found VoicePipelineAgent in {loc}")
            print_signature(module.VoicePipelineAgent, "VoicePipelineAgent")
            found_vpa = True
    except ImportError:
        pass

if not found_vpa:
    print("DEBUG: VoicePipelineAgent NOT FOUND in standard locations")
