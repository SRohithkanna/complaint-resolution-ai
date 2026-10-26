from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Complaint, Evidence
from app.schemas import ComplaintCreate, ComplaintResponse, EvidenceCreate

router = APIRouter(prefix="/api/complaints", tags=["Complaints"])


@router.post(
    "",
    response_model=ComplaintResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_complaint(
    complaint_data: ComplaintCreate,
    db: Session = Depends(get_db),
):
    complaint_code = (
        f"CMP-{datetime.now(timezone.utc).year}-"
        f"{uuid4().hex[:8].upper()}"
    )

    complaint = Complaint(
        complaint_code=complaint_code,
        description=complaint_data.description,
        source=complaint_data.source,
        location=complaint_data.location,
        priority="medium",
        status="submitted",
        sender_email=complaint_data.sender_email,
        email_subject=complaint_data.email_subject,
        evidence_quality=complaint_data.evidence_quality,
        validation_flags=complaint_data.validation_flags,
    )

    try:
        db.add(complaint)
        db.commit()
        db.refresh(complaint)
    except Exception:
        db.rollback()
        raise

    return complaint


@router.get("/{complaint_code}", response_model=ComplaintResponse)
def get_complaint(
    complaint_code: str,
    db: Session = Depends(get_db),
):
    complaint = (
        db.query(Complaint)
        .filter(Complaint.complaint_code == complaint_code)
        .first()
    )

    if complaint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )

    return complaint

from app.schemas import EvidenceCreate


@router.post("/{complaint_code}/evidence", status_code=status.HTTP_201_CREATED)
def create_evidence(
    complaint_code: str,
    evidence_data: EvidenceCreate,
    db: Session = Depends(get_db),
):
    complaint = (
        db.query(Complaint)
        .filter(Complaint.complaint_code == complaint_code)
        .first()
    )

    if complaint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )

    evidence = Evidence(
        complaint_id=complaint.id,
        filename=evidence_data.filename,
        stored_path=evidence_data.stored_path,
        captured_at=evidence_data.captured_at,
        camera_make=evidence_data.camera_make,
        camera_model=evidence_data.camera_model,
        latitude=evidence_data.latitude,
        longitude=evidence_data.longitude,
        metadata_status=evidence_data.metadata_status,
    )

    try:
        db.add(evidence)
        db.commit()
        db.refresh(evidence)
    except Exception:
        db.rollback()
        raise

    return {
        "message": "Evidence saved successfully",
        "evidence_id": evidence.id,
        "complaint_id": complaint.id,
        "complaint_code": complaint.complaint_code,
    }