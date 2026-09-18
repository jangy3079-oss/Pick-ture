"""Pydantic response/request schemas matching shared/CONTRACT.md section 3 exactly (snake_case)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class PortraitBonus(BaseModel):
    eyes_open: bool
    smiling: bool
    adjustment: float


class DateRange(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None


class UploadResponse(BaseModel):
    uploaded_count: int
    photo_ids: list[str]


class PhotoOut(BaseModel):
    photo_id: str
    filename: str
    album_id: str
    image_url: str
    is_blurry: bool
    duplicate_group_id: Optional[str] = None
    face_count: int
    category: str  # "person" | "general"
    aesthetic_score: float
    portrait_bonus: Optional[PortraitBonus] = None
    zero_shot_tags: dict[str, float]


class AlbumOut(BaseModel):
    album_id: str
    country: Optional[str] = None
    date_range: DateRange
    photo_count: int
    cover_photo_id: str


class MostRetaken(BaseModel):
    duplicate_group_id: str
    count: int
    representative_photo_id: str


class BestShot(BaseModel):
    photo_id: str
    aesthetic_score: float


class BestGroupPhoto(BaseModel):
    photo_id: str
    aesthetic_score: float
    face_count: int


class TopLocation(BaseModel):
    place: str
    count: int


class MostPhotographedPerson(BaseModel):
    """P2 addition (not in original CONTRACT.md schema) — see
    app/face_clustering.py and CONTRACT.md changelog."""

    count: int
    representative_photo_id: str


class ReportOut(BaseModel):
    total_photos: int
    selfie_count: int
    food_count: int
    landscape_count: int
    blurry_count: int
    eyes_closed_count: int
    most_retaken: Optional[MostRetaken] = None
    best_shot: Optional[BestShot] = None
    best_group_photo: Optional[BestGroupPhoto] = None
    top_location: Optional[TopLocation] = None
    most_photographed_person: Optional[MostPhotographedPerson] = None


class GeneratePostRequest(BaseModel):
    style: str  # "blog" | "instagram"
    report: ReportOut
    best_shot_ids: list[str]


class GeneratePostResponse(BaseModel):
    text: str
