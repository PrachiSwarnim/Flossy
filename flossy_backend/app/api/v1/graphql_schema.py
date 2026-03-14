
import strawberry
from typing import List, Optional
from app.core.database import SessionLocal
from app.models import Patient, Appointment

@strawberry.type
class PatientType:
    id: int
    name: str
    phone: str
    age: Optional[int]
    source: Optional[str]

@strawberry.type
class AppointmentType:
    id: int
    patient_id: int
    datetime: str
    status: str
    doctor_name: Optional[str]

@strawberry.type
class Query:
    @strawberry.field
    def patients(self, name_contains: Optional[str] = None) -> List[PatientType]:
        db = SessionLocal()
        try:
            query = db.query(Patient)
            if name_contains:
                query = query.filter(Patient.name.ilike(f"%{name_contains}%"))
            return [PatientType(id=p.id, name=p.name, phone=p.phone, age=p.age, source=p.source) for p in query.all()]
        finally:
            db.close()

    @strawberry.field
    def appointments(self, status: Optional[str] = None) -> List[AppointmentType]:
        db = SessionLocal()
        try:
            query = db.query(Appointment)
            if status:
                query = query.filter(Appointment.status == status)
            return [AppointmentType(
                id=a.id, 
                patient_id=a.patient_id, 
                datetime=a.datetime.isoformat(), 
                status=a.status,
                doctor_name=a.doctor_name
            ) for a in query.all()]
        finally:
            db.close()

schema = strawberry.Schema(query=Query)
