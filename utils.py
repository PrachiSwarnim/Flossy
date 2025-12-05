# utils.py
from google.genai import Client
from google.genai.types import GenerationConfig
import numpy as np
import itertools
import os

# NOTE: this module does not instantiate genai_client to avoid circular imports.
# Use `llm_client.genai_client` or pass model/client in callers as needed.

client = Client()  # local client for short helper calls if you want; prefer llm_client in server

from google.genai import Client

def ai_generate(prompt, temperature=0.0, model="gemini-2.5-flash", client_override=None):
    c = client_override or client

    # Older Gemini SDKs accept only this minimal signature
    res = c.models.generate_content(
        model=model,
        contents=prompt
    )

    # return text safely
    try:
        return res.text.strip()
    except:
        return str(res)
    
def cos_sim(a, b):
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)

def embed_with_client(genai_client, text):
    """Return vector list (floats) using provided genai_client."""
    resp = genai_client.models.embed_content(
        model="models/text-embedding-004",
        contents=[text]
    )
    emb = resp.embeddings[0].values
    return list(emb)

def build_actions(prompt_variants, temps, ctx_sizes, models):
    """
    Returns list of combos: [(prompt_idx, temp, ctx_size, model_idx), ...]
    Index in this list is the action_id used by bandits.
    """
    combos = list(itertools.product(range(len(prompt_variants)), temps, ctx_sizes, range(len(models))))
    return combos
