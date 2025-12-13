import sys
import pkg_resources

try:
    dist = pkg_resources.get_distribution("livekit-agents")
    print(f"livekit-agents version: {dist.version}")
except Exception as e:
    print(f"Could not get livekit-agents version: {e}")

try:
    import livekit.agents.llm
    print("Successfully imported livekit.agents.llm")
    print(f"dir(livekit.agents.llm): {dir(livekit.agents.llm)}")
    
    if hasattr(livekit.agents.llm, 'function_context'):
        print("\nFound function_context in livekit.agents.llm")
        print(f"dir(livekit.agents.llm.function_context): {dir(livekit.agents.llm.function_context)}")
    else:
        print("\nfunction_context NOT found in livekit.agents.llm")

except ImportError as e:
    print(f"ImportError importing livekit.agents.llm: {e}")
except Exception as e:
    print(f"Error inspecting livekit.agents.llm: {e}")
