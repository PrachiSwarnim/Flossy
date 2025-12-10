# rl_core.py
from llm_client import genai_client
from utils import build_actions
from contextual_bandit import LinUCB
import numpy as np
import os

# Define the search space (tweakable)
PROMPT_VARIANTS = [
    """
You are FlossyAI Doctor Assistant.
Provide a factual answer in ≤5 lines using ONLY the given context.
If greeting, greet Dr. {doctor}. and say how you can help them today. No hallucinations.
If there is a question with greeting then greet Dr. {doctor} and then give the factual answer.
CONTEXT:
{context}
QUESTION:
{query}
""",
    """
Act as FlossyAI Medical Assistant.
Keep responses crisp, medically safe, and context-grounded.
Greet only if user greets. Explain in simple terms if asked.
CONTEXT:
{context}
QUESTION:
{query}
""",
    """
You are a concise, professional AI dental consultant.
Provide a 4-5 line answer using only the retrieved CONTEXT.
Avoid extra fluff. Keep explanations clear.
CONTEXT:
{context}
QUESTION:
{query}
"""
]

TEMPS = [0.0, 0.2, 0.4]
CTX_SIZES = [1, 3, 5]
MODELS = ["gemini-2.5-flash"]

ACTIONS = build_actions(PROMPT_VARIANTS, TEMPS, CTX_SIZES, MODELS)
ACTION_IDS = list(range(len(ACTIONS)))

# Choose d carefully: if your embedding dim is 1536, reduce via PCA offline.
# For now we assume embedding dim = 768 (as in your symptom_kb).
D = int(os.getenv("RL_CONTEXT_DIM", "768"))

bandit = LinUCB(bandit_name="doctor_global_v1", actions=ACTION_IDS, d=D, alpha=1.0)
