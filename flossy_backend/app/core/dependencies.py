from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import User

def require_role(expected_role):
    def _require_role(request: Request, db: Session = Depends(get_db)):
        payload = getattr(request.state, "user", None)
        if not payload:
            raise HTTPException(status_code=401, detail="Not authenticated")

        email = (payload.get("email") or payload.get("email_address") or "").lower()
        user = db.query(User).filter(User.email.ilike(email)).first()

        if not user:
            # AUTO-SYNC: Try to create user on the fly if they are missing from DB
            from app.core.auth_utils import sync_user_to_db
            user = sync_user_to_db(db, payload)
            if not user:
                raise HTTPException(status_code=403, detail="User not found in local database and sync failed")

        if expected_role != "any":
            # ALLOW dentists and receptionists to access "patient" endpoints 
            # (they will see their own patient profile if it exists)
            effective_expected = expected_role
            if expected_role == "patient":
                effective_expected = ["patient", "dentist", "receptionist"]
            
            if isinstance(effective_expected, list):
                if user.role not in effective_expected:
                    print(f"🔒 Role mismatch: User {user.email} has role '{user.role}', but needs '{effective_expected}'")
                    raise HTTPException(status_code=403, detail=f"Insufficient permissions (Needs {effective_expected})")
            elif user.role != effective_expected:
                print(f"🔒 Role mismatch: User {user.email} has role '{user.role}', but needs '{effective_expected}'")
                raise HTTPException(status_code=403, detail=f"Insufficient permissions (Needs {effective_expected})")

        return user



    return _require_role
