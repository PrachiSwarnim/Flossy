import os
import json

from typing import Optional, Tuple, List
from app.core.config import GOOGLE_API_KEY
from app.services.llm_client import genai_client as _static_genai_client

# Globals for Lazy Loading
_faiss_index = None
_faiss_chunks = None
_bandit = None
ACTIONS = None
PROMPT_VARIANTS = None
MODELS = None
_genai_client = None

def load_faiss_index():
    global _faiss_index, _faiss_chunks
    if _faiss_index is None:
        try:
            import faiss
        except ImportError:
            raise RuntimeError("FAISS library not installed. Please install faiss-cpu.")

        if not os.path.exists("dental_embeddings.faiss"):
             # Try absolute path or one level up if in app dir
             # Assuming running from flossy_backend root
             raise FileNotFoundError("FAISS file missing: dental_embeddings.faiss")

        if not os.path.exists("dental_meta.json"):
            raise FileNotFoundError("Meta file missing: dental_meta.json")

        try:
            _faiss_index = faiss.read_index("dental_embeddings.faiss")
            with open("dental_meta.json", "r", encoding="utf-8") as f:
                meta = json.load(f)
            _faiss_chunks = meta.get("chunks", [])
            print("FAISS index loaded (lazy).")
        except Exception as e:
            # Fallback or re-raise
            print(f"Error loading FAISS: {e}")
            raise RuntimeError(f"FAISS load failed: {e}")

    return _faiss_index, _faiss_chunks

def get_genai_client():
    # Use the one initialized in llm_client if available
    return _static_genai_client

def get_bandit_and_meta():
    global _bandit, ACTIONS, PROMPT_VARIANTS, MODELS
    if _bandit is None:
        try:
            # Assumes rl_core.py is in the python path (root of backend)
            from rl_core import bandit as bandit_obj, ACTIONS as _A, PROMPT_VARIANTS as _P, MODELS as _M, LinUCB as LinUCBClass
            ACTIONS, PROMPT_VARIANTS, MODELS = _A, _P, _M
            _bandit = bandit_obj if bandit_obj is not None else LinUCBClass(
                bandit_name="doctor_global_v1",
                actions=list(range(len(_A))),
                d=768,
                alpha=1.0
            )
            print("RL bandit loaded lazily.")
        except Exception as e:
            print("Failed to lazy-load RL bandit:", e)
            try:
                from rl_core import ACTIONS as _A, PROMPT_VARIANTS as _P, MODELS as _M
                ACTIONS, PROMPT_VARIANTS, MODELS = _A, _P, _M
            except Exception:
                ACTIONS, PROMPT_VARIANTS, MODELS = [], [], []
            _bandit = None
    return _bandit, ACTIONS, PROMPT_VARIANTS, MODELS
