from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class PrescriptionCreate(BaseModel):
    patient_name: str
    details: Optional[str] = None # Will be used as "Chief Complaint"
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    recommendations: Optional[str] = None
    created_at: Optional[datetime] = None # Allow backdating
    continue_prescription_id: Optional[int] = None # If set, this is a continuation of that prescription

class PrescriptionUpdate(BaseModel):
    details: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    recommendations: Optional[str] = None
    created_at: Optional[datetime] = None
