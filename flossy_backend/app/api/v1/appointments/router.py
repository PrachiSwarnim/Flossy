from datetime import datetime, timezone, timedelta
import re
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from core.database import get_db
from core.dependencies import require_role
from models import Appointment, User, Patient
from .schemas import AppointmentUpdate

router = APIRouter()

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
    
    # 3. Explicitly update the reason
    if appointment_update.reason:
        db_appointment.reason = appointment_update.reason 

    # 4. Commit changes
    db.commit()
    db.refresh(db_appointment)
    
    return {"message": "Appointment updated successfully", "appointment": {
        "id": db_appointment.id,
        "reason": db_appointment.reason,
        "status": db_appointment.status,
        "time": db_appointment.datetime.isoformat()
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
        if a.datetime < today_start:
            history_appts.append(a)
        elif today_start <= a.datetime < today_end:
            today_appts.append(a)
        else:
            upcoming_appts.append(a)

    def fmt(a):
        return {
            "id": a.id,
            "time": a.datetime.isoformat(),
            "patient_name": a.patient.name if a.patient else "Unknown",
            "patient_phone": a.patient.phone if a.patient else None,
            "patient_age": a.patient.age if a.patient else None,
            "reason": a.reason,
            "status": a.status,
            "follow_up_reason": a.follow_up_reason,
            "follow_up_status": a.follow_up_status,
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
        is_today_strict = today_start <= a.datetime < today_end
        is_past_pending = a.datetime < today_start and a.status == "scheduled"
        is_past_completed = a.datetime < today_start and a.status != "scheduled"

        if is_today_strict or is_past_pending:
            today_appts.append(a)
        elif a.datetime >= today_end:
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
