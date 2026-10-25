"""Email ingestion: poll inbox -> save photos -> EXIF -> validation gate -> store -> reply.

Run:  python ingest.py            (loops forever)
      python ingest.py --once     (single pass, good for testing)
Set DRY_RUN=1 to print replies instead of sending them.
"""
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
    """Core logic, independent of IMAP so it can be unit-tested.

    attachments: list of (filename, bytes). Returns a result dict.
    """
    code = storage.new_complaint_code()
    photos, photo_rows = [], []

    for filename, payload in attachments:
        ext = os.path.splitext(filename or "")[1].lower()
        if ext not in config.IMAGE_EXTENSIONS or len(payload) > config.MAX_ATTACHMENT_BYTES:
            continue
        path = storage.save_photo(code, filename, payload)
        exif = extract_exif(path)
        photos.append(exif)
        photo_rows.append(storage.evidence_row(len(photo_rows) + 1, filename, path, exif))

    gate = validate(body, photos, received_at)

    if gate.status.startswith("REJECT"):
        mailer.send_template(sender, gate.reply_reason)
        return {"accepted": False, "status": gate.status}

    storage.save_complaint({
        "complaint_code": code,
        "user_email": sender,
        "subject": subject,
        "raw_text": body.strip(),
        "channel": "email",
        "received_at": received_at,
        "evidence_quality": gate.evidence_quality,
        "flags": gate.flags,
        "evidence": photo_rows,
    })
    mailer.send_template(sender, "no_exif" if gate.reply_reason == "no_exif" else "received", code)
    return {"accepted": True, "code": code, "status": gate.status, "flags": gate.flags}


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
