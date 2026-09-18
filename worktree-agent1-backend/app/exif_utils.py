"""EXIF extraction helpers (DateTimeOriginal, GPS) using Pillow. No network/model calls."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import ExifTags, Image
from PIL.ExifTags import GPSTAGS

_TAG_NAME_TO_ID = {name: tag_id for tag_id, name in ExifTags.TAGS.items()}
DATETIME_ORIGINAL_TAG = _TAG_NAME_TO_ID.get("DateTimeOriginal")
GPSINFO_TAG = _TAG_NAME_TO_ID.get("GPSInfo")
EXIF_IFD_TAG = _TAG_NAME_TO_ID.get("ExifOffset")  # 0x8769, points to the Exif SubIFD


def _to_degrees(value) -> float:
    d, m, s = value
    return float(d) + float(m) / 60.0 + float(s) / 3600.0


def extract_datetime_and_gps(image_path: Path) -> tuple[Optional[datetime], Optional[tuple[float, float]]]:
    """Returns (taken_at, (lat, lon)) — either may be None if absent/unparseable."""
    taken_at: Optional[datetime] = None
    gps: Optional[tuple[float, float]] = None
    try:
        with Image.open(image_path) as img:
            exif = img.getexif()
            if not exif:
                return None, None

            raw = None
            if DATETIME_ORIGINAL_TAG and DATETIME_ORIGINAL_TAG in exif:
                raw = exif[DATETIME_ORIGINAL_TAG]
            elif EXIF_IFD_TAG:
                try:
                    exif_sub_ifd = exif.get_ifd(EXIF_IFD_TAG)
                    raw = exif_sub_ifd.get(DATETIME_ORIGINAL_TAG)
                except (KeyError, AttributeError):
                    raw = None
            if raw:
                try:
                    taken_at = datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
                except (ValueError, TypeError):
                    taken_at = None

            gps_ifd = None
            if GPSINFO_TAG:
                try:
                    gps_ifd = exif.get_ifd(GPSINFO_TAG)
                except (KeyError, AttributeError):
                    gps_ifd = None
            if gps_ifd:
                named = {GPSTAGS.get(k, k): v for k, v in gps_ifd.items()}
                lat = named.get("GPSLatitude")
                lat_ref = named.get("GPSLatitudeRef")
                lon = named.get("GPSLongitude")
                lon_ref = named.get("GPSLongitudeRef")
                if lat and lon and lat_ref and lon_ref:
                    lat_deg = _to_degrees(lat)
                    lon_deg = _to_degrees(lon)
                    if lat_ref in ("S", "s"):
                        lat_deg = -lat_deg
                    if lon_ref in ("W", "w"):
                        lon_deg = -lon_deg
                    gps = (lat_deg, lon_deg)
    except Exception:
        return None, None

    return taken_at, gps
