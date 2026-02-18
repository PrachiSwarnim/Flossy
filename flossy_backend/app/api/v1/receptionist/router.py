from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.core.database import get_db
from app.core.dependencies import require_role
from app.models import Patient, Appointment
from app.api.v1.patients.schemas import ReceptionistPatientAdd

router = APIRouter()

@router.post("/add_patient")
def add_receptionist_patient(data: ReceptionistPatientAdd, db: Session = Depends(get_db), user = Depends(require_role(["receptionist", "dentist", "admin"]))):
    try:
        # 1. Check/Create Patient — search by phone first, then by name
        patient = None

        # Try exact phone match (skip TEMP_ phones)
        if data.phone and not data.phone.startswith("TEMP_"):
            patient = db.query(Patient).filter(Patient.phone == data.phone).first()

        # If no match by phone, try matching by name (case-insensitive)
        if not patient:
            patient = db.query(Patient).filter(
                func.lower(Patient.name) == func.lower(data.name)
            ).first()

        if patient:
            # Update existing patient with new info
            if data.name:
                patient.name = data.name
            if data.phone and not data.phone.startswith("TEMP_"):
                # Replace TEMP phone with real phone
                if patient.phone and patient.phone.startswith("TEMP_"):
                    patient.phone = data.phone
                elif not patient.phone:
                    patient.phone = data.phone
            if data.age is not None:
                patient.age = data.age
            if data.sex:
                patient.sex = data.sex
            db.commit()
            db.refresh(patient)
            print(f"✅ Updated existing patient {patient.id}: {patient.name}, phone={patient.phone}")
        else:
            # Create new patient
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
            print(f"✅ Created new patient {patient.id}: {patient.name}, phone={patient.phone}")

        # 2. Parse datetime — MUST be timezone-aware for IST comparisons in dentist dashboard
        dt_obj = data.datetime
        if isinstance(dt_obj, str):
            try:
                dt_obj = datetime.fromisoformat(dt_obj.replace('Z', '+00:00'))
            except:
                dt_obj = datetime.now(timezone.utc)
        # Ensure timezone-aware (if naive, assume UTC)
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=timezone.utc)

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

        print(f"✅ Created appointment {new_appt.id} for patient {patient.id}: {data.reason} at {dt_obj}")
        return {"success": True, "appointment_id": new_appt.id, "patient_id": patient.id}

    except Exception as e:
        db.rollback()
        print(f"❌ Error in add_receptionist_patient: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add patient: {str(e)}")

