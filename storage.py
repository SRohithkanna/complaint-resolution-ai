"""Storage layer. Rohith owns the real PostgreSQL schema; until it is ready this
writes one JSON file per complaint. Swap `save_complaint` for a DB insert later --
nothing else in the project needs to change."""
import json
import os
import re
import uuid
from datetime import datetime

import config


def new_complaint_code() -> str:
    return "CMP-" + datetime.now().strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6].upper()


def save_photo(code: str, filename: str, payload: bytes) -> str:
    """Save ORIGINAL bytes untouched (re-encoding would strip EXIF)."""
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", filename or "photo.jpg")
    folder = os.path.join(config.UPLOAD_DIR, code)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, safe)
    with open(path, "wb") as f:
        f.write(payload)
    return path

def metadata_status(exif: dict) -> str:
    """complete = time + GPS + camera all present; missing = none of them; else partial."""
    found = [
        exif.get("captured_at") is not None,
        exif.get("gps_lat") is not None and exif.get("gps_lon") is not None,
        bool(exif.get("camera_make") or exif.get("camera_model")),
    ]
    if all(found):
        return "complete"
    return "partial" if any(found) else "missing"


def evidence_row(evidence_id: int, filename: str, path: str, exif: dict) -> dict:
    """One entry of the `evidence` list in complaint.json."""
    captured = exif.get("captured_at")
    return {
        "id": evidence_id,
        "filename": filename,
        "stored_path": os.path.abspath(path),
        "captured_at": captured.strftime("%Y:%m:%d %H:%M:%S") if captured else None,
        "gps": {"latitude": exif.get("gps_lat"), "longitude": exif.get("gps_lon")},
        "camera_make": exif.get("camera_make"),
        "camera_model": exif.get("camera_model"),
        "metadata_status": metadata_status(exif),
        "created_at": datetime.now().astimezone().isoformat(),
    }


def next_complaint_id() -> int:
    """Stand-in for a DB serial: count saved complaints + 1. Rohith's table replaces this."""
    if not os.path.isdir(config.UPLOAD_DIR):
        return 1
    done = sum(
        os.path.exists(os.path.join(config.UPLOAD_DIR, d, "complaint.json"))
        for d in os.listdir(config.UPLOAD_DIR)
    )
    return done + 1

def save_complaint(record: dict) -> None:
    if record.get("complaint_id") is None:
        record["complaint_id"] = next_complaint_id()

    record["evidence_count"] = len(record["evidence"])
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    path = os.path.join(config.UPLOAD_DIR, record["complaint_code"], "complaint.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(record, f, indent=2, default=str)
