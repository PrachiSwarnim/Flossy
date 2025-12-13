from livekit.agents import AgentSession
import inspect

try:
    print(f"AgentSession init: {inspect.signature(AgentSession.__init__)}")
except Exception as e:
    print(f"Error inspecting AgentSession: {e}")

try:
    print(f"AgentSession doc: {AgentSession.__doc__}")
except:
    pass
