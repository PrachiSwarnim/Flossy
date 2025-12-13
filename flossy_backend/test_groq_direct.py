from llm_client import groq_client
import sys

print("Testing Groq Direct...")
if not groq_client:
    print("❌ Groq Client is NONE. Check .env")
    sys.exit(1)

try:
    print("Sending request to Groq...")
    chat_completion = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": "Say hello"}],
        model="llama-3.3-70b-versatile",
    )
    print(f"✅ Groq Response: {chat_completion.choices[0].message.content}")
except Exception as e:
    print(f"❌ Groq Direct Error: {e}")
