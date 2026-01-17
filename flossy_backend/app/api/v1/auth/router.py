from datetime import datetime, timezone
import requests
from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.orm import Session
from app.core.config import CLERK_SECRET_KEY
from app.core.database import get_db
from app.models import User, Patient

router = APIRouter()

from app.core.auth_utils import (
    get_automatic_role, 
    sync_clerk_role, 
    fetch_clerk_email, 
    sync_user_to_db
)

@router.post("/check_email")
def check_email(payload: dict, db: Session = Depends(get_db)):
    email = payload.get("email", "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    exists = db.query(User).filter(User.email.ilike(email)).first() is not None
    return {"exists": exists}

@router.post("/select_role")
def select_role(payload: dict, request: Request, db: Session = Depends(get_db)):
    user_payload = getattr(request.state, "user", None)
    if not user_payload:
        raise HTTPException(status_code=401, detail="Authentication required")

    user = sync_user_to_db(db, user_payload)
    if not user:
         raise HTTPException(status_code=400, detail="Sync failed")

    return {"success": True, "role": user.role, "email": user.email}

@router.post("/post_login")
def post_login(request: Request, db: Session = Depends(get_db)):
    user_payload = getattr(request.state, "user", None)
    if not user_payload:
        print("❌ post_login: No user in request.state")
        raise HTTPException(status_code=401, detail="Authentication required")

    print(f"🔄 post_login: Syncing user {user_payload.get('sub')}")
    user = sync_user_to_db(db, user_payload)
    if not user:
         print("❌ post_login: Sync failed")
         raise HTTPException(status_code=400, detail="Sync failed")

    print(f"✅ post_login: Success for {user.email} (role: {user.role})")
    return {"user": {"id": user.id, "email": user.email, "role": user.role}}


@router.get("/email_exists")
def email_exists(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email.ilike(email)).first()
    return {"exists": user is not None}
