"""FastAPI app. Endpoints match shared/CONTRACT.md section 3 exactly (snake_case,
field names, status codes). No CORS middleware — Agent 2 (Streamlit) calls this
server-side via `requests` (CONTRACT.md 0-1), so no browser CORS is involved.
"""
from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app import albums as albums_module
from app import generate_post as generate_post_module
from app import preprocessing, report as report_module
from app import vision
from app.exif_utils import extract_datetime_and_gps
from app.models import (
    AlbumOut,
    DateRange,
    GeneratePostRequest,
    GeneratePostResponse,
    PhotoOut,
    PortraitBonus,
    ReportOut,
    UploadResponse,
)
from app.storage import IMAGES_DIR, PhotoRecord, store

app = FastAPI(title="Travel Photo Best-Cut Backend")


def _photo_to_out(p: PhotoRecord) -> PhotoOut:
    return PhotoOut(
        photo_id=p.photo_id,
        filename=p.filename,
        album_id=p.album_id,
        image_url=f"/api/photos/{p.photo_id}/image",
        is_blurry=p.is_blurry,
        duplicate_group_id=p.duplicate_group_id,
        face_count=p.face_count,
        category=p.category,
        aesthetic_score=p.aesthetic_score,
        portrait_bonus=PortraitBonus(**p.portrait_bonus) if p.portrait_bonus else None,
        zero_shot_tags=p.zero_shot_tags,
    )


@app.post("/api/upload", response_model=UploadResponse)
async def upload_photos(photos: list[UploadFile]) -> UploadResponse:
    if not photos:
        raise HTTPException(status_code=400, detail="No photos provided")

    new_records: list[PhotoRecord] = []
    new_paths: dict[str, Path] = {}

    for upload in photos:
        photo_id = str(uuid.uuid4())
        suffix = Path(upload.filename or "").suffix or ".jpg"
        dest = IMAGES_DIR / f"{photo_id}{suffix}"
        content = await upload.read()
        dest.write_bytes(content)

        taken_at, gps = extract_datetime_and_gps(dest)
        record = PhotoRecord(
            photo_id=photo_id,
            filename=upload.filename or dest.name,
            file_path=dest,
            taken_at=taken_at.isoformat() if taken_at else None,
            gps=gps,
        )
        record.is_blurry = preprocessing.is_blurry(dest)
        new_records.append(record)
        new_paths[photo_id] = dest

    dup_groups = preprocessing.find_duplicate_groups(new_paths)
    for record in new_records:
        record.duplicate_group_id = dup_groups.get(record.photo_id)

    for record in new_records:
        face_count, portrait_bonus = vision.analyze_faces(record.file_path)
        record.face_count = face_count
        record.category = "person" if face_count >= 1 else "general"
        record.portrait_bonus = portrait_bonus if record.category == "person" else None
        record.aesthetic_score = round(vision.aesthetic_score(record.file_path), 4)
        record.zero_shot_tags = vision.zero_shot_tags(record.file_path)
        store.add_photo(record)

    # Assumption (documented in shared/AGENT1_STATUS.md): album classification
    # re-runs over ALL photos currently in the store on every upload call, so
    # album_ids can change across upload batches. CONTRACT.md's flow is a
    # single upload followed immediately by album/photo queries, which this
    # handles correctly; multi-batch merging semantics are undefined there.
    all_photos = list(store.photos.values())
    new_albums = albums_module.classify_albums(all_photos)
    store.set_albums(new_albums)

    return UploadResponse(
        uploaded_count=len(new_records),
        photo_ids=[r.photo_id for r in new_records],
    )


@app.get("/api/albums", response_model=list[AlbumOut])
def list_albums() -> list[AlbumOut]:
    return [
        AlbumOut(
            album_id=a.album_id,
            country=a.country,
            date_range=DateRange(start=a.date_start, end=a.date_end),
            photo_count=len(a.photo_ids),
            cover_photo_id=a.cover_photo_id,
        )
        for a in store.list_albums()
    ]


@app.get("/api/photos", response_model=list[PhotoOut])
def list_photos(album_id: str) -> list[PhotoOut]:
    album = store.get_album(album_id)
    if album is None:
        raise HTTPException(status_code=400, detail="Unknown album_id")
    return [_photo_to_out(store.get_photo(pid)) for pid in album.photo_ids]


@app.get("/api/photos/{photo_id}", response_model=PhotoOut)
def get_photo(photo_id: str) -> PhotoOut:
    record = store.get_photo(photo_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Unknown photo_id")
    return _photo_to_out(record)


@app.get("/api/report", response_model=ReportOut)
def get_report(album_id: str) -> ReportOut:
    album = store.get_album(album_id)
    if album is None:
        raise HTTPException(status_code=400, detail="Unknown album_id")
    photos = store.photos_in_album(album_id)
    return ReportOut(**report_module.build_report(photos))


@app.post("/api/generate-post", response_model=GeneratePostResponse)
def generate_post(request: GeneratePostRequest) -> GeneratePostResponse:
    text = generate_post_module.generate_post(request.style, request.report, request.best_shot_ids)
    return GeneratePostResponse(text=text)


@app.get("/api/photos/{photo_id}/image")
def get_photo_image(photo_id: str) -> FileResponse:
    record = store.get_photo(photo_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Unknown photo_id")
    media_type = mimetypes.guess_type(str(record.file_path))[0] or "image/jpeg"
    return FileResponse(record.file_path, media_type=media_type)
