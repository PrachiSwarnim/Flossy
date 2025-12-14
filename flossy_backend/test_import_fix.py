
import os
try:
    from livekit.agents.multimodal import MultimodalAgent
    with open("verification.log", "w") as f:
        f.write("SUCCESS: Import worked")
except ImportError as e:
    with open("verification.log", "w") as f:
        f.write(f"FAILURE: {e}")
except Exception as e:
    with open("verification.log", "w") as f:
        f.write(f"ERROR: {e}")
