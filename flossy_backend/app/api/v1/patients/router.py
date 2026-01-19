from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_role
from app.models import Patient, TriageResult
from app.api.v1.patients.schemas import PatientUpdate
from app.core.utils import clean_name

router = APIRouter()

@router.get("/")
def get_all_patients(db: Session = Depends(get_db), user = Depends(require_role(["receptionist", "dentist", "admin"]))):
    """
    Returns all non-archived patients with AI risk profiling and triage status.
    Excludes staff members (dentists, receptionists) from the list.
    Ensures all users with 'patient' role have a patient record.
    """
    from sqlalchemy import or_, desc
    from app.models import Appointment, TriageResult, User
    import time
    import re
    
    def extract_name_from_email(email: str) -> str:
        """Extract a clean, human-readable name from an email address."""
        if not email or "@" not in email:
            return "Unknown"
        
        local_part = email.split("@")[0]
        
        # Remove numbers
        local_part = re.sub(r'\d+', '', local_part)
        
        # Split by common separators
        parts = re.split(r'[._\-]', local_part)
        
        # Filter out empty parts and very short parts (likely initials)
        parts = [p.strip().title() for p in parts if len(p.strip()) > 1]
        
        if len(parts) >= 2:
            # Check if it looks like lastname.firstname format (common in India)
            # Heuristic: if first part looks like a surname (vasisht, kumar, sharma, etc)
            # Actually, simpler: just reverse if parts[1] is a common first name
            # For now, let's just use as-is but put them in a natural order
            # Assumption: email format firstname.lastname or lastname.firstname
            # We'll display as "Firstname Lastname" by taking parts[1] parts[0] if needed
            # Actually let's just join them and let the clinic edit if wrong
            return " ".join(parts)
        elif len(parts) == 1:
            return parts[0]
        else:
            return "Unknown"
    
    # First, ensure all users with role='patient' have a Patient record
    patient_users = db.query(User).filter(User.role == "patient").all()
    for pu in patient_users:
        existing = db.query(Patient).filter(Patient.user_id == pu.id).first()
        if not existing:
            # Auto-create patient record for this user
            clean_name = extract_name_from_email(pu.email)
            unique_placeholder = f"TEMP_{pu.id}_{int(time.time()) % 100000}"
            new_patient = Patient(
                name=clean_name,
                phone=unique_placeholder,
                user_id=pu.id,
                source="website"
            )
            db.add(new_patient)
    db.commit()
    
    # Query all non-archived patients
    patients = db.query(Patient).filter(or_(Patient.is_archived == 0, Patient.is_archived == None)).all()
    
    results = []
    for p in patients:
        # Skip patients whose linked user is a dentist or receptionist (staff)
        if p.user and p.user.role in ["dentist", "receptionist", "admin"]:
            continue
        
        # Skip system/test accounts
        if p.phone and p.phone in ["0000000000", "0", "00000", "1234567890"]:
            continue
        if p.name and p.name.lower().strip() in ["system", "test", "admin", "unknown"]:
            continue
            
        display_name = p.name.strip().title() if p.name else "Unknown Patient"
        
        # Hide TEMP_ placeholder phone numbers
        phone_display = p.phone
        if phone_display and phone_display.startswith("TEMP_"):
            phone_display = None  # Hide placeholder
        
        # Fetch latest triage
        latest_triage = db.query(TriageResult).filter(TriageResult.patient_id == p.id).order_by(desc(TriageResult.created_at)).first()
        
        # Calculate behavioral risk (No-shows / Payment Delays)
        missed = db.query(Appointment).filter(Appointment.patient_id == p.id, Appointment.status == "missed").count()
        total_appt = db.query(Appointment).filter(Appointment.patient_id == p.id).count()
        
        risk_score = 0
        risk_reasons = []
        
        if total_appt > 0 and (missed / total_appt) > 0.3:
            risk_score += 40
            risk_reasons.append("High cancellation rate (30%+)")
        
        if latest_triage and latest_triage.urgency == "emergency":
            risk_score += 50
            risk_reasons.append("Active clinical emergency")
            
        risk_level = "Low"
        if risk_score > 70: risk_level = "Critical"
        elif risk_score > 30: risk_level = "Moderate"

        results.append({
            "id": p.id,
            "name": display_name,
            "phone": phone_display,
            "age": p.age,
            "email": p.user.email if p.user else None,
            "source": p.source or "website",
            "sex": p.sex,
            "risk_profile": {
                "level": risk_level,
                "score": risk_score,
                "reasons": risk_reasons,
                "ai_explanation": f"Patient flagged as {risk_level} risk due to {', '.join(risk_reasons) if risk_reasons else 'clean history'}."
            },
            "latest_triage": {
                "urgency": latest_triage.urgency,
                "issue": latest_triage.probable_issue,
                "reasoning": latest_triage.ai_reasoning
            } if latest_triage else None
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
@router.patch("/me")
def update_my_profile(data: PatientUpdate, db: Session = Depends(get_db), user = Depends(require_role("patient"))):
    """
    Allow a patient to update their own profile.
    """
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    
    if not patient:
        # Create a basic patient profile if it doesn't exist yet
        # (This can happen if they logged in but haven't booked an appointment yet)
        patient = Patient(
            user_id=user.id,
            name=data.name or (user.email.split("@")[0] if user.email else "New Patient"),
            email=user.email
        )
        db.add(patient)
        db.flush()

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
