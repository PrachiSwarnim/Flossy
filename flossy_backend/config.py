# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Get this from your Murf Dashboard
    MURF_API_KEY = os.getenv("MURF_API_KEY") 
    # Use a specific Voice ID (e.g., 'en-US-genny' is a good female assistant voice)
    MURF_VOICE_ID = "en-US-genny" 

settings = Settings()