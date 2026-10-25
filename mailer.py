"""Outbound email (SMTP over SSL). Set DRY_RUN=1 to print instead of sending."""
import os
import smtplib
from email.message import EmailMessage

import config

TEMPLATES = {
    "no_photo": (
        "We need a photo to process your complaint",
        "Hello,\n\nWe received your complaint but it had no photo attached. "
        "Please reply with the ORIGINAL photo as an attachment (not a screenshot, "
        "not forwarded from WhatsApp), taken at actual size with location enabled "
        "on your phone camera.\n\nThank you.",
    ),
    "no_text": (
        "Please describe your complaint",
        "Hello,\n\nWe received your email but the body was empty or too short. "
        "Please describe the problem (what, where, since when) in the email text "
        "and attach the photo again.\n\nThank you.",
    ),
    "no_exif": (
        "Complaint received - photo lacks metadata",
        "Hello,\n\nYour complaint {code} has been registered. However, the photo has no "
        "date/location metadata (likely a screenshot or a forwarded copy), so it "
        "carries less weight in verification. If you can, reply with the original "
        "photo attached at actual size with location enabled.\n\nThank you.",
    ),
    "received": (
        "Complaint received: {code}",
        "Hello,\n\nYour complaint has been registered with ID {code}. "
        "You can use this ID to track its status.\n\nThank you.",
    ),
}


def send_template(to_addr: str, key: str, code: str = "") -> None:
    subject, body = TEMPLATES[key]
    send(to_addr, subject.format(code=code), body.format(code=code))


def send(to_addr: str, subject: str, body: str) -> None:
    if os.getenv("DRY_RUN") == "1":
        print(f"[DRY_RUN] to={to_addr} subject={subject!r}")
        return
    msg = EmailMessage()
    msg["From"] = config.IMAP_USER
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT) as s:
        s.login(config.IMAP_USER, config.IMAP_PASSWORD)
        s.send_message(msg)
