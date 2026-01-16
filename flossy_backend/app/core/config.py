import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_ISSUER = os.getenv("CLERK_ISSUER", "https://meet-grouse-33.clerk.accounts.dev")
JWKS_URL = f"{CLERK_ISSUER}/.well-known/jwks.json"

print(f"🔧 Config: CLERK_ISSUER={CLERK_ISSUER}")
print(f"🔧 Config: JWKS_URL={JWKS_URL}")
if CLERK_SECRET_KEY:
    print(f"🔧 Config: CLERK_SECRET_KEY=loaded ({CLERK_SECRET_KEY[:4]}***)")
else:
    print("⚠️ Config: CLERK_SECRET_KEY is MISSING!")

LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGINS", "*")

