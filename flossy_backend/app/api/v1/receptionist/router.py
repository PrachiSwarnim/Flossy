from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_role
from app.models import Patient, Appointment
from app.api.v1.patients.schemas import ReceptionistPatientAdd

router = APIRouter()

@router.post("/add_patient")
def add_receptionist_patient(data: ReceptionistPatientAdd, db: Session = Depends(get_db), user = Depends(require_role(["receptionist", "dentist", "admin"]))):
    # 1. Check/Create Patient
    patient = db.query(Patient).filter(Patient.phone == data.phone).first()
    if not patient:
        patient = Patient(
            name=data.name,
            phone=data.phone,
            age=data.age,
            contact_datetime=datetime.now(timezone.utc),
            source="manual",
            sex=data.sex
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
    else:
        # Update age if changed
        if data.age is not None:
             patient.age = data.age
             db.commit()
    
    # 2. Assign a default doctor or let dentist pick
    # Parse datetime if string
    dt_obj = data.datetime
    if isinstance(dt_obj, str):
         try:
             dt_obj = datetime.fromisoformat(dt_obj.replace('Z', '+00:00'))
         except:
             dt_obj = datetime.now(timezone.utc)

    new_appt = Appointment(
        patient_id=patient.id,
        datetime=dt_obj,
        reason=data.reason,
        status="scheduled",
        doctor_name=data.doctor_name
    )
    db.add(new_appt)
    db.commit()
    db.refresh(new_appt)

    # --- TRIGGER BOOKING CONFIRMATION SMS ---
    # try:
    #     from app.reminders import send_simulated_notification
    #     send_simulated_notification(db, new_appt, level=0)
    # except Exception as e:
    #     print(f"⚠️ Failed to send booking confirmation: {e}")
        
    return {"success": True, "appointment_id": new_appt.id}
