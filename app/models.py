from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

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

    # Additional complaint information
    sender_email = Column(String(255), nullable=True)
    email_subject = Column(String(255), nullable=True)
    evidence_quality = Column(String(30), nullable=True)
    validation_flags = Column(JSONB, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    evidence = relationship(
        "Evidence",
        back_populates="complaint",
        cascade="all, delete-orphan",
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)

    complaint_id = Column(
        Integer,
        ForeignKey("complaints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    filename = Column(String(255), nullable=False)
    stored_path = Column(Text, nullable=False)

    captured_at = Column(String(50), nullable=True)
    camera_make = Column(String(100), nullable=True)
    camera_model = Column(String(100), nullable=True)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    metadata_status = Column(String(30), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    complaint = relationship("Complaint", back_populates="evidence")


class GroundTruth(Base):
    __tablename__ = "ground_truth"

    id = Column(Integer, primary_key=True, index=True)

    case_id = Column(String(50), unique=True, nullable=False)

    complaint_id = Column(
        Integer,
        ForeignKey("complaints.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    expected_verdict = Column(String(30), nullable=False)
    reason = Column(Text, nullable=False)
    human_review_required = Column(Boolean, nullable=False, default=False)
    is_simulated = Column(Boolean, nullable=False, default=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    complaint = relationship("Complaint")