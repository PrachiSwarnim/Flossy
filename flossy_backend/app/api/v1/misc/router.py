from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import TreatmentCatalog

router = APIRouter()

@router.get("/treatments")
def get_treatment_catalog(db: Session = Depends(get_db)):
    """Fetches the list of standard dental treatments and their default costs."""
    catalog = db.query(TreatmentCatalog).all()
    return {
        "treatments": [
            {"id": t.id, "name": t.name, "cost": t.default_cost, "category": t.category} 
            for t in catalog
        ]
    }
