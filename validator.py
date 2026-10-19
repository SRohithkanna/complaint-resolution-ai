"""Validation gate: runs BEFORE any agent. Decides what to do with an incoming email.

Outcomes (status):
  REJECT_NO_PHOTO   -> auto-reply, no complaint created
  REJECT_NO_TEXT    -> auto-reply, no complaint created
  ACCEPT            -> photo has usable EXIF, evidence_quality = "strong"
  ACCEPT_WEAK       -> photo has no EXIF (screenshot / stripped), quality = "weak"
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

import config

MIN_TEXT_CHARS = 15


@dataclass
class GateResult:
    status: str
    evidence_quality: str = "none"  # strong | weak | none
    flags: List[str] = field(default_factory=list)
    reply_reason: Optional[str] = None


def validate(body: str, photos: List[dict], received_at: datetime) -> GateResult:
    """photos: list of dicts returned by exif_utils.extract_exif (one per image)."""
    if len((body or "").strip()) < MIN_TEXT_CHARS:
        return GateResult("REJECT_NO_TEXT", reply_reason="no_text")
    if not photos:
        return GateResult("REJECT_NO_PHOTO", reply_reason="no_photo")

    flags: List[str] = []
    any_exif = any(p["has_exif"] for p in photos)
    any_time = any(p["captured_at"] for p in photos)
    any_gps = any(p["gps_lat"] is not None for p in photos)

    if not any_exif:
        flags.append("NO_EXIF")
    if any_exif and not any_time:
        flags.append("NO_TIMESTAMP")
    if any_exif and not any_gps:
        flags.append("NO_GPS")

    naive_received = received_at.replace(tzinfo=None)
    for p in photos:
        cap = p["captured_at"]
        if cap:
            if cap > naive_received + timedelta(hours=24):
                flags.append("PHOTO_FROM_FUTURE")
            if cap < naive_received - timedelta(days=config.MAX_PHOTO_AGE_DAYS):
                flags.append("PHOTO_STALE")
        sw = (p["software"] or "").lower()
        if any(k in sw for k in ("photoshop", "gimp", "lightroom", "snapseed", "picsart")):
            flags.append("EDITED_SOFTWARE")
        if p["has_exif"] and not p["device"]:
            flags.append("NO_DEVICE")

    flags = sorted(set(flags))
    if not any_exif or not any_time:
        return GateResult("ACCEPT_WEAK", "weak", flags, reply_reason="no_exif")
    quality = "weak" if {"PHOTO_FROM_FUTURE", "EDITED_SOFTWARE"} & set(flags) else "strong"
    return GateResult("ACCEPT", quality, flags)
