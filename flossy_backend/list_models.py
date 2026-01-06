from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

with open("models.txt", "w") as f:
    f.write("=== AVAILABLE GEMINI MODELS ===\n")
    try:
        for model in client.models.list():
            f.write(f"{model.name}\n")
    except Exception as e:
        f.write(f"Error listing models: {e}\n")

