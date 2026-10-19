"""EXIF extraction. IMPORTANT: always call this on the ORIGINAL saved bytes.
Re-saving an image with Pillow strips EXIF, so never resize/convert before this."""
from datetime import datetime
from typing import Optional

from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS
import warnings
from datetime import datetime
from typing import Optional

try:
    import pillow_heif  # iPhones send HEIC

    pillow_heif.register_heif_opener()
except ImportError:  # HEIC just won't open
    pass

EXIF_IFD = 0x8769
GPS_IFD = 0x8825


def _to_degrees(value, ref) -> Optional[float]:
    """Convert EXIF (deg, min, sec) rationals to signed decimal degrees."""
    try:
        d, m, s = (float(x) for x in value)
        dec = d + m / 60.0 + s / 3600.0
        return -dec if ref in ("S", "W") else dec
    except (TypeError, ValueError, ZeroDivisionError):
        return None

def _clean(value) -> Optional[str]:
    """EXIF strings often carry trailing NULs/spaces."""
    if value is None:
        return None
    return str(value).replace("\x00", "").strip() or None


def _parse_dt(raw) -> Optional[datetime]:
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw).strip(), "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None


def extract_exif(path: str) -> dict:
    """Return a flat dict. Never raises: unreadable files give has_exif=False."""
    empty = {
        "has_exif": False,
        "captured_at": None,
        "gps_lat": None,
        "gps_lon": None,
        "camera_make": None,
        "camera_model": None,
        "device": None,
        "device": None,
        "software": None,
    }
    old_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", Image.DecompressionBombWarning)
            img = Image.open(path)
            raw = img.getexif()
    except Exception:
        return empty
    finally:
        Image.MAX_IMAGE_PIXELS = old_limit
    if not raw:
        return empty

    base = {TAGS.get(k, k): v for k, v in raw.items()}
    try:
        exif_ifd = {TAGS.get(k, k): v for k, v in raw.get_ifd(EXIF_IFD).items()}
    except Exception:
        exif_ifd = {}
    try:
        gps = {GPSTAGS.get(k, k): v for k, v in raw.get_ifd(GPS_IFD).items()}
    except Exception:
        gps = {}

    lat = lon = None
    if gps.get("GPSLatitude") and gps.get("GPSLongitude"):
        lat = _to_degrees(gps["GPSLatitude"], gps.get("GPSLatitudeRef"))
        lon = _to_degrees(gps["GPSLongitude"], gps.get("GPSLongitudeRef"))

    make, model = _clean(base.get("Make")), _clean(base.get("Model"))
    device = " ".join(x for x in (make, model) if x) or None
    captured = _parse_dt(exif_ifd.get("DateTimeOriginal") or base.get("DateTime"))

    return {
        "has_exif": True,
        "captured_at": captured,
        "gps_lat": lat,
        "gps_lon": lon,
        "camera_make": make,
        "camera_model": model,
        "device": device,
        "device": device,
        "software": base.get("Software"),
    }
