"""Unit tests for app.face_clustering (P2: most-photographed person).

Mocks detect_face_crops/embed_face_crop so the suite doesn't load the real
CLIP/mediapipe models — clustering logic is tested in isolation from vision.
"""
import torch

import app.face_clustering as face_clustering
from app.storage import PhotoRecord


def _photo(pid, aesthetic_score=5.0):
    return PhotoRecord(
        photo_id=pid, filename=f"{pid}.jpg", file_path=f"/tmp/{pid}.jpg",
        category="person", face_count=1, aesthetic_score=aesthetic_score,
    )


def _unit(*values):
    v = torch.tensor(values, dtype=torch.float32)
    return v / v.norm()


def test_fewer_than_two_person_photos_returns_none():
    assert face_clustering.find_most_photographed_person([_photo("a")]) is None
    assert face_clustering.find_most_photographed_person([]) is None


def test_same_person_across_photos_is_clustered_and_counted(monkeypatch):
    photos = [_photo("a", aesthetic_score=3.0), _photo("b", aesthetic_score=9.0), _photo("c", aesthetic_score=1.0)]

    # a and b: near-identical embedding (same person). c: very different (different person).
    embeddings = {
        "a": _unit(1.0, 0.0, 0.0),
        "b": _unit(0.99, 0.01, 0.0),
        "c": _unit(0.0, 1.0, 0.0),
    }

    monkeypatch.setattr(face_clustering, "detect_face_crops", lambda fp: ["fake_crop"])

    # find_most_photographed_person iterates photos in order, one face crop
    # each -> embed_face_crop is called once per photo in that same order.
    call_order = iter(["a", "b", "c"])

    def fake_embed_stateful(crop):
        pid = next(call_order)
        return embeddings[pid]

    monkeypatch.setattr(face_clustering, "embed_face_crop", fake_embed_stateful)

    result = face_clustering.find_most_photographed_person(photos)
    assert result is not None
    assert result["count"] == 2
    assert result["representative_photo_id"] == "b"  # higher aesthetic_score among {a, b}


def test_no_repeat_person_returns_none(monkeypatch):
    photos = [_photo("a"), _photo("b")]
    embeddings = {"a": _unit(1.0, 0.0), "b": _unit(0.0, 1.0)}
    call_order = iter(["a", "b"])

    monkeypatch.setattr(face_clustering, "detect_face_crops", lambda fp: ["crop"])
    monkeypatch.setattr(face_clustering, "embed_face_crop", lambda crop: embeddings[next(call_order)])

    assert face_clustering.find_most_photographed_person(photos) is None
