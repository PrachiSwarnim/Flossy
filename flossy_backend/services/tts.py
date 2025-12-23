import os
import requests
from dotenv import load_dotenv

load_dotenv()

def stream_text_to_speech(text: str):
    """
    Generates audio from text using ElevenLabs API directly via requests.
    This is more reliable than the SDK across different environments.
    """
    api_key = os.getenv("ELEVEN_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "ZT9u07TYPVl83ejeLakq")
    model_id = "eleven_flash_v2.5"
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    
    data = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    
    try:
        print(f"🎙️ ElevenLabs Direct Stream: {text[:30]}...")
        response = requests.post(url, json=data, headers=headers, stream=True)
        
        if response.status_code != 200:
            print(f"❌ ElevenLabs Error: {response.status_code} - {response.text}")
            return
            
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                yield chunk
                
    except Exception as e:
        print(f"❌ ElevenLabs Connectivity Error: {e}")
