from typing import Optional
from pydantic import BaseModel

class PatientUpdate(BaseModel):
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None

class ReceptionistPatientAdd(BaseModel):
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: str
    age: int
    datetime: str # Or datetime
    reason: str
    doctor_name: Optional[str] = None
    sex: Optional[str] = None
