
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ComplaintCreate(BaseModel):
    description: str
    location: str | None = None
    source: str = "text"


class ComplaintResponse(BaseModel):
    id: int
    complaint_code: str
    description: str
    location: str | None
    source: str
    priority: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
