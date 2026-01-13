import os
from dotenv import load_dotenv

load_dotenv()

# --- GOOGLE GEMINI (Keep for Embeddings + Backup) ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai_client = None

if GOOGLE_API_KEY:
    try:
        from google.genai import Client
        genai_client = Client(api_key=GOOGLE_API_KEY)
        print("(OK) Google GenAI Client Initialized")
    except Exception as e:
        print(f"(!) Google GenAI Init Failed: {e}")

# --- GROQ (Primary for Chat/Voice) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = None

if GROQ_API_KEY:
    try:
        from groq import Groq
        groq_client = Groq(api_key=GROQ_API_KEY)
        print("(OK) Groq Client Initialized")
    except Exception as e:
        print(f"(!) Groq Init Failed: {e}")
else:
    print("(!) GROQ_API_KEY is missing!")
