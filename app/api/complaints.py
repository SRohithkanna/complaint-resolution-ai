
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Complaint
from app.schemas import ComplaintCreate, ComplaintResponse

router = APIRouter(
    prefix="/api/complaints",
    tags=["Complaints"]
)


@router.post(
    "",
    response_model=ComplaintResponse,
    status_code=status.HTTP_201_CREATED
)
def create_complaint(
    complaint_data: ComplaintCreate,
    db: Session = Depends(get_db)
):
    complaint_code = (
        f"CMP-{datetime.now(timezone.utc).year}-{uuid4().hex[:8].upper()}"
    )

    complaint = Complaint(
        complaint_code=complaint_code,
        description=complaint_data.description,
        source=complaint_data.source,
        location=complaint_data.location,
        priority="medium",
        status="submitted"
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    return complaint


@router.get(
    "/{complaint_code}",
    response_model=ComplaintResponse
)
def get_complaint(
    complaint_code: str,
    db: Session = Depends(get_db)
):
    complaint = (
        db.query(Complaint)
        .filter(Complaint.complaint_code == complaint_code)
        .first()
    )

    if complaint is None:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found"
        )

    return complaint
