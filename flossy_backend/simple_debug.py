
import sqlalchemy
from sqlalchemy import create_engine, text
import datetime

# URL provided by user
url = "postgresql+psycopg2://flossy_user:prachi2973@localhost/flossy_db"

def run():
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            print("Successfully connected.")
            
            print("\n--- APPOINTMENTS ---")
            # Fetch all appointments
            result = conn.execute(text("SELECT id, datetime, status, doctor_name, patient_id FROM appointments"))
            rows = result.fetchall()
            if not rows:
                print("No appointments found.")
            for row in rows:
                print(row)

            print("\n--- DENTISTS ---")
            result = conn.execute(text("SELECT id, email, role FROM users WHERE role='dentist'"))
            rows = result.fetchall()
            for row in rows:
                print(row)
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run()
