"""Unit tests for app.storage's content-hash dedup index (used by POST
/api/upload to avoid creating duplicate photo_ids on re-upload of the same
bytes — iteration 4 fix)."""
from app.storage import PhotoRecord, Store


def test_find_by_content_hash_returns_none_when_absent():
    store = Store()
    assert store.find_by_content_hash("nope") is None


def test_add_photo_indexes_content_hash():
    store = Store()
    record = PhotoRecord(
        photo_id="p1", filename="a.jpg", file_path="/tmp/a.jpg", content_hash="abc123",
    )
    store.add_photo(record)
    found = store.find_by_content_hash("abc123")
    assert found is not None
    assert found.photo_id == "p1"


def test_photo_without_content_hash_is_not_indexed():
    store = Store()
    store.add_photo(PhotoRecord(photo_id="p1", filename="a.jpg", file_path="/tmp/a.jpg"))
    assert store._hash_to_photo_id == {}
