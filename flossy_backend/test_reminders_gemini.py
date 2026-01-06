import os
import sys
from dotenv import load_dotenv

def log(msg):
    with open("test_log.txt", "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

log("DEBUG: Starting test script...")
log("DEBUG: Importing dotenv...")

# Load env vars to ensure we have API keys
load_dotenv()
log("DEBUG: Env vars loaded.")

try:
    log("DEBUG: Importing reminders...")
    from reminders import generate_quirky_message_gemini
except Exception as e:
    log(f"CRITICAL ERROR IMPORTING: {e}")
    sys.exit(1)

def test_quirky_messages():
    log("🧪 Testing Quirky Reminder Generation (Gemini)...")
    
    test_cases = [
        (1, "Alice", "10:00 AM", "Dr. Smith"),
        (2, "Bob", "8:00 PM", "Dr. Jones"),
        (4, "Charlie", "2:00 PM", "Dr. White"),
        (5, "David", "3:30 PM", "Dr. Smile"),
    ]

    for level, patient, time_str, doctor in test_cases:
        log(f"\n--- Level {level} (Patient: {patient}) ---")
        try:
            msg = generate_quirky_message_gemini(level, patient, time_str, doctor)
            log(f"Generated Message:\n{msg}")
            
            # Basic checks
            if not msg:
                log("❌ Error: Message is empty!")
            elif "Reminder:" in msg and "Gemini message generation failed" not in msg and len(msg) > 20: 
                 pass
        except Exception as e:
            log(f"❌ Error generating message: {e}")
             
    log("\n✅ Test Complete")

if __name__ == "__main__":
    if os.path.exists("test_log.txt"):
        os.remove("test_log.txt")
    test_quirky_messages()
