from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_role
from app.models import Patient
from app.api.v1.patients.schemas import PatientUpdate

router = APIRouter()

@router.get("/")
def get_all_patients(db: Session = Depends(get_db), user = Depends(require_role(["receptionist", "dentist", "admin"]))):
    """
    Returns all non-archived patients with optimized formatting and source info.
    """
    # Relaxed filter: include 0 OR NULL
    from sqlalchemy import or_
    patients = db.query(Patient).filter(or_(Patient.is_archived == 0, Patient.is_archived == None)).all()
    print(f"DEBUG: Found {len(patients)} patients in DB query.")
    
    results = []
    for p in patients:
        display_name = p.name.strip().title() if p.name else "Unknown Patient"
        results.append({
            "id": p.id,
            "name": display_name,
            "phone": p.phone,
            "age": p.age,
            "email": p.user.email if p.user else None,
            "source": p.source or "website",
            "sex": p.sex
        })
    
    results.sort(key=lambda x: x["name"])
    return results

@router.patch("/{id}")
def update_patient(id: int, data: PatientUpdate, db: Session = Depends(get_db), user = Depends(require_role("receptionist"))):
    patient = db.query(Patient).filter(Patient.id == id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    if data.name:
        patient.name = data.name
    if data.phone:
        patient.phone = data.phone
    if data.age is not None:
        patient.age = data.age
    if data.sex:
        patient.sex = data.sex
        
    db.commit()
    return {"success": True}

@router.post("/{id}/archive")
def archive_patient(id: int, db: Session = Depends(get_db), user = Depends(require_role("receptionist"))):
    patient = db.query(Patient).filter(Patient.id == id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    patient.is_archived = 1
    db.commit()
    return {"success": True}

@router.get("/me")
def get_my_profile(db: Session = Depends(get_db), user_payload = Depends(require_role("patient"))):
    from models import User
    email = (user_payload.get("email") or user_payload.get("email_address") or "").lower()
    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
         return {
            "name": f"{user_payload.get('first_name', '')} {user_payload.get('last_name', '')}".strip() or "New Patient",
            "phone": None,
            "age": None,
            "sex": None,
            "email": email
        }
    
    return {
        "id": patient.id,
        "name": patient.name,
        "phone": patient.phone,
        "age": patient.age,
        "email": email,
        "sex": patient.sex
    }
