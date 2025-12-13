
import sqlalchemy
from sqlalchemy import create_engine, text
import os

# URL provided by user
url = "postgresql+psycopg2://flossy_user:prachi2973@localhost/flossy_db"

def run():
    try:
        engine = create_engine(url)
        with open("debug_output.txt", "w") as f:
            f.write("Connecting...\n")
            with engine.connect() as conn:
                f.write("Connected.\n")
                
                f.write("\n--- DENTISTS ---\n")
                result = conn.execute(text("SELECT id, email, role FROM users WHERE role='dentist'"))
                rows = result.fetchall()
                for row in rows:
                    f.write(f"{row}\n")

                f.write("\n--- APPOINTMENTS ---\n")
                # Fetch all appointments
                result = conn.execute(text("SELECT id, datetime, status, doctor_name, patient_id FROM appointments"))
                rows = result.fetchall()
                if not rows:
                    f.write("No appointments found.\n")
                for row in rows:
                    f.write(f"{row}\n")
                    
    except Exception as e:
        with open("debug_output.txt", "a") as f:
            f.write(f"Error: {e}\n")

if __name__ == "__main__":
    run()
