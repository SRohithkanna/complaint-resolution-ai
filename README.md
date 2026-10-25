# Email ingestion (Dhanvanyaa)

Email in -> photo saved untouched -> EXIF extracted -> validation gate -> stored -> auto-reply.

## Setup (10 minutes)
1. `python -m venv .venv && source .venv/bin/activate` (Windows: `.venv\Scripts\activate`)
2. `pip install -r requirements.txt`
3. Create a NEW Gmail account for the project. Turn on 2-Step Verification, then create an
   App Password (Google Account -> Security -> App passwords). Gmail -> Settings -> Forwarding
   and POP/IMAP -> enable IMAP.
4. `cp .env.example .env` and fill in the address and app password.
5. `python -m pytest -q` -> all tests should pass (no inbox needed).
6. `DRY_RUN=1 python ingest.py --once` -> reads the inbox but only prints replies.
   Send yourself a test email from your phone with a photo attached, run it, and check
   `uploads/CMP-.../complaint.json`.
7. Remove DRY_RUN to send real replies. `python ingest.py` loops forever.

## Files
- `exif_utils.py` EXIF -> captured_at, gps, device, software
- `validator.py` the gate: REJECT_NO_PHOTO / REJECT_NO_TEXT / ACCEPT / ACCEPT_WEAK + flags
- `ingest.py` IMAP polling; `process_message()` holds the logic and is what tests call
- `mailer.py` SMTP replies; `storage.py` JSON stub, swap for Rohith's PostgreSQL insert
- `tests/` 10 tests using generated photos with and without EXIF

## Handing off to the team
- Rohith: replace `storage.save_complaint` with an insert into `complaints` + `evidence`
  (columns: has_exif, captured_at, gps_lat, gps_lon, device, software) + `evidence_quality`, `flags`.
- Ritika: the temporal/spatial checks read `flags` and the evidence rows.
