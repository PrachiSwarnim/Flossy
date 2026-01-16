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
            raise HTTPException(status_code=403, detail="User not found in local database")

        if expected_role != "any":
            if isinstance(expected_role, list):
                if user.role not in expected_role:
                    raise HTTPException(status_code=403, detail="Insufficient permissions")
            elif user.role != expected_role:
                raise HTTPException(status_code=403, detail="Insufficient permissions")

        return user

    return _require_role
