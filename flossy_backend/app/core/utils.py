from google.genai import Client
from google.genai.types import GenerationConfig
import numpy as np
import itertools
import os
from app.core.config import GOOGLE_API_KEY
from app.services.llm_client import groq_client

# Models mapping
GROQ_MODEL = "llama-3.3-70b-versatile" # Current supported model

client = Client(api_key=GOOGLE_API_KEY)

def ai_generate(prompt, temperature=0.7, model="gemini-2.0-flash", client_override=None):
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
            contents=prompt,
            config=GenerationConfig(temperature=temperature)
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
    # Handle both old and new response structure if necessary, or assume new
    if hasattr(resp, "embeddings"):
        emb = resp.embeddings[0].values
    else:
        # Fallback for possible dictionary-like access if SDK changed
        emb = resp['embeddings'][0]['values']
    return list(emb)

def build_actions(prompt_variants, temps, ctx_sizes, models):
    """
    Returns list of combos: [(prompt_idx, temp, ctx_size, model_idx), ...]
    Index in this list is the action_id used by bandits.
    """
    combos = list(itertools.product(range(len(prompt_variants)), temps, ctx_sizes, range(len(models))))
    return combos

def clean_name(name: str) -> str:
    """Helper to remove strings like 'None', 'null', 'undefined' and trailing numbers from names."""
    import re
    if not name:
        return ""
    # Remove common placeholder strings
    for placeholder in ["None", "null", "undefined", "None None"]:
        name = name.replace(placeholder, "")
    
    # Remove trailing digits from each word (e.g., "Dhruv7" -> "Dhruv")
    words = name.split()
    cleaned_words = [re.sub(r'\d+$', '', word) for word in words]
    # Filter out any empty strings that might result
    cleaned_words = [w for w in cleaned_words if w.strip()]
    
    return " ".join(cleaned_words).strip()
