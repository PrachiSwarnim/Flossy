from app.core.database import SessionLocal
from app.models import Patient, User

db = SessionLocal()
print("--- USERS ---")
users = db.query(User).all()
for u in users:
    print(f"User: {u.id}, {u.email}, Role: {u.role}")

print("\n--- PATIENTS ---")
try:
    patients = db.query(Patient).all()
    for p in patients:
        print(f"Patient: {p.id}, {p.name}, Phone: {p.phone}, Archive: {p.is_archived}, UserID: {p.user_id}")
except Exception as e:
    print(f"Error querying patients: {e}")
db.close()
