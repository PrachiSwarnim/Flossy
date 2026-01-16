from fastapi import APIRouter

from app.api.v1.auth.router import router as auth_router
from app.api.v1.appointments.router import router as appointments_router
from app.api.v1.patients.router import router as patients_router
from app.api.v1.prescriptions.router import router as prescriptions_router
from app.api.v1.invoices.router import router as invoices_router
from app.api.v1.misc.router import router as misc_router
from app.api.v1.doctors.router import router as doctors_router
from app.api.v1.receptionist.router import router as receptionist_router
from app.api.v1.ai.router import router as ai_router
from app.api.v1.public.router import router as public_router

api_router = APIRouter()

api_router.include_router(public_router, prefix="/v1/public", tags=["Public"])
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])

api_router.include_router(appointments_router, prefix="/appointments", tags=["Appointments"])
api_router.include_router(patients_router, prefix="/patients", tags=["Patients"])
api_router.include_router(receptionist_router, prefix="/receptionist", tags=["Receptionist"])
api_router.include_router(prescriptions_router, prefix="/prescriptions", tags=["Prescriptions"])
api_router.include_router(invoices_router, prefix="/invoices", tags=["Invoices"])
api_router.include_router(misc_router, prefix="", tags=["Misc"]) # Uses /treatments
api_router.include_router(doctors_router, prefix="/doctors", tags=["Doctors"]) # Uses / (so /api/doctors)

api_router.include_router(ai_router, prefix="", tags=["AI"])
