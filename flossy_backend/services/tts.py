# services/tts.py
import requests
from config import settings

def stream_text_to_speech(text: str):
    """
    Generates audio from text using Murf Falcon and yields chunks of data.
    """
    url = "https://api.murf.ai/v1/speech/stream"
    
    headers = {
        "api-key": settings.MURF_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mp3"
    }
    
    payload = {
        "text": text,
        "voiceId": settings.MURF_VOICE_ID, # Configured in settings
        "model": "FALCON",                 # Critical for speed
        "multiNativeLocale": "en-US"
    }

    # Make the request with stream=True
    with requests.post(url, json=payload, headers=headers, stream=True) as response:
        if response.status_code != 200:
            # Log error for debugging
            print(f"TTS Error: {response.status_code} - {response.text}")
            yield b"" # Yield empty bytes or handle error gracefully
            return

        # Yield chunks as they arrive (Low Latency)
        for chunk in response.iter_content(chunk_size=4096):
            if chunk:
                yield chunk