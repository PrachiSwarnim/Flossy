# llm_client.py
from google.genai import Client
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY env var")

genai_client = Client(api_key=GEMINI_API_KEY)
