import io
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DRY_RUN"] = "1"  # never send real mail in tests

import pytest
from PIL import Image

import config
import ingest
from exif_utils import extract_exif
from validator import validate


def make_jpeg(with_exif=True, taken="2026:10:14 10:00:00", gps=True, software=None) -> bytes:
    img = Image.new("RGB", (64, 64), "gray")
    buf = io.BytesIO()
    if not with_exif:
        img.save(buf, "JPEG")
        return buf.getvalue()
    exif = Image.Exif()
    exif[0x010F] = "Apple"
    exif[0x0110] = "iPhone 13"
    if software:
        exif[0x0131] = software
    exif.get_ifd(0x8769)[0x9003] = taken
    if gps:
        g = exif.get_ifd(0x8825)
        g[1], g[2], g[3], g[4] = "N", (13.0, 3.0, 36.0), "E", (80.0, 15.0, 0.0)
    img.save(buf, "JPEG", exif=exif)
    return buf.getvalue()


@pytest.fixture(autouse=True)
def tmp_uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "UPLOAD_DIR", str(tmp_path))


def write(tmp_path, data, name="p.jpg"):
    p = tmp_path / name
    p.write_bytes(data)
    return str(p)


def test_exif_extracted(tmp_path):
    e = extract_exif(write(tmp_path, make_jpeg()))
    assert e["has_exif"] and e["device"] == "Apple iPhone 13"
    assert e["captured_at"] == datetime(2026, 10, 14, 10, 0, 0)
    assert abs(e["gps_lat"] - 13.06) < 1e-6 and abs(e["gps_lon"] - 80.25) < 1e-6


def test_no_exif(tmp_path):
    assert extract_exif(write(tmp_path, make_jpeg(with_exif=False)))["has_exif"] is False


def test_garbage_file_does_not_crash(tmp_path):
    assert extract_exif(write(tmp_path, b"not an image"))["has_exif"] is False


RECV = datetime(2026, 10, 14, 12, 0, 0)
GOOD = {"has_exif": True, "captured_at": datetime(2026, 10, 14, 10, 0), "gps_lat": 1.0,
        "gps_lon": 1.0, "device": "Apple iPhone", "software": None}


def test_gate_rejects_no_photo():
    assert validate("Streetlight broken near gate 2", [], RECV).status == "REJECT_NO_PHOTO"


def test_gate_rejects_short_text():
    assert validate("broken", [GOOD], RECV).status == "REJECT_NO_TEXT"


def test_gate_accepts_strong():
    r = validate("Streetlight broken near gate 2 since Monday", [GOOD], RECV)
    assert r.status == "ACCEPT" and r.evidence_quality == "strong" and r.flags == []


def test_gate_weak_without_exif():
    p = {**GOOD, "has_exif": False, "captured_at": None, "gps_lat": None, "device": None}
    r = validate("Streetlight broken near gate 2 since Monday", [p], RECV)
    assert r.status == "ACCEPT_WEAK" and "NO_EXIF" in r.flags


def test_gate_flags_stale_edited_future():
    old = {**GOOD, "captured_at": datetime(2026, 1, 1)}
    assert "PHOTO_STALE" in validate("x" * 30, [old], RECV).flags
    ed = {**GOOD, "software": "Adobe Photoshop 25"}
    r = validate("x" * 30, [ed], RECV)
    assert "EDITED_SOFTWARE" in r.flags and r.evidence_quality == "weak"
    fut = {**GOOD, "captured_at": datetime(2027, 1, 1)}
    assert "PHOTO_FROM_FUTURE" in validate("x" * 30, [fut], RECV).flags


def test_end_to_end_process_message(tmp_path):
    res = ingest.process_message("a@b.com", "Complaint", "Projector in Room 204 is broken since yesterday",
                                 [("IMG_1.jpg", make_jpeg())], RECV)
    assert res["accepted"] and res["status"] == "ACCEPT"
    saved = tmp_path / res["code"]
    assert (saved / "complaint.json").exists() and (saved / "IMG_1.jpg").exists()
    # stored original must still carry EXIF (proves we never re-encoded it)
    assert extract_exif(str(saved / "IMG_1.jpg"))["has_exif"]


def test_end_to_end_rejects_without_photo():
    res = ingest.process_message("a@b.com", "x", "Projector in Room 204 is broken", [], RECV)
    assert res == {"accepted": False, "status": "REJECT_NO_PHOTO"}
