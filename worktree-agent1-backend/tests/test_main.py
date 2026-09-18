"""Endpoint schema tests. Per PLAN.md: GET /api/photos/{photo_id} must match
shared/CONTRACT.md section 3 exactly (field names included) — this is the most
important test since Agent 2's whole frontend depends on it.

We inject PhotoRecord/AlbumRecord objects directly into the in-memory store
rather than running the full upload pipeline, to keep this a fast unit test of
the endpoint/schema layer (not an integration test of the ML pipeline, which
is exercised manually/ad-hoc against dataset/ per PLAN.md's 검증 범위).
"""
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.storage import AlbumRecord, PhotoRecord, store

DATASET_DIR = Path(__file__).resolve().parent.parent.parent / "dataset"
REAL_SAMPLE_PHOTO = DATASET_DIR / "IMG_9322.jpeg"


def _reset_store():
    store.photos.clear()
    store.albums.clear()


def test_get_photo_matches_contract_schema_person_category():
    _reset_store()
    record = PhotoRecord(
        photo_id="photo-1",
        filename="IMG_1.jpg",
        file_path="/tmp/IMG_1.jpg",
        album_id="album-1",
        is_blurry=False,
        duplicate_group_id=None,
        face_count=1,
        category="person",
        aesthetic_score=7.8,
        portrait_bonus={"eyes_open": True, "smiling": True, "adjustment": 0.5},
        zero_shot_tags={"selfie": 0.82, "food": 0.05, "landscape": 0.10},
    )
    store.add_photo(record)

    client = TestClient(app)
    resp = client.get("/api/photos/photo-1")
    assert resp.status_code == 200
    body = resp.json()

    assert set(body.keys()) == {
        "photo_id", "filename", "album_id", "image_url", "is_blurry",
        "duplicate_group_id", "face_count", "category", "aesthetic_score",
        "portrait_bonus", "zero_shot_tags",
    }
    assert body["photo_id"] == "photo-1"
    assert body["album_id"] == "album-1"
    assert body["image_url"] == "/api/photos/photo-1/image"
    assert body["category"] == "person"
    assert body["portrait_bonus"] == {"eyes_open": True, "smiling": True, "adjustment": 0.5}
    assert body["zero_shot_tags"] == {"selfie": 0.82, "food": 0.05, "landscape": 0.10}


def test_get_photo_general_category_has_null_portrait_bonus():
    _reset_store()
    record = PhotoRecord(
        photo_id="photo-2",
        filename="IMG_2.jpg",
        file_path="/tmp/IMG_2.jpg",
        album_id="album-1",
        category="general",
        aesthetic_score=6.0,
        zero_shot_tags={"selfie": 0.1, "food": 0.1, "landscape": 0.8},
    )
    store.add_photo(record)

    client = TestClient(app)
    resp = client.get("/api/photos/photo-2")
    assert resp.status_code == 200
    assert resp.json()["portrait_bonus"] is None


def test_get_photo_unknown_id_is_404():
    _reset_store()
    client = TestClient(app)
    resp = client.get("/api/photos/does-not-exist")
    assert resp.status_code == 404


def test_list_photos_by_album_returns_array():
    _reset_store()
    album = AlbumRecord(album_id="album-1", country="France", photo_ids=["p1", "p2"], cover_photo_id="p1")
    store.set_albums({"album-1": album})
    store.add_photo(PhotoRecord(photo_id="p1", filename="a.jpg", file_path="/tmp/a.jpg", album_id="album-1"))
    store.add_photo(PhotoRecord(photo_id="p2", filename="b.jpg", file_path="/tmp/b.jpg", album_id="album-1"))

    client = TestClient(app)
    resp = client.get("/api/photos", params={"album_id": "album-1"})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 2
    assert {p["photo_id"] for p in body} == {"p1", "p2"}


def test_list_photos_unknown_album_is_400():
    _reset_store()
    client = TestClient(app)
    resp = client.get("/api/photos", params={"album_id": "nope"})
    assert resp.status_code == 400


def test_get_photo_image_serves_real_bytes():
    """CONTRACT.md 3장: image_url은 실제 이미지 바이트를 내려주는 정적 경로여야 함.
    목업이 아니라 dataset/의 실제 JPEG 파일을 그대로 서빙하는지 바이트 단위로 확인."""
    _reset_store()
    store.add_photo(
        PhotoRecord(
            photo_id="photo-img", filename="IMG_9322.jpeg", file_path=REAL_SAMPLE_PHOTO, album_id="album-1",
        )
    )

    client = TestClient(app)
    resp = client.get("/api/photos/photo-img/image")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"
    assert resp.content == REAL_SAMPLE_PHOTO.read_bytes()


def test_get_photo_image_thumbnail_is_resized_and_smaller():
    """?size=thumb resizes to a 300px short side and returns a (usually)
    much smaller JPEG than the original — verified against a real photo."""
    _reset_store()
    store.add_photo(
        PhotoRecord(
            photo_id="photo-img", filename="IMG_9322.jpeg", file_path=REAL_SAMPLE_PHOTO, album_id="album-1",
        )
    )

    client = TestClient(app)
    resp = client.get("/api/photos/photo-img/image", params={"size": "thumb"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"
    assert len(resp.content) < len(REAL_SAMPLE_PHOTO.read_bytes())

    from io import BytesIO
    from PIL import Image
    with Image.open(BytesIO(resp.content)) as img:
        assert min(img.width, img.height) == 300


def test_get_photo_image_unknown_size_falls_back_to_original():
    _reset_store()
    store.add_photo(
        PhotoRecord(
            photo_id="photo-img", filename="IMG_9322.jpeg", file_path=REAL_SAMPLE_PHOTO, album_id="album-1",
        )
    )
    client = TestClient(app)
    resp = client.get("/api/photos/photo-img/image", params={"size": "bogus"})
    assert resp.status_code == 200
    assert resp.content == REAL_SAMPLE_PHOTO.read_bytes()


def test_get_photo_image_unknown_id_is_404():
    _reset_store()
    client = TestClient(app)
    resp = client.get("/api/photos/does-not-exist/image")
    assert resp.status_code == 404


def test_get_albums_schema():
    _reset_store()
    album = AlbumRecord(
        album_id="album-1",
        country="Germany",
        date_start="2026-08-01",
        date_end="2026-08-04",
        photo_ids=["p1"],
        cover_photo_id="p1",
    )
    store.set_albums({"album-1": album})

    client = TestClient(app)
    resp = client.get("/api/albums")
    assert resp.status_code == 200
    body = resp.json()
    assert body == [{
        "album_id": "album-1",
        "country": "Germany",
        "date_range": {"start": "2026-08-01", "end": "2026-08-04"},
        "photo_count": 1,
        "cover_photo_id": "p1",
    }]


def test_get_report_requires_album_id_query_param():
    client = TestClient(app)
    resp = client.get("/api/report")
    assert resp.status_code == 422  # missing required query param


def test_get_report_unknown_album_is_400():
    _reset_store()
    client = TestClient(app)
    resp = client.get("/api/report", params={"album_id": "nope"})
    assert resp.status_code == 400


def test_get_report_schema():
    _reset_store()
    album = AlbumRecord(album_id="album-1", photo_ids=["p1"], cover_photo_id="p1")
    store.set_albums({"album-1": album})
    store.add_photo(
        PhotoRecord(
            photo_id="p1", filename="a.jpg", file_path="/tmp/a.jpg", album_id="album-1",
            aesthetic_score=9.2, zero_shot_tags={"selfie": 0.1, "food": 0.1, "landscape": 0.8},
        )
    )

    client = TestClient(app)
    resp = client.get("/api/report", params={"album_id": "album-1"})
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {
        "total_photos", "selfie_count", "food_count", "landscape_count",
        "blurry_count", "eyes_closed_count", "most_retaken", "best_shot",
        "best_group_photo", "top_location", "most_photographed_person",
    }
    assert body["total_photos"] == 1
    assert body["best_shot"] == {"photo_id": "p1", "aesthetic_score": 9.2}
    # only 1 photo in album -> no repeat-person clustering possible
    assert body["most_photographed_person"] is None
