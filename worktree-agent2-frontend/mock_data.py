"""
mock_data.py — CONTRACT.md 스키마 기반 목업 데이터
API가 미구현 상태일 때 화면 작업에 사용하는 더미 데이터.
실제 API가 구현되면 이 파일을 호출하지 않고 api_client.py로 전환한다.
"""

# GET /api/albums 목업
MOCK_ALBUMS = [
    {
        "album_id": "album-de-001",
        "country": "Germany",
        "date_range": {"start": "2026-08-01", "end": "2026-08-04"},
        "photo_count": 214,
        "cover_photo_id": "photo-001"
    },
    {
        "album_id": "album-at-001",
        "country": "Austria",
        "date_range": {"start": "2026-08-04", "end": "2026-08-07"},
        "photo_count": 98,
        "cover_photo_id": "photo-010"
    },
    {
        "album_id": "album-kr-001",
        "country": None,  # GPS 없는 케이스: country=null
        "date_range": {"start": "2026-07-28", "end": "2026-07-31"},
        "photo_count": 53,
        "cover_photo_id": "photo-020"
    }
]

MOCK_ALBUMS_SINGLE = [
    {
        "album_id": "album-jp-001",
        "country": "Japan",
        "date_range": {"start": "2026-09-01", "end": "2026-09-05"},
        "photo_count": 120,
        "cover_photo_id": "photo-100"
    }
]

# GET /api/photos?album_id=xxx 목업
MOCK_PHOTOS = [
    {
        "photo_id": "photo-001",
        "filename": "IMG_0001.jpg",
        "album_id": "album-de-001",
        "image_url": "http://localhost:8000/api/photos/photo-001/image",
        "is_blurry": False,
        "duplicate_group_id": None,
        "face_count": 2,
        "category": "person",
        "aesthetic_score": 9.2,
        "portrait_bonus": {"eyes_open": True, "smiling": True, "adjustment": 0.5},
        "zero_shot_tags": {"selfie": 0.12, "food": 0.03, "landscape": 0.05}
    },
    {
        "photo_id": "photo-002",
        "filename": "IMG_0002.jpg",
        "album_id": "album-de-001",
        "image_url": "http://localhost:8000/api/photos/photo-002/image",
        "is_blurry": False,
        "duplicate_group_id": None,
        "face_count": 0,
        "category": "general",
        "aesthetic_score": 8.7,
        "portrait_bonus": None,
        "zero_shot_tags": {"selfie": 0.02, "food": 0.04, "landscape": 0.85}
    },
    {
        "photo_id": "photo-003",
        "filename": "IMG_0003.jpg",
        "album_id": "album-de-001",
        "image_url": "http://localhost:8000/api/photos/photo-003/image",
        "is_blurry": False,
        "duplicate_group_id": "dup-001",
        "face_count": 1,
        "category": "person",
        "aesthetic_score": 8.1,
        "portrait_bonus": {"eyes_open": True, "smiling": False, "adjustment": 0.0},
        "zero_shot_tags": {"selfie": 0.72, "food": 0.01, "landscape": 0.05}
    },
    {
        "photo_id": "photo-004",
        "filename": "IMG_0004.jpg",
        "album_id": "album-de-001",
        "image_url": "http://localhost:8000/api/photos/photo-004/image",
        "is_blurry": True,
        "duplicate_group_id": None,
        "face_count": 0,
        "category": "general",
        "aesthetic_score": 4.2,
        "portrait_bonus": None,
        "zero_shot_tags": {"selfie": 0.05, "food": 0.78, "landscape": 0.02}
    },
    {
        "photo_id": "photo-005",
        "filename": "IMG_0005.jpg",
        "album_id": "album-de-001",
        "image_url": "http://localhost:8000/api/photos/photo-005/image",
        "is_blurry": False,
        "duplicate_group_id": None,
        "face_count": 5,
        "category": "person",
        "aesthetic_score": 8.5,
        "portrait_bonus": {"eyes_open": True, "smiling": True, "adjustment": 0.5},
        "zero_shot_tags": {"selfie": 0.08, "food": 0.01, "landscape": 0.10}
    },
    {
        "photo_id": "photo-006",
        "filename": "IMG_0006.jpg",
        "album_id": "album-de-001",
        "image_url": "http://localhost:8000/api/photos/photo-006/image",
        "is_blurry": False,
        "duplicate_group_id": None,
        "face_count": 0,
        "category": "general",
        "aesthetic_score": 7.9,
        "portrait_bonus": None,
        "zero_shot_tags": {"selfie": 0.01, "food": 0.02, "landscape": 0.92}
    },
]

# GET /api/report?album_id=xxx 목업
MOCK_REPORT = {
    "total_photos": 214,
    "selfie_count": 42,
    "food_count": 18,
    "landscape_count": 87,
    "blurry_count": 12,
    "eyes_closed_count": 5,
    "most_retaken": {
        "duplicate_group_id": "dup-001",
        "count": 7,
        "representative_photo_id": "photo-003"
    },
    "best_shot": {"photo_id": "photo-001", "aesthetic_score": 9.2},
    "best_group_photo": {"photo_id": "photo-005", "aesthetic_score": 8.5, "face_count": 5},
    "top_location": {"place": "Munich", "count": 74}
}

MOCK_REPORT_NO_LOCATION = {
    "total_photos": 53,
    "selfie_count": 10,
    "food_count": 8,
    "landscape_count": 20,
    "blurry_count": 3,
    "eyes_closed_count": 1,
    "most_retaken": {
        "duplicate_group_id": "dup-002",
        "count": 3,
        "representative_photo_id": "photo-020"
    },
    "best_shot": {"photo_id": "photo-020", "aesthetic_score": 8.0},
    "best_group_photo": {"photo_id": "photo-021", "aesthetic_score": 7.5, "face_count": 3},
    "top_location": None  # GPS 없는 케이스
}


def get_mock_albums(use_single=False):
    return MOCK_ALBUMS_SINGLE if use_single else MOCK_ALBUMS


def get_mock_photos(album_id: str):
    return [p for p in MOCK_PHOTOS if p["album_id"] == album_id]


def get_mock_report(album_id: str):
    if album_id == "album-kr-001":
        return MOCK_REPORT_NO_LOCATION
    return MOCK_REPORT
