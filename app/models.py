
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database import Base


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    complaint_code = Column(String(30), unique=True, nullable=False)
    description = Column(Text, nullable=False)
    source = Column(String(20), default="text", nullable=False)
    location = Column(String(255), nullable=True)
    priority = Column(String(20), default="normal", nullable=False)
    status = Column(String(30), default="submitted", nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
