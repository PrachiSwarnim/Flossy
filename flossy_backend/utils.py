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
from llm_client import groq_client

# Models mapping
GROQ_MODEL = "llama-3.3-70b-versatile" # Current supported model


def ai_generate(prompt, temperature=0.7, model="gemini-2.5-flash", client_override=None):
    # 1. Try Groq First (if available)
    if groq_client:
        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a helpful dental assistant named Flossy."},
                    {"role": "user", "content": prompt}
                ],
                model=GROQ_MODEL,
                temperature=temperature,
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
             print(f"⚠️ Groq Error: {e}. Falling back to Gemini...")

    # 2. Fallback to Gemini
    c = client_override or client
    try:
        res = c.models.generate_content(
            model=model,
            contents=prompt
        )
        return res.text.strip()
    except Exception as e:
        print(f"❌ Both AI Providers Failed: {e}")
        return "I apologize, but I am currently having trouble connecting to my brain. Please try again later."
    
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
