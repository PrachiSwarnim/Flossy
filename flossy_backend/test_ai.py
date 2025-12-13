from utils import ai_generate
print("Testing AI Generation (likely via Groq)...")
try:
    response = ai_generate("Hello, say 'Groq is working' if you can hear me.")
    print(f"✅ AI Response: {response}")
except Exception as e:
    print(f"❌ AI Test Failed: {e}")
