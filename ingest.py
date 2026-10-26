"""Email ingestion: poll inbox -> save photos -> EXIF -> validation gate -> store -> reply.

Run:  python ingest.py            (loops forever)
      python ingest.py --once     (single pass, good for testing)
Set DRY_RUN=1 to print replies instead of sending them.
"""
import requests
import argparse
import os
import sys
import time
from datetime import datetime

from imap_tools import AND, MailBox

import config
import mailer
import storage
from exif_utils import extract_exif
from validator import validate



def process_message(sender: str, subject: str, body: str, attachments: list, received_at: datetime) -> dict:
    """Validate an email complaint, register it through FastAPI, and preserve evidence locally."""

    photos, photo_rows = [], []

    # Use a temporary identifier for storing photos before the backend
    # generates the official complaint code.
    temporary_code = storage.new_complaint_code()

    for filename, payload in attachments:
        ext = os.path.splitext(filename or "")[1].lower()

        if ext not in config.IMAGE_EXTENSIONS or len(payload) > config.MAX_ATTACHMENT_BYTES:
            continue

        path = storage.save_photo(temporary_code, filename, payload)
        exif = extract_exif(path)

        photos.append(exif)
        photo_rows.append(
            storage.evidence_row(len(photo_rows) + 1, filename, path, exif)
        )

    gate = validate(body, photos, received_at)

    if gate.status.startswith("REJECT"):
        mailer.send_template(sender, gate.reply_reason)
        return {"accepted": False, "status": gate.status}

    # Register the accepted complaint through the PostgreSQL-backed API.
    api_base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    description = body.strip()

    # Register the complaint and its email-related metadata in PostgreSQL.
    response = requests.post(
        f"{api_base_url}/api/complaints",
        json={
            "description": description,
            "location": None,
            "source": "email",
            "sender_email": sender,
            "email_subject": subject,
            "evidence_quality": gate.evidence_quality,
            "validation_flags": gate.flags,
        },
        timeout=15,
    )

    response.raise_for_status()
    api_result = response.json()

    # Use the official complaint code returned by FastAPI/PostgreSQL.
    code = api_result["complaint_code"]

    # Move the locally saved evidence from its temporary folder to the
    # official complaint-code folder.
    temporary_folder = os.path.join(config.UPLOAD_DIR, temporary_code)
    official_folder = os.path.join(config.UPLOAD_DIR, code)

    if os.path.isdir(temporary_folder):
        if os.path.exists(official_folder):
            raise FileExistsError(
                f"Evidence folder already exists for complaint {code}"
            )
        os.replace(temporary_folder, official_folder)

    # Update evidence paths after moving the folder.
    for row in photo_rows:
        row["stored_path"] = os.path.abspath(
            os.path.join(
                official_folder,
                os.path.basename(row["stored_path"]),
            )
        )

    # Save each photo's metadata in PostgreSQL.
    for row in photo_rows:
        gps = row.get("gps") or {}

        evidence_payload = {
            "filename": row["filename"],
            "stored_path": row["stored_path"],
            "captured_at": row.get("captured_at"),
            "camera_make": row.get("camera_make"),
            "camera_model": row.get("camera_model"),
            "latitude": gps.get("latitude"),
            "longitude": gps.get("longitude"),
            "metadata_status": row.get("metadata_status"),
        }

        evidence_response = requests.post(
            f"{api_base_url}/api/complaints/{code}/evidence",
            json=evidence_payload,
            timeout=15,
        )
        evidence_response.raise_for_status()

    # Preserve ingestion-specific details locally. PostgreSQL remains the
    # source of truth for the registered complaint itself.
    storage.save_complaint({
        "complaint_code": code,
        "complaint_id": api_result["id"],
        "user_email": sender,
        "subject": subject,
        "raw_text": description,
        "channel": "email",
        "received_at": received_at,
        "evidence_quality": gate.evidence_quality,
        "flags": gate.flags,
        "evidence": photo_rows,
    })

    mailer.send_template(
        sender,
        "no_exif" if gate.reply_reason == "no_exif" else "received",
        code,
    )

    return {
        "accepted": True,
        "code": code,
        "complaint_id": api_result["id"],
        "status": gate.status,
        "flags": gate.flags,
    }

def poll_once(box: MailBox) -> int:
    handled = 0
    # mark_seen=True so each email is processed exactly once
    for msg in box.fetch(AND(seen=False), mark_seen=True):
        try:
            atts = [(a.filename, a.payload) for a in msg.attachments]
            res = process_message(msg.from_, msg.subject, msg.text or "", atts, msg.date)
            print(f"[{datetime.now():%H:%M:%S}] {msg.from_} -> {res}")
        except Exception as e:  # one bad email must not kill the loop
            print(f"ERROR processing uid={msg.uid}: {e!r}", file=sys.stderr)
        handled += 1
    return handled


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.dry_run:
        os.environ["DRY_RUN"] = "1"
    if not config.IMAP_USER or not config.IMAP_PASSWORD:
        sys.exit("Set IMAP_USER and IMAP_PASSWORD in .env first (see .env.example)")

    while True:
        try:
            with MailBox(config.IMAP_HOST).login(config.IMAP_USER, config.IMAP_PASSWORD) as box:
                poll_once(box)
        except Exception as e:  # network blip etc: log, wait, retry
            print(f"Connection error: {e!r}", file=sys.stderr)
        if args.once:
            break
        time.sleep(config.POLL_SECONDS)


if __name__ == "__main__":
    main()
