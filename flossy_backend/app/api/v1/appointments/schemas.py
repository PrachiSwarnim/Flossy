from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AppointmentUpdate(BaseModel):
    datetime: Optional[datetime]
    status: Optional[str]
    reason: Optional[str]
