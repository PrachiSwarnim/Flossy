from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_
import re

from core.database import get_db
from models import User

router = APIRouter()

@router.get("/")
def get_doctors(db: Session = Depends(get_db)):
    # 1. Get all users with role 'dentist' OR specific admin email (case-insensitive)
    dentists = db.query(User).filter(
        or_(
            User.role == "dentist",
            User.email.ilike("prachi.swarnim@gmail.com")
        )
    ).all()
    
    doctor_names = []
    for d in dentists:
        # 1. Use email prefix as source
        if not d.email: continue
        raw_name = d.email.split("@")[0]

        # Cleanup: Remove digits (e.g. shruti01 -> shruti), replace dots/underscores
        clean = re.sub(r'\d+', '', raw_name)
        clean = clean.replace(".", " ").replace("_", " ").replace("-", " ").strip()
        
        parts = clean.split()
        if len(parts) == 2:
            # Special logic:
            # - prachi.swarnim@... -> Prachi Swarnim (Do not swap)
            # - choudhary.shruti@... -> Shruti Choudhary (Swap)
            p1 = parts[0].lower()
            p2 = parts[1].lower()

            if p1 == "choudhary" and p2 == "shruti":
                # Known inverted case
                proper = f"{parts[1].capitalize()} {parts[0].capitalize()}"
            else:
                # Default: Don't swap (assume firstname.lastname)
                proper = f"{parts[0].capitalize()} {parts[1].capitalize()}"
        else:
            proper = " ".join(p.capitalize() for p in parts)
        
        # Add Prefix
        if not proper.lower().startswith("dr.") and not proper.lower().startswith("dr "):
             doctor_names.append(f"Dr. {proper}")
        else:
             doctor_names.append(proper)
        
    return {"doctors": sorted(list(set(doctor_names)))} # Unique & Sorted
