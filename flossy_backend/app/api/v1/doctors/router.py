from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_
import re

from app.core.database import get_db
from app.models import User

router = APIRouter()

# Guaranteed doctors that must always appear in the dropdown
GUARANTEED_DOCTORS = [
    "Dr. Shagufta Jawaid",
    "Dr. Shruti Choudhary",
]

@router.get("/")
def get_doctors(db: Session = Depends(get_db)):
    # 1. Get all users with role 'dentist' OR specific admin email (case-insensitive)
    dentists = db.query(User).filter(
        or_(
            User.role == "dentist",
            User.email.ilike("prachi.swarnim@gmail.com")
        )
    ).all()
    
    doctor_names = set(GUARANTEED_DOCTORS)  # Start with guaranteed doctors
    from app.core.auth_utils import extract_names_from_email
    
    for d in dentists:
        # Use stored names if available
        if d.first_name:
            proper = f"{d.first_name} {d.last_name or ''}".strip()
        else:
            # Fallback to extraction
            fname, lname = extract_names_from_email(d.email)
            proper = f"{fname} {lname}".strip()
        
        # Add Prefix
        if not proper.lower().startswith("dr.") and not proper.lower().startswith("dr "):
             doctor_names.add(f"Dr. {proper}")
        else:
             doctor_names.add(proper)
        
    return {"doctors": sorted(list(doctor_names))}
