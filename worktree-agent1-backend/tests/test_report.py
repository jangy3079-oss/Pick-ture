"""Unit tests for app.report aggregation (shared/CONTRACT.md 3, GET /api/report)."""
from app.report import build_report
from app.storage import PhotoRecord


def _photo(pid, **kwargs):
    defaults = dict(
        filename=f"{pid}.jpg",
        file_path=f"/tmp/{pid}.jpg",
        is_blurry=False,
        face_count=0,
        category="general",
        aesthetic_score=5.0,
        zero_shot_tags={"selfie": 0.1, "food": 0.1, "landscape": 0.8},
    )
    defaults.update(kwargs)
    return PhotoRecord(photo_id=pid, **defaults)


def test_empty_album_report():
    r = build_report([])
    assert r["total_photos"] == 0
    assert r["best_shot"] is None
    assert r["most_retaken"] is None
    assert r["best_group_photo"] is None
    assert r["top_location"] is None


def test_category_counts_use_argmax_tag():
    photos = [
        _photo("selfie1", face_count=1, zero_shot_tags={"selfie": 0.9, "food": 0.05, "landscape": 0.05}),
        _photo("food1", zero_shot_tags={"selfie": 0.1, "food": 0.8, "landscape": 0.1}),
        _photo("land1", zero_shot_tags={"selfie": 0.2, "food": 0.2, "landscape": 0.6}),
    ]
    r = build_report(photos)
    assert r["selfie_count"] == 1
    assert r["food_count"] == 1
    assert r["landscape_count"] == 1


def test_low_confidence_selfie_with_no_face_falls_back():
    """Human-reported bug (2026-09-19): CLIP zero-shot weakly (51%) tagged a
    faceless architecture photo as 'selfie'. A low-confidence selfie call
    with no detected face is treated as CLIP being wrong -> falls back to
    food vs. landscape."""
    faceless_but_selfie_tagged = _photo(
        "gate", face_count=0,
        zero_shot_tags={"selfie": 0.51, "food": 0.11, "landscape": 0.38},
    )
    r = build_report([faceless_but_selfie_tagged])
    assert r["selfie_count"] == 0
    assert r["landscape_count"] == 1


def test_high_confidence_selfie_with_no_face_is_trusted():
    """Follow-up human-reported bug (same day): a genuine mirror selfie
    (phone occluding part of the face) made mediapipe miss the face
    (face_count == 0), but CLIP was ~99.6% confident it's a selfie. Excluding
    selfie here left food/landscape to 'win' on near-zero noise (0.003 vs
    0.001) - worse than trusting CLIP's near-certain read. High-confidence
    selfie calls must NOT be excluded just because face_count == 0."""
    mirror_selfie_missed_face = _photo(
        "mirror", face_count=0,
        zero_shot_tags={"selfie": 0.9956, "food": 0.0031, "landscape": 0.0014},
    )
    r = build_report([mirror_selfie_missed_face])
    assert r["selfie_count"] == 1
    assert r["food_count"] == 0


def test_selfie_tag_counted_when_face_present():
    real_selfie = _photo(
        "selfie", face_count=1, category="person",
        zero_shot_tags={"selfie": 0.99, "food": 0.005, "landscape": 0.005},
    )
    r = build_report([real_selfie])
    assert r["selfie_count"] == 1


def test_blurry_and_eyes_closed_counts():
    photos = [
        _photo("blurry", is_blurry=True),
        _photo("sharp", is_blurry=False),
        _photo(
            "eyes_closed",
            category="person",
            face_count=1,
            portrait_bonus={"eyes_open": False, "smiling": False, "adjustment": -1.0},
        ),
        _photo(
            "eyes_open",
            category="person",
            face_count=1,
            portrait_bonus={"eyes_open": True, "smiling": True, "adjustment": 1.0},
        ),
    ]
    r = build_report(photos)
    assert r["blurry_count"] == 1
    assert r["eyes_closed_count"] == 1


def test_most_retaken_picks_largest_duplicate_group_and_best_representative():
    photos = [
        _photo("d1", duplicate_group_id="g1", aesthetic_score=3.0),
        _photo("d2", duplicate_group_id="g1", aesthetic_score=8.0),
        _photo("d3", duplicate_group_id="g1", aesthetic_score=4.0),
        _photo("d4", duplicate_group_id="g2", aesthetic_score=9.0),
    ]
    r = build_report(photos)
    assert r["most_retaken"]["duplicate_group_id"] == "g1"
    assert r["most_retaken"]["count"] == 3
    assert r["most_retaken"]["representative_photo_id"] == "d2"


def test_best_shot_is_highest_aesthetic_score():
    photos = [_photo("low", aesthetic_score=2.0), _photo("high", aesthetic_score=9.5)]
    r = build_report(photos)
    assert r["best_shot"] == {"photo_id": "high", "aesthetic_score": 9.5}


def test_best_group_photo_requires_two_plus_faces_and_person_category():
    photos = [
        _photo("solo", category="person", face_count=1, aesthetic_score=9.0),
        _photo("group_low", category="person", face_count=3, aesthetic_score=4.0),
        _photo("group_high", category="person", face_count=5, aesthetic_score=8.5),
    ]
    r = build_report(photos)
    assert r["best_group_photo"] == {
        "photo_id": "group_high",
        "aesthetic_score": 8.5,
        "face_count": 5,
    }


def test_top_location_none_when_no_gps():
    photos = [_photo("a"), _photo("b")]
    r = build_report(photos)
    assert r["top_location"] is None


def test_top_location_most_common_city():
    photos = [
        _photo("a", city="Prague"),
        _photo("b", city="Prague"),
        _photo("c", city="Berlin"),
    ]
    r = build_report(photos)
    assert r["top_location"] == {"place": "Prague", "count": 2}
