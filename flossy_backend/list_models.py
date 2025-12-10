from google import genai
import os

api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

print("\n=== AVAILABLE GEMINI MODELS ===\n")
for model in client.models.list():
    print(model.name)
