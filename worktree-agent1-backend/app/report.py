"""GET /api/report aggregation logic (shared/CONTRACT.md section 3).

Assumption (not specified in CONTRACT.md): selfie/food/landscape counts use the
argmax of each photo's zero_shot_tags dict (the category CLIP considers most
likely), not a fixed probability threshold — simplest rule consistent with
"CLIP 제로샷" classification and avoids an arbitrary threshold choice.

Fix (2026-09-19, human-reported): CLIP's 3-way zero-shot vote has no "none of
these" option, so on ambiguous architecture/landscape photos it sometimes
picks "selfie" with a weak margin (e.g. 51% vs 38%) even when mediapipe found
zero faces in the photo — verified against dataset/IMG_9322.jpeg (a Prague
Castle gate with no people, tagged selfie=0.51).

Follow-up fix (same day): the first version of this fix excluded "selfie"
outright whenever face_count == 0, which over-corrected — mediapipe misses
faces on real selfies too (occluded by the phone, mirror selfies), e.g.
dataset/IMG_9371.jpeg and dataset/IMG_9498.jpeg are genuine phone-in-hand
mirror selfies where mediapipe found 0 faces but CLIP was ~99.6%/99.56%
confident it's a selfie. Blindly excluding selfie there left food vs.
landscape to "win" on near-zero, meaningless scores (e.g. food=0.003 vs
landscape=0.001) — a worse answer than trusting CLIP's near-certain call.

So the exclusion now only kicks in when face_count == 0 AND CLIP itself is
NOT confident (selfie score < SELFIE_CONFIDENCE_FLOOR): a low-confidence
selfie call with no detected face is probably CLIP being wrong (the gate
photo case), while a near-certain selfie call with no detected face is
probably mediapipe missing an occluded/angled face (the mirror selfie case)
and CLIP's read is kept.
"""
from __future__ import annotations

from collections import Counter
from typing import Optional

from app.storage import PhotoRecord

SELFIE_CONFIDENCE_FLOOR = 0.9


def _argmax_tag(photo: PhotoRecord) -> Optional[str]:
    if not photo.zero_shot_tags:
        return None
    candidates = photo.zero_shot_tags
    if photo.face_count == 0 and candidates.get("selfie", 0) < SELFIE_CONFIDENCE_FLOOR:
        candidates = {k: v for k, v in candidates.items() if k != "selfie"}
        if not candidates:
            return None
    return max(candidates.items(), key=lambda kv: kv[1])[0]


def build_report(photos: list[PhotoRecord], most_photographed_person: Optional[dict] = None) -> dict:
    total_photos = len(photos)
    selfie_count = sum(1 for p in photos if _argmax_tag(p) == "selfie")
    food_count = sum(1 for p in photos if _argmax_tag(p) == "food")
    landscape_count = sum(1 for p in photos if _argmax_tag(p) == "landscape")
    blurry_count = sum(1 for p in photos if p.is_blurry)
    eyes_closed_count = sum(
        1 for p in photos
        if p.category == "person" and p.portrait_bonus and not p.portrait_bonus.get("eyes_open", True)
    )

    most_retaken = None
    group_ids = [p.duplicate_group_id for p in photos if p.duplicate_group_id]
    if group_ids:
        group_id, count = Counter(group_ids).most_common(1)[0]
        members = [p for p in photos if p.duplicate_group_id == group_id]
        representative = max(members, key=lambda p: p.aesthetic_score)
        most_retaken = {
            "duplicate_group_id": group_id,
            "count": count,
            "representative_photo_id": representative.photo_id,
        }

    best_shot = None
    if photos:
        best = max(photos, key=lambda p: p.aesthetic_score)
        best_shot = {"photo_id": best.photo_id, "aesthetic_score": best.aesthetic_score}

    best_group_photo = None
    group_photos = [p for p in photos if p.category == "person" and p.face_count >= 2]
    if group_photos:
        best = max(group_photos, key=lambda p: p.aesthetic_score)
        best_group_photo = {
            "photo_id": best.photo_id,
            "aesthetic_score": best.aesthetic_score,
            "face_count": best.face_count,
        }

    top_location = None
    cities = [p.city for p in photos if p.city]
    if cities:
        place, count = Counter(cities).most_common(1)[0]
        top_location = {"place": place, "count": count}

    return {
        "total_photos": total_photos,
        "selfie_count": selfie_count,
        "food_count": food_count,
        "landscape_count": landscape_count,
        "blurry_count": blurry_count,
        "eyes_closed_count": eyes_closed_count,
        "most_retaken": most_retaken,
        "best_shot": best_shot,
        "best_group_photo": best_group_photo,
        "top_location": top_location,
        "most_photographed_person": most_photographed_person,
    }
