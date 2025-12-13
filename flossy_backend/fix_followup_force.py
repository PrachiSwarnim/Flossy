from database import engine
from sqlalchemy import text

def force_fix():
    print("Forcing follow_up_reason column addition...")
    with engine.connect() as conn:
        # 1. Try adding column directly
        try:
            conn.execute(text("ALTER TABLE appointments ADD COLUMN follow_up_reason TEXT"))
            conn.commit()
            print("✅ SUCCESS: Added column 'follow_up_reason'")
        except Exception as e:
            print(f"⚠️ ADD COLUMN Attempt 1 failed: {e}")
            
    # 2. Verify
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT follow_up_reason FROM appointments LIMIT 1"))
            print("✅ VERIFIED: Column exists (Selection worked)")
    except Exception as e:
        print(f"❌ VERIFICATION FAILED: {e}")

if __name__ == "__main__":
    force_fix()
