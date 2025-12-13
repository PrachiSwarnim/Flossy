import livekit.agents.llm as llm
import sys

with open("llm_inspection.txt", "w") as f:
    f.write(f"LLM Dir: {dir(llm)}\n")
    try:
        f.write(f"Looking for FunctionContext: {'FunctionContext' in dir(llm)}\n")
    except:
        pass
    try:
        import livekit.agents.llm.function_context
        f.write("Found submodule function_context\n")
    except ImportError:
        f.write("Submodule function_context NOT found\n")
