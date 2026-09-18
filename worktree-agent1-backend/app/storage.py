"""In-memory data store for photos/albums.

Assumption (see shared/AGENT1_STATUS.md): demo-scale project, no persistence
requirement in CONTRACT.md, so a process-local dict is sufficient.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
IMAGES_DIR = DATA_DIR / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class PhotoRecord:
    photo_id: str
    filename: str
    file_path: Path
    album_id: Optional[str] = None
    is_blurry: bool = False
    duplicate_group_id: Optional[str] = None
    face_count: int = 0
    category: str = "general"
    aesthetic_score: float = 0.0
    portrait_bonus: Optional[dict] = None
    zero_shot_tags: dict = field(default_factory=dict)
    taken_at: Optional[str] = None  # ISO datetime string, from EXIF
    gps: Optional[tuple[float, float]] = None  # (lat, lon)
    country: Optional[str] = None
    city: Optional[str] = None
    content_hash: Optional[str] = None  # sha256 of raw bytes, for re-upload dedup


@dataclass
class AlbumRecord:
    album_id: str
    country: Optional[str] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    photo_ids: list[str] = field(default_factory=list)
    cover_photo_id: Optional[str] = None


class Store:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.photos: dict[str, PhotoRecord] = {}
        self.albums: dict[str, AlbumRecord] = {}
        self._hash_to_photo_id: dict[str, str] = {}

    def add_photo(self, record: PhotoRecord) -> None:
        with self._lock:
            self.photos[record.photo_id] = record
            if record.content_hash:
                self._hash_to_photo_id[record.content_hash] = record.photo_id

    def get_photo(self, photo_id: str) -> Optional[PhotoRecord]:
        return self.photos.get(photo_id)

    def find_by_content_hash(self, content_hash: str) -> Optional[PhotoRecord]:
        """Used by POST /api/upload to skip re-processing an exact re-upload
        (same bytes) of a photo that's already in the store — prevents the
        same file from accumulating multiple photo_ids across upload calls."""
        photo_id = self._hash_to_photo_id.get(content_hash)
        return self.photos.get(photo_id) if photo_id else None

    def photos_in_album(self, album_id: str) -> list[PhotoRecord]:
        return [p for p in self.photos.values() if p.album_id == album_id]

    def set_albums(self, albums: dict[str, AlbumRecord]) -> None:
        with self._lock:
            self.albums = albums

    def list_albums(self) -> list[AlbumRecord]:
        return list(self.albums.values())

    def get_album(self, album_id: str) -> Optional[AlbumRecord]:
        return self.albums.get(album_id)


store = Store()
