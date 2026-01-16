from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AppointmentUpdate(BaseModel):
    datetime: Optional[datetime] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    denial_reason: Optional[str] = None

class AppointmentCreate(BaseModel):
    datetime: datetime
    reason: Optional[str] = None
    doctor_id: Optional[int] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
