from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

class InvoiceItemCreate(BaseModel):
    treatment_name: str
    treatment_date: Optional[str] = None # format "YYYY-MM-DD"
    cost: float
    discount: float = 0.0

class PaymentRecordCreate(BaseModel):
    paid_on: Optional[str] = None # format "YYYY-MM-DD"
    payment_method: str
    amount: float

class InvoiceCreate(BaseModel):
    patient_name: str
    date: Optional[datetime] = None # Allow backdating
    invoice_number: Optional[str] = None
    currency: Optional[str] = "INR"
    discount: float = 0.0
    items: List[InvoiceItemCreate]
    payments: List[PaymentRecordCreate]
