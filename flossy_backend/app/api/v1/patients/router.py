from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_role
from app.models import Patient
from app.api.v1.patients.schemas import PatientUpdate
from app.core.utils import clean_name

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
def get_my_profile(db: Session = Depends(get_db), user = Depends(require_role("patient"))):
    """
    Get the current patient's profile.
    Note: require_role returns a User object, not the JWT payload.
    """
    # user is already a User object from require_role
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    
    if not patient:
        # Return basic profile from User if no Patient record exists
        # Try to get first/last name from user's email or stored names
        name_parts = []
        if hasattr(user, 'first_name') and user.first_name:
            if user.first_name and user.first_name != "None":
                name_parts.append(user.first_name)
        
        if hasattr(user, 'last_name') and user.last_name:
            if user.last_name and user.last_name != "None":
                name_parts.append(user.last_name)
        
        display_name = " ".join(name_parts).strip() if name_parts else "New Patient"
        
        return {
            "name": display_name,
            "phone": None,
            "age": None,
            "sex": None,
            "email": user.email
        }
    
    # Filter out "None" from patient name if it exists
    final_name = clean_name(patient.name)

    return {
        "id": patient.id,
        "name": final_name or clean_name(user.email.split("@")[0]),
        "phone": patient.phone,
        "age": patient.age,
        "email": user.email,
        "sex": patient.sex
    }
