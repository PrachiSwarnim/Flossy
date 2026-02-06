from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_role
from app.models import Patient, TriageResult
from app.core.auth_utils import extract_names_from_email
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
    
    
    print(f"🔍 Fetching patients for user: {user.email}")
    
    # Debug: Check all users first
    all_users = db.query(User).all()
    print(f"📋 Total users in DB: {len(all_users)}")
    for u in all_users:
        print(f"   - User {u.id}: {u.email}, role={u.role}")
    
    # First, ensure all users with role='patient' have a Patient record
    patient_users = db.query(User).filter(User.role == "patient").all()
    print(f"👥 Users with role='patient': {len(patient_users)}")
    
    for pu in patient_users:
        existing = db.query(Patient).filter(Patient.user_id == pu.id).first()
        if not existing:
            # Auto-create patient record for this user
            print(f"   ➕ Creating patient record for user {pu.id}: {pu.email}")
            fname, lname = extract_names_from_email(pu.email)
            extracted_name = f"{fname} {lname}".strip()
            unique_placeholder = f"TEMP_{pu.id}_{int(time.time()) % 100000}"
            new_patient = Patient(
                name=extracted_name,
                first_name=fname,
                last_name=lname,
                phone=unique_placeholder,
                user_id=pu.id,
                source="website"
            )
            db.add(new_patient)
        else:
            print(f"   ✅ Patient record exists for user {pu.id}: patient_id={existing.id}")
    db.commit()
    
    # Query ALL patients first, then filter in Python (PostgreSQL might have issues with NULL comparison)
    all_patients = db.query(Patient).all()
    print(f"📊 Total patients in DB (all): {len(all_patients)}")
    
    # Filter out archived patients (handle NULL, 0, False as "not archived")
    patients = [p for p in all_patients if not p.is_archived or p.is_archived == 0]
    print(f"📊 After removing archived: {len(patients)}")
    
    # Debug: Show all patients before filtering
    for p in patients:
        print(f"   - Patient {p.id}: name={p.name}, phone={p.phone}, user_id={p.user_id}, is_archived={p.is_archived}")
    
    results = []
    skipped_staff = 0
    skipped_test = 0
    
    for p in patients:
        # Skip system/test accounts (based on specific placeholder values)
        if p.phone and p.phone in ["0000000000", "0", "00000", "1234567890"]:
            skipped_test += 1
            continue
        if p.name and p.name.lower().strip() in ["system", "test", "admin", "unknown"]:
            skipped_test += 1
            continue
        
        # Skip patients who are actually staff members (dentists, receptionists, admins)
        if p.user and p.user.role in ["dentist", "receptionist", "admin"]:
            skipped_staff += 1
            continue
            
        # NOTE: Previously we filtered staff users here, but this was too aggressive
            
        # Display name priority: patient's actual first_name > email extraction > name field
        if p.first_name:
            # Use patient's actual name fields
            display_name = f"{p.first_name} {p.last_name or ''}".strip()
        elif p.user and p.user.email:
            # Fall back to extracting from linked user's email
            fname, lname = extract_names_from_email(p.user.email)
            display_name = f"{fname} {lname}".strip()
        else:
            display_name = clean_name(p.name).title() if p.name else "Unknown Patient"
        
        # Hide placeholder and invalid phone numbers - show null in dashboard
        phone_display = p.phone
        if phone_display:
            # Check for various placeholder patterns
            if (phone_display.startswith("TEMP_") or 
                phone_display in ["0000000000", "0", "00000", "1234567890", "N/A", "NA", "null", "None"] or
                len(phone_display) < 7 or  # Too short to be real
                not any(c.isdigit() for c in phone_display)):  # No digits at all
                phone_display = None  # Show as null/empty in dashboard
        
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
            "role": p.user.role if p.user else "patient",  # Include role from linked user
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
    
    print(f"✅ Returning {len(results)} patients (Skipped: {skipped_staff} staff, {skipped_test} test)")
    results.sort(key=lambda x: x["name"])
    return results

@router.get("/debug")
def debug_patients(db: Session = Depends(get_db), user = Depends(require_role(["dentist", "admin"]))):
    """
    Debug endpoint to see raw patient and user data.
    """
    from app.models import User
    
    # Get all users
    users = db.query(User).all()
    users_data = [{"id": u.id, "email": u.email, "role": u.role, "first_name": u.first_name, "last_name": u.last_name} for u in users]
    
    # Get all patients (NO FILTERING)
    patients = db.query(Patient).all()
    patients_data = [{"id": p.id, "name": p.name, "phone": p.phone, "user_id": p.user_id, "is_archived": p.is_archived} for p in patients]
    
    return {
        "users_count": len(users_data),
        "users": users_data,
        "patients_count": len(patients_data),
        "patients": patients_data
    }

@router.patch("/{id}")
def update_patient(id: int, data: PatientUpdate, db: Session = Depends(get_db), user = Depends(require_role("receptionist"))):
    patient = db.query(Patient).filter(Patient.id == id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    if data.name:
        patient.name = data.name
    if data.first_name:
        patient.first_name = data.first_name
    if data.last_name:
        patient.last_name = data.last_name
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
        "first_name": patient.first_name,
        "last_name": patient.last_name,
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
            name=data.name or (user.email.split("@")[0] if user.email else "New Patient")
        )
        db.add(patient)
        db.flush()

    if data.name:
        patient.name = data.name
    if data.first_name:
        patient.first_name = data.first_name
    if data.last_name:
        patient.last_name = data.last_name
    if data.phone:
        patient.phone = data.phone
    if data.age is not None:
        patient.age = data.age
    if data.sex:
        patient.sex = data.sex
        
    db.commit()
    return {"success": True}
