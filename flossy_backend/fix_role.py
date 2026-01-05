import os
import requests
from dotenv import load_dotenv
from database import SessionLocal
from models import User

load_dotenv()

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
TARGET_EMAIL = "prachi.swarnim@gmail.com"
TARGET_ROLE = "dentist"

def fix_role():
    print(f"Fixing role for {TARGET_EMAIL} to '{TARGET_ROLE}'...")

    # 1. Local DB Update
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == TARGET_EMAIL).first()
        if user:
            print(f"Found user in DB (current role: {user.role})")
            user.role = TARGET_ROLE
            db.commit()
            print("✅ Local DB role updated.")
        else:
            print("❌ User not found in local DB.")
    except Exception as e:
        print(f"❌ DB Error: {e}")
    finally:
        db.close()

    # 2. Clerk Metadata Update
    if not CLERK_SECRET_KEY:
        print("❌ Missing CLERK_SECRET_KEY")
        return

    headers = {"Authorization": f"Bearer {CLERK_SECRET_KEY}"}
    
    # Fetch User ID
    print("Fetching Clerk User ID...")
    try:
        res = requests.get(f"https://api.clerk.dev/v1/users?email_address={TARGET_EMAIL}", headers=headers)
        if not res.ok:
            print(f"❌ Failed to fetch user from Clerk: {res.text}")
            return
        
        users = res.json()
        if not users:
            print("❌ User not found in Clerk.")
            return

        user_id = users[0]["id"]
        print(f"Found Clerk ID: {user_id}")

        # Update Metadata
        patch_res = requests.patch(
            f"https://api.clerk.dev/v1/users/{user_id}",
            headers=headers,
            json={"public_metadata": {"role": TARGET_ROLE}}
        )
        
        if patch_res.ok:
            print("✅ Clerk metadata updated.")
        else:
            print(f"❌ Failed to update Clerk metadata: {patch_res.text}")

    except Exception as e:
        print(f"❌ Clerk API Error: {e}")

if __name__ == "__main__":
    fix_role()
