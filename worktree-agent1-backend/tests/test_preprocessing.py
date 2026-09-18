"""Unit tests for blur detection and duplicate grouping against real photos in
dataset/ (the only real-photo sample available, per shared/AGENT1_STATUS.md)."""
from pathlib import Path

from app.preprocessing import find_duplicate_groups, is_blurry

DATASET_DIR = Path(__file__).resolve().parent.parent.parent / "dataset"


def test_is_blurry_runs_on_real_photos_without_error():
    photos = [p for p in DATASET_DIR.iterdir() if p.is_file()]
    assert photos
    for p in photos:
        result = is_blurry(p)
        assert isinstance(result, bool)


def test_find_duplicate_groups_detects_identical_files():
    photo_paths = {
        "a": DATASET_DIR / "IMG_9398.jpeg",
        "b": DATASET_DIR / "IMG_9398 (1).jpeg",
        "c": DATASET_DIR / "IMG_9322.jpeg",
    }
    groups = find_duplicate_groups(photo_paths)
    assert groups.get("a") is not None
    assert groups["a"] == groups["b"]
    assert groups.get("c") is None


def test_find_duplicate_groups_empty_input():
    assert find_duplicate_groups({}) == {}
