from database import SessionLocal
from models import Patient

def cleanup():
    db = SessionLocal()
    try:
        # Find 'prachi.swarnim'
        bad_patient = db.query(Patient).filter(Patient.name == "prachi.swarnim").first()
        if bad_patient:
            print(f"Found bad patient: {bad_patient.name} (ID: {bad_patient.id})")
            db.delete(bad_patient)
            db.commit()
            print("Deleted successfully.")
        else:
            print("No patient named 'prachi.swarnim' found.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    cleanup()
