from sqlalchemy import text
from database import engine

def update_sequence():
    print("Updating patient ID sequence to start from 1000...")
    with engine.connect() as conn:
        try:
            # Check if largest ID is already > 1000 to avoid conflict
            result = conn.execute(text("SELECT MAX(id) FROM patients"))
            max_id = result.scalar() or 0
            
            start_val = max(1000, max_id + 1)
            
            conn.execute(text(f"ALTER SEQUENCE patients_id_seq RESTART WITH {start_val}"))
            conn.commit()
            print(f"✅ Success! Patient ID sequence restarted with {start_val}.")
        except Exception as e:
            print(f"❌ Error updating sequence: {e}")

if __name__ == "__main__":
    update_sequence()
