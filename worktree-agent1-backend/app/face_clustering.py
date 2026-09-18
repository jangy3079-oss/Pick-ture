"""P2 (PLAN.md task 8): face clustering to find the most-photographed person.

Not specified in the original shared/CONTRACT.md — added as an ADDITIVE,
nullable field on GET /api/report (`most_photographed_person`). See
shared/CONTRACT.md changelog and shared/TASKS_FOR_AGENT2.md for the notice to
Agent 2.

Approach: crop each detected face (mediapipe) and embed it with the CLIP model
already loaded for zero_shot_tags (app.vision.embed_face_crop) — no dedicated
face-recognition/identity model is in CONTRACT.md's pre-approved package list,
so this reuses an existing model rather than adding a new dependency mid-loop.
CLIP wasn't trained for face identity, so this is a coarse proxy, not
face-recognition-grade accuracy; good enough for a P2 "nice to have" stat.

Clustering: simple greedy single-pass clustering by cosine similarity against
running cluster centroids (no new clustering library needed).
"""
from __future__ import annotations

import torch

from app.storage import PhotoRecord
from app.vision import detect_face_crops, embed_face_crop

SIMILARITY_THRESHOLD = 0.9


def _cluster_embeddings(items: list[tuple[str, torch.Tensor]]) -> dict[str, int]:
    """items: [(photo_id, embedding), ...] (one entry per detected face).
    Returns {photo_id: cluster_index} — last-write-wins if a photo has
    multiple faces in the same cluster, which is fine since callers only
    care about which photos contain a given cluster at all."""
    centroids: list[torch.Tensor] = []
    counts: list[int] = []
    assignment: dict[str, int] = {}

    for photo_id, embedding in items:
        best_idx, best_sim = -1, -1.0
        for idx, centroid in enumerate(centroids):
            sim = torch.dot(embedding, centroid).item()
            if sim > best_sim:
                best_idx, best_sim = idx, sim

        if best_idx >= 0 and best_sim >= SIMILARITY_THRESHOLD:
            n = counts[best_idx]
            centroids[best_idx] = (centroids[best_idx] * n + embedding) / (n + 1)
            centroids[best_idx] /= centroids[best_idx].norm()
            counts[best_idx] += 1
            assignment[photo_id] = best_idx
        else:
            centroids.append(embedding.clone())
            counts.append(1)
            assignment[photo_id] = len(centroids) - 1

    return assignment


def find_most_photographed_person(photos: list[PhotoRecord]) -> dict | None:
    person_photos = [p for p in photos if p.category == "person"]
    if len(person_photos) < 2:
        return None

    face_items: list[tuple[str, torch.Tensor]] = []
    for photo in person_photos:
        for crop in detect_face_crops(photo.file_path):
            face_items.append((photo.photo_id, embed_face_crop(crop)))

    if len(face_items) < 2:
        return None

    assignment = _cluster_embeddings(face_items)

    photos_per_cluster: dict[int, set[str]] = {}
    for photo_id, cluster_idx in assignment.items():
        photos_per_cluster.setdefault(cluster_idx, set()).add(photo_id)

    best_cluster_idx, best_photo_ids = max(
        photos_per_cluster.items(), key=lambda kv: len(kv[1])
    )
    if len(best_photo_ids) < 2:
        return None

    by_id = {p.photo_id: p for p in person_photos}
    representative = max((by_id[pid] for pid in best_photo_ids), key=lambda p: p.aesthetic_score)

    return {
        "count": len(best_photo_ids),
        "representative_photo_id": representative.photo_id,
    }
