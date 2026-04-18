import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_ISSUER = os.getenv("CLERK_ISSUER", "https://clerk.smileartistsdentalstudio.com")
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
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://smileartistsdentalstudio.com",
    "https://www.smileartistsdentalstudio.com",
    "https://smile-artists-dental-studio.vercel.app",
    "https://flossy-ui.vercel.app",
    "https://flossy-ui-nine.vercel.app",
    "https://flossy-backend-422640267680.asia-south1.run.app"
]

# Cloud Storage
STORAGE_BUCKET = os.getenv("GOOGLE_STORAGE_BUCKET", "smile-artists-uploads")
UPLOAD_DIR = "uploads"
