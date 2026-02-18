from datetime import datetime, timezone, timedelta
import re
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models import Appointment, User, Patient
from app.api.v1.appointments.schemas import AppointmentUpdate, AppointmentCreate
from app.core.utils import clean_name

router = APIRouter()

@router.post("/", status_code=201)
def create_appointment(
    appt: AppointmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    user = Depends(require_role(["patient"])) # Only patients book for themselves generally
):
    """
    Create a new appointment.
    Note: require_role returns a User object, not the JWT payload.
    We use request.state.user for the JWT payload (for first/last name).
    """
    # user is already a User object from require_role
    # Get JWT payload for additional info like first_name, last_name
    jwt_payload = getattr(request.state, "user", {})
    
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        # Build name from JWT payload or user email
        first_name = jwt_payload.get("first_name", "") if isinstance(jwt_payload, dict) else ""
        last_name = jwt_payload.get("last_name", "") if isinstance(jwt_payload, dict) else ""
        name = clean_name(f"{first_name} {last_name}")
        if not name:
            name = clean_name(user.email.split("@")[0].replace(".", " ").title()) or "New Patient"
        
        patient = Patient(
            name=name,
            phone=appt.phone or "0000000000",
            user_id=user.id,
            age=appt.age,
            sex=appt.sex
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
    else:
        # Update existing patient if info provided
        if appt.phone and (not patient.phone or patient.phone == "0000000000"):
            patient.phone = appt.phone
        if appt.age:
            patient.age = appt.age
        if appt.sex:
            patient.sex = appt.sex
        db.commit()

    # 2. Create Appointment
    new_appt = Appointment(
        patient_id=patient.id,
        doctor_id=appt.doctor_id,
        datetime=appt.datetime,
        reason=appt.reason,
        status="pending_approval" # Default for new bookings
    )
    db.add(new_appt)
    db.commit()
    db.refresh(new_appt)
    return {"message": "Appointment requested", "id": new_appt.id, "status": new_appt.status}

@router.put("/{id}")
def update_appointment(id: int, appointment_update: AppointmentUpdate, db: Session = Depends(get_db)):
    # 1. Fetch the appointment
    db_appointment = db.query(Appointment).filter(Appointment.id == id).first()
    if not db_appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # 2. Update fields if provided
    if appointment_update.datetime:
        db_appointment.datetime = appointment_update.datetime
    
    if appointment_update.status:
        db_appointment.status = appointment_update.status
        
        # Logic: If status becomes "pending_approval" (re-negotiation by patient), clear previous denial
        if appointment_update.status == "pending_approval":
            db_appointment.denial_reason = None
            
    # 3. Explicitly update the reason and denial_reason
    if appointment_update.reason:
        db_appointment.reason = appointment_update.reason 
        
    if appointment_update.denial_reason is not None: # Allow clearing it if needed, or setting it
        db_appointment.denial_reason = appointment_update.denial_reason

    # 4. Commit changes
    db.commit()
    db.refresh(db_appointment)
    
    return {"message": "Appointment updated successfully", "appointment": {
        "id": db_appointment.id,
        "reason": db_appointment.reason,
        "status": db_appointment.status,
        "time": db_appointment.datetime.isoformat(),
        "denial_reason": db_appointment.denial_reason
    }}

@router.get("/today")
def get_today_appointments(request: Request, db: Session = Depends(get_db)):
    user_payload = getattr(request.state, "user", None)
    if not user_payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    email = (user_payload.get("email") or user_payload.get("email_address") or "").lower()
    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user:
        user = User(email=email, created_at=datetime.now(timezone.utc))
        db.add(user)
        db.commit()
        db.refresh(user)

    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, now.day, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    base_query = (
        db.query(Appointment)
        .options(joinedload(Appointment.patient))
        .filter(
            Appointment.datetime >= start,
            Appointment.datetime < end,
            Appointment.status == "scheduled"
        )
        .order_by(Appointment.datetime.asc())
    )

    if user.role == "dentist" or user.role == "receptionist":
        # Dentists (and Receptionists) see ALL appointments
        appts = base_query.all()
    else:
        # Patients only see their own
        patient = db.query(Patient).filter(Patient.user_id == user.id).first()
        if not patient:
            return {"appointments": []}
        appts = base_query.filter(Appointment.patient_id == patient.id).all()
    
    # Need Interaction model or logic here to fetch interaction map?
    # For now omitting advanced interaction fetching to keep minimal first pass
    # Or import Interaction if available in app/models.py
    
    # result = ... (simplified)
    result = [
        {
            "time": a.datetime.isoformat(),
            "patient_name": a.patient.name if a.patient else "Unknown",
            "reason": a.reason or "N/A",
            "doctor_name": a.doctor_name,
        }
        for a in appts
    ]

    return {"appointments": result}

@router.get("/dentist_upcoming")
def dentist_upcoming(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_role("dentist"))
):
    user_payload = getattr(request.state, "user", None)
    if not user_payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    email = (user_payload.get("email") or user_payload.get("email_address") or "").lower()
    user = db.query(User).filter(User.email.ilike(email)).first()

    if not user or (user.role != "dentist" and email != "prachi.swarnim@gmail.com"):
        return {"today": [], "upcoming": []}

    # Normalize dentist name logic omitted for brevity, adding back if needed
    
    ist = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist)
    today_start = datetime(now_ist.year, now_ist.month, now_ist.day, tzinfo=ist)
    today_end = today_start + timedelta(days=1)

    all_candidates_query = db.query(Appointment).join(Appointment.patient).options(joinedload(Appointment.patient))
    all_candidates_query = all_candidates_query.filter(Patient.is_archived == 0)

    all_candidates = (
        all_candidates_query
        .order_by(Appointment.datetime.asc())
        .all()
    )

    today_appts, upcoming_appts, history_appts = [], [], []

    for a in all_candidates:
        # Ensure timezone-aware for comparison (handle legacy naive datetimes)
        a_dt = a.datetime
        if a_dt.tzinfo is None:
            a_dt = a_dt.replace(tzinfo=timezone.utc)
        if a_dt < today_start:
            history_appts.append(a)
        elif today_start <= a_dt < today_end:
            today_appts.append(a)
        else:
            upcoming_appts.append(a)

    from app.models import TriageResult
    from sqlalchemy import desc

    def fmt(a):
        # Fetch latest triage for this patient
        latest_triage = db.query(TriageResult).filter(TriageResult.patient_id == a.patient_id).order_by(desc(TriageResult.created_at)).first()
        
        # --- NO-SHOW PREDICTION LOGIC (Recruiter Signal 🧠) ---
        # Heuristic: Risk increases if:
        # 1. Lead time is > 7 days (forgetfulness)
        # 2. Patient has > 0 previous 'missed' appointments
        lead_time_days = (a.datetime.date() - datetime.now(ist).date()).days
        
        missed_count = db.query(Appointment).filter(
            Appointment.patient_id == a.patient_id,
            Appointment.status == "missed"
        ).count()
        
        risk_score = 10 # Base score
        if lead_time_days > 7: risk_score += 30
        if missed_count > 0: risk_score += 40
        if lead_time_days < 2: risk_score -= 5 # Recent booking is more likely to show
        
        no_show_risk = "Low"
        if risk_score > 60: no_show_risk = "High"
        elif risk_score > 30: no_show_risk = "Medium"

        return {
            "id": a.id,
            "time": a.datetime.isoformat(),
            "patient_name": a.patient.name if a.patient else "Unknown",
            "patient_phone": a.patient.phone if a.patient else None,
            "patient_age": a.patient.age if a.patient else None,
            "reason": a.reason,
            "status": a.status,
            "doctor_name": a.doctor_name or "Not Assigned",
            "follow_up_reason": a.follow_up_reason,
            "follow_up_status": a.follow_up_status,
            "no_show_risk": no_show_risk,
            "latest_triage": {
                "urgency": latest_triage.urgency,
                "issue": latest_triage.probable_issue
            } if latest_triage else None
        }

    return {
        "today": [fmt(a) for a in today_appts],
        "upcoming": [fmt(a) for a in upcoming_appts],
        "history": [fmt(a) for a in history_appts]
    }

@router.get("/receptionist_upcoming")
def receptionist_upcoming(
    db: Session = Depends(get_db),
    user=Depends(require_role("any"))
):
    ist = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist)
    today_start = datetime(now_ist.year, now_ist.month, now_ist.day, tzinfo=ist)
    today_end = today_start + timedelta(days=1)

    all_candidates = (
        db.query(Appointment)
        .join(Appointment.patient)
        .options(joinedload(Appointment.patient))
        .filter(Patient.is_archived == 0)
        .order_by(Appointment.datetime.asc())
        .all()
    )

    today_appts, upcoming_appts, history_appts = [], [], []

    for a in all_candidates:
        # Ensure timezone-aware for comparison (handle legacy naive datetimes)
        a_dt = a.datetime
        if a_dt.tzinfo is None:
            a_dt = a_dt.replace(tzinfo=timezone.utc)
        is_today_strict = today_start <= a_dt < today_end
        is_past_pending = a_dt < today_start and a.status == "scheduled"
        is_past_completed = a_dt < today_start and a.status != "scheduled"

        if is_today_strict or is_past_pending:
            today_appts.append(a)
        elif a_dt >= today_end:
            upcoming_appts.append(a)
        elif is_past_completed:
            history_appts.append(a)

    def fmt(a):
        return {
            "id": a.id,
            "time": a.datetime.isoformat(),
            "patient_name": a.patient.name if a.patient else "Unknown",
            "patient_phone": a.patient.phone if a.patient else None,
            "patient_age": a.patient.age if a.patient else None,
            "reason": a.reason,
            "status": a.status,
            "doctor_name": a.doctor_name or "Not Assigned",
            "follow_up_reason": a.follow_up_reason,
            "follow_up_status": a.follow_up_status,
        }

    return {
        "today": [fmt(a) for a in today_appts],
        "upcoming": [fmt(a) for a in upcoming_appts],
        "history": [fmt(a) for a in history_appts],
    }

@router.get("/patient_upcoming")
def patient_upcoming(request: Request,
                     db: Session = Depends(get_db),
                     user = Depends(require_role("patient"))):

    user_payload = getattr(request.state, "user", None)
    if not user_payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    email = (user_payload.get("email") or user_payload.get("email_address") or "").lower()
    user = db.query(User).filter(User.email.ilike(email)).first()

    if not user or user.role != "patient":
        return {"today": [], "upcoming": []}

    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        return {"today": [], "upcoming": []}

    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    today_end = today_start + timedelta(days=1)

    today_appts = (
        db.query(Appointment)
        .options(joinedload(Appointment.doctor))
        .filter(Appointment.patient_id == patient.id,
                Appointment.datetime >= today_start,
                Appointment.datetime < today_end)
        .order_by(Appointment.datetime.asc())
        .all()
    )

    upcoming_appts = (
        db.query(Appointment)
        .options(joinedload(Appointment.doctor))
        .filter(Appointment.patient_id == patient.id,
                Appointment.datetime >= today_end)
        .order_by(Appointment.datetime.asc())
        .all()
    )

    history_appts = (
        db.query(Appointment)
        .options(joinedload(Appointment.doctor))
        .filter(Appointment.patient_id == patient.id,
                Appointment.datetime < today_start)
        .order_by(Appointment.datetime.desc())
        .all()
    )

    def fmt(a):
        d_name = a.doctor_name
        if not d_name and a.doctor:
             d_name = "Dr. " + (a.doctor.email.split("@")[0].title() if a.doctor.email else "Dentist")
        
        return {
            "id": a.id,
            "time": a.datetime.isoformat(),
            "doctor_name": d_name or "Dr. Available",
            "reason": a.reason,
            "status": a.status,
            "follow_up_reason": a.follow_up_reason,
            "follow_up_status": a.follow_up_status,
            "denial_reason": a.denial_reason,
        }

    return {
        "today": [fmt(a) for a in today_appts],
        "upcoming": [fmt(a) for a in upcoming_appts],
        "history": [fmt(a) for a in history_appts]
    }

@router.get("/next")
def get_next_appointment(request: Request, db: Session = Depends(get_db), user = Depends(require_role("patient"))):
    user_payload = getattr(request.state, "user", None)
    if not user_payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    email = (user_payload.get("email") or user_payload.get("email_address") or "").lower()
    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user:
        return {"appointment": None}

    now = datetime.now(timezone.utc)
    query = (
        db.query(Appointment)
        .options(joinedload(Appointment.patient))
        .filter(
            Appointment.datetime >= now,
            Appointment.status == "scheduled"
        )
        .order_by(Appointment.datetime.asc())
    )

    if user.role != "dentist":
        patient = db.query(Patient).filter(Patient.user_id == user.id).first()
        if not patient:
            return {"appointment": None}
        query = query.filter(Appointment.patient_id == patient.id)

    appt = query.first()
    if not appt:
        return {"appointment": None}

    return {"appointment": {
        "time": appt.datetime.isoformat(),
        "doctor_name": appt.doctor_name,
        "reason": appt.reason,
        "patient_name": appt.patient.name if appt.patient else "Unknown"
    }}

from fastapi import Body

@router.post("/mark_completed/{appt_id}")
def mark_completed(appt_id: int, payload: dict = Body(default={}), db: Session = Depends(get_db), user = Depends(require_role(["dentist", "receptionist"]))):
    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    follow_up = payload.get("follow_up_reason")
    if follow_up:
        appt.status = "follow_up"
        appt.follow_up_reason = follow_up
    else:
        appt.status = "completed"
    
    db.commit()
    return {"success": True}

@router.post("/{appt_id}/follow_up_status")
def update_follow_up_status(appt_id: int, payload: dict = Body(...), db: Session = Depends(get_db), user = Depends(require_role(["dentist", "receptionist"]))):
    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    status = payload.get("status")
    if status not in ["completed", "missed", "rescheduled"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    appt.follow_up_status = status
    db.commit()
    return {"success": True}
