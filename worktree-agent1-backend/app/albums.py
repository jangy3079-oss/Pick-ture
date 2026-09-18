"""Album auto-classification: 2-stage clustering per shared/CONTRACT.md section 3-1.

Stage 1 (time-gap clustering): sort photos by EXIF DateTimeOriginal, start a new
"trip" whenever the gap between consecutive photos exceeds TRIP_GAP_HOURS.
Stage 2 (country re-classification): within each trip, reverse-geocode GPS
coordinates to a country and split the trip into one album per country. GPS-less
photos inherit the country of the nearest-in-time GPS-having photo in the same
trip. If a trip has no GPS at all, stage 2 is skipped and the trip becomes a
single album with country=None.

Calibration note (CONTRACT.md 6-1): checked against dataset/ (19 real photos,
Prague, spanning 2026-01-20 10:26 -> 2026-01-21 17:26, max gap ~19.5h between
consecutive shots) with the default 48h threshold -> correctly forms a single
trip/album. No evidence in the sample to justify a different default, so 48h
(the CONTRACT.md default) is kept as-is.

Assumption (undocumented edge case): CONTRACT.md only specifies nearest-neighbor
interpolation for GPS-less photos, not for photos with NO EXIF timestamp at all
(stage 1 input). Photos with no timestamp are appended, in upload order, to
whichever trip already has the most photos (the "main" trip) — reasonable
default for a demo dataset where a handful of screenshots/downloaded images
might have no EXIF at all. If there are no trips yet (all photos timestamp-less),
they all form a single trip together.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import reverse_geocode

from app.storage import AlbumRecord, PhotoRecord

TRIP_GAP_HOURS = 48


@dataclass
class _Trip:
    photos: list[PhotoRecord]


def _split_into_trips(photos: list[PhotoRecord]) -> list[_Trip]:
    timed = sorted((p for p in photos if p.taken_at), key=lambda p: p.taken_at)
    untimed = [p for p in photos if not p.taken_at]

    trips: list[_Trip] = []
    current: list[PhotoRecord] = []
    prev_dt: Optional[datetime] = None
    for photo in timed:
        dt = datetime.fromisoformat(photo.taken_at)
        if prev_dt is not None and dt - prev_dt > timedelta(hours=TRIP_GAP_HOURS):
            trips.append(_Trip(photos=current))
            current = []
        current.append(photo)
        prev_dt = dt
    if current:
        trips.append(_Trip(photos=current))

    if not trips:
        trips.append(_Trip(photos=[]))
    largest = max(trips, key=lambda t: len(t.photos))
    largest.photos.extend(untimed)

    return trips


def _reverse_geocode_country_city(lat: float, lon: float) -> tuple[str, str]:
    result = reverse_geocode.search([(lat, lon)])[0]
    return result["country"], result["city"]


def _apply_country_stage(trip_photos: list[PhotoRecord]) -> None:
    """Mutates trip_photos in place, setting .country and .city."""
    gps_photos = [p for p in trip_photos if p.gps]
    if not gps_photos:
        for p in trip_photos:
            p.country = None
            p.city = None
        return

    for p in gps_photos:
        p.country, p.city = _reverse_geocode_country_city(*p.gps)

    gps_with_time = sorted(
        (p for p in gps_photos if p.taken_at),
        key=lambda p: p.taken_at,
    )
    no_gps = [p for p in trip_photos if not p.gps]
    if not gps_with_time:
        fallback = gps_photos[0]
        for p in no_gps:
            p.country, p.city = fallback.country, fallback.city
        return

    for p in no_gps:
        if p.taken_at:
            target = datetime.fromisoformat(p.taken_at)
            nearest = min(
                gps_with_time,
                key=lambda g: abs(datetime.fromisoformat(g.taken_at) - target),
            )
        else:
            nearest = gps_with_time[0]
        p.country, p.city = nearest.country, nearest.city


def classify_albums(photos: list[PhotoRecord]) -> dict[str, AlbumRecord]:
    """Assigns album_id/country to each PhotoRecord in place and returns the
    resulting {album_id: AlbumRecord} map."""
    if not photos:
        return {}

    trips = _split_into_trips(photos)

    albums: dict[str, AlbumRecord] = {}
    for trip in trips:
        if not trip.photos:
            continue
        _apply_country_stage(trip.photos)

        by_country: dict[Optional[str], list[PhotoRecord]] = {}
        for p in trip.photos:
            by_country.setdefault(p.country, []).append(p)

        for country, members in by_country.items():
            album_id = str(uuid.uuid4())
            for p in members:
                p.album_id = album_id

            dated = sorted((p for p in members if p.taken_at), key=lambda p: p.taken_at)
            date_start = dated[0].taken_at[:10] if dated else None
            date_end = dated[-1].taken_at[:10] if dated else None
            cover = dated[0].photo_id if dated else members[0].photo_id

            albums[album_id] = AlbumRecord(
                album_id=album_id,
                country=country,
                date_start=date_start,
                date_end=date_end,
                photo_ids=[p.photo_id for p in members],
                cover_photo_id=cover,
            )

    return albums
