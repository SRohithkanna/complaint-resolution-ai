import os
from dotenv import load_dotenv

load_dotenv()

IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_USER = os.getenv("IMAP_USER", "")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "30"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tiff"}
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024
# Photos older than this (relative to the email) are flagged as stale evidence
MAX_PHOTO_AGE_DAYS = 7
