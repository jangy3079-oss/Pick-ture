"""Blur detection (OpenCV Laplacian variance) and duplicate grouping (imagededup PHash).

Assumption: blur threshold and duplicate-similarity threshold are not specified
in CONTRACT.md, so reasonable defaults are used (see constants below). CONTRACT.md
6-1 only asks for the 48h album-clustering threshold to be calibrated with real
photos; these two thresholds are out of that scope, so we pick sane defaults and
move on rather than blocking on calibration.
"""
from __future__ import annotations

from pathlib import Path

import cv2
from imagededup.methods import PHash

BLUR_VARIANCE_THRESHOLD = 100.0


def is_blurry(image_path: Path) -> bool:
    image = cv2.imread(str(image_path))
    if image is None:
        return False
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    return bool(variance < BLUR_VARIANCE_THRESHOLD)


def find_duplicate_groups(photo_paths: dict[str, Path]) -> dict[str, str]:
    """Return {photo_id: duplicate_group_id} for photos that have at least one
    near-duplicate in the batch. Photos with no duplicates are omitted (caller
    treats missing key as duplicate_group_id=None)."""
    if not photo_paths:
        return {}

    phasher = PHash()
    id_by_filename = {path.name: photo_id for photo_id, path in photo_paths.items()}
    image_dir = next(iter(photo_paths.values())).parent

    encodings = phasher.encode_images(image_dir=str(image_dir))
    # Only keep encodings for files we actually just processed (image_dir may
    # contain photos from earlier uploads too).
    encodings = {name: enc for name, enc in encodings.items() if name in id_by_filename}
    duplicates = phasher.find_duplicates(encoding_map=encodings)

    group_of: dict[str, str] = {}
    next_group_index = 0
    for filename, dup_filenames in duplicates.items():
        if not dup_filenames:
            continue
        photo_id = id_by_filename[filename]
        members = {photo_id} | {id_by_filename[f] for f in dup_filenames if f in id_by_filename}
        existing_group = next((group_of[m] for m in members if m in group_of), None)
        group_id = existing_group or f"dupgroup-{next_group_index}"
        if existing_group is None:
            next_group_index += 1
        for m in members:
            group_of[m] = group_id

    return group_of
