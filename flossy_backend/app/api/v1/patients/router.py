from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from core.dependencies import require_role
from models import Patient
from .schemas import PatientUpdate

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
            "source": p.source or "website"
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
