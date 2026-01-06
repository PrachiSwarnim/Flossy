import sys

try:
    import twilio
    with open("check_twilio.log", "w") as f:
        f.write(f"SUCCESS: Twilio version {twilio.__version__}")
except ImportError:
    with open("check_twilio.log", "w") as f:
        f.write("FAILURE: Twilio not found")
except Exception as e:
    with open("check_twilio.log", "w") as f:
        f.write(f"ERROR: {e}")
