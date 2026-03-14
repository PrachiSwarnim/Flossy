# rl_core.py
from llm_client import genai_client
from utils import build_actions
from contextual_bandit import LinUCB
import numpy as np
import os

# Define the search space (tweakable)
PROMPT_VARIANTS = [
    """
You are Flossy, the intelligent receptionist for Smile Artists Dental Studio.
Answer questions about pricing and symptoms using your Knowledge Base.
Use `lookup_patient`, `get_todays_appointments`, and `list_all_patients` for patient info.
Be warm, professional and concise.
""",
    """
Act as Flossy, a professional dental front-desk assistant.
Your goal is to help patients book appointments and answer their queries.
Use your tools (`get_todays_appointments`, `lookup_patient`, `list_all_patients`) to provide accurate schedule and patient data.
Keep responses to 1-2 sentences.
""",
    """
You are Flossy, a helpful and empathetic AI assistant for a dental clinic.
Greet patients warmly and use your calendar tools (`check_availability`, `book_appointment`) for bookings.
For patient records, use the appropriate lookup tools. Never hallucinate patient data.
"""
]

TEMPS = [0.0, 0.2, 0.4]
CTX_SIZES = [1, 3, 5]
MODELS = [
    "models/gemini-2.5-flash",
    "models/gemini-2.5-pro",
    "models/gemini-2.0-flash-lite-001",
]

ACTIONS = build_actions(PROMPT_VARIANTS, TEMPS, CTX_SIZES, MODELS)
ACTION_IDS = list(range(len(ACTIONS)))

# Choose d carefully: if your embedding dim is 1536, reduce via PCA offline.
# For now we assume embedding dim = 768 (as in your symptom_kb).
D = int(os.getenv("RL_CONTEXT_DIM", "768"))

bandit = LinUCB(bandit_name="doctor_global_v1", actions=ACTION_IDS, d=D, alpha=1.0)
