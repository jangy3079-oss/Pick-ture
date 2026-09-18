"""
api_client.py — FastAPI 백엔드(포트 8001) 호출 모듈
목업 데이터 없음 — 실제 백엔드만 호출한다.

TASKS_FOR_AGENT2.md 반복 2 지시:
- Base URL: http://localhost:8001 (8000 아님, Antigravity IDE가 8000 점유)
- image_url은 상대경로(/api/photos/{id}/image)로 오므로 BASE_URL 접두사를 붙여 완전한 URL 구성
"""

import requests
from typing import Optional

BASE_URL = "http://localhost:8001"
TIMEOUT_SHORT = 5       # 헬스체크, 목록 조회
TIMEOUT_UPLOAD = 120    # 업로드+ML 처리 (20장 기준 약 1~2분 소요 가능)
TIMEOUT_POST = 60       # Claude API 호출


def is_backend_alive() -> bool:
    """백엔드 서버가 실행 중인지 확인"""
    try:
        r = requests.get(f"{BASE_URL}/docs", timeout=3)
        return r.status_code < 500
    except Exception:
        return False


def build_image_url(relative_or_absolute: str) -> str:
    """
    image_url 필드가 상대경로(/api/...)이면 BASE_URL을 붙여 반환.
    이미 절대 URL이면 그대로 반환.
    """
    if relative_or_absolute.startswith("http"):
        return relative_or_absolute
    return f"{BASE_URL}{relative_or_absolute}"


def upload_photos(files) -> dict:
    """
    POST /api/upload — multipart/form-data, 필드명 'photos'
    반환: {"uploaded_count": int, "photo_ids": [str]}
    실패 시: {"error": str, "uploaded_count": 0, "photo_ids": []}
    """
    multipart = []
    for f in files:
        f.seek(0)
        multipart.append(("photos", (f.name, f.read(), "image/jpeg")))
    r = requests.post(f"{BASE_URL}/api/upload", files=multipart, timeout=TIMEOUT_UPLOAD)
    r.raise_for_status()
    return r.json()


def get_albums() -> list:
    """
    GET /api/albums
    반환: [{album_id, country, date_range, photo_count, cover_photo_id}, ...]
    """
    r = requests.get(f"{BASE_URL}/api/albums", timeout=TIMEOUT_SHORT)
    r.raise_for_status()
    return r.json()


def get_photos(album_id: str) -> list:
    """
    GET /api/photos?album_id=xxx
    반환: [photo_schema, ...]  — 배열
    각 photo의 image_url은 build_image_url()로 절대 URL로 변환해서 반환
    """
    r = requests.get(f"{BASE_URL}/api/photos", params={"album_id": album_id}, timeout=TIMEOUT_SHORT)
    r.raise_for_status()
    photos = r.json()
    # image_url을 절대 URL로 정규화
    for p in photos:
        if "image_url" in p:
            p["image_url"] = build_image_url(p["image_url"])
    return photos


def get_report(album_id: str) -> dict:
    """
    GET /api/report?album_id=xxx
    album_id 없으면 400. 반환: ReportOut 스키마
    """
    r = requests.get(f"{BASE_URL}/api/report", params={"album_id": album_id}, timeout=TIMEOUT_SHORT)
    r.raise_for_status()
    return r.json()


def generate_post(style: str, report: dict, best_shot_ids: list) -> dict:
    """
    POST /api/generate-post
    style: "blog" | "instagram"
    반환: {"text": str}
    """
    # report에 직렬화 불가 필드가 없는지 정리
    payload = {"style": style, "report": report, "best_shot_ids": best_shot_ids}
    r = requests.post(f"{BASE_URL}/api/generate-post", json=payload, timeout=TIMEOUT_POST)
    r.raise_for_status()
    return r.json()
