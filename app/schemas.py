from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ComplaintCreate(BaseModel):
    description: str
    location: str | None = None
    source: str = "text"
    sender_email: str | None = None
    email_subject: str | None = None
    evidence_quality: str | None = None
    validation_flags: list[str] | None = None


class ComplaintResponse(BaseModel):
    id: int
    complaint_code: str
    description: str
    location: str | None
    source: str
    priority: str
    status: str
    sender_email: str | None = None
    email_subject: str | None = None
    evidence_quality: str | None = None
    validation_flags: list[str] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
class EvidenceCreate(BaseModel):
    filename: str
    stored_path: str
    captured_at: str | None = None
    camera_make: str | None = None
    camera_model: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    metadata_status: str | None = None