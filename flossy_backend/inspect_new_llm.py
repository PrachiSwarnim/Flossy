import livekit.agents.llm
import sys

with open("llm_new.txt", "w") as f:
    try:
        from livekit.agents.llm import chat_context
        f.write(f"chat_context: {dir(chat_context)}\n")
    except ImportError as e:
        f.write(f"Error importing chat_context: {e}\n")
        
    try:
        from livekit.agents.llm import tool_context
        f.write(f"tool_context: {dir(tool_context)}\n")
    except ImportError as e:
        f.write(f"Error importing tool_context: {e}\n")

    f.write(f"llm root: {dir(livekit.agents.llm)}\n")
