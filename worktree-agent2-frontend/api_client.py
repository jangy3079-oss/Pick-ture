"""
api_client.py — FastAPI 백엔드(포트 8000)와의 통신 모듈
백엔드가 미구현인 경우 mock_data.py의 목업 데이터로 폴백한다.
"""

import requests
from typing import Optional
import mock_data

BASE_URL = "http://localhost:8000"
TIMEOUT = 30  # 업로드/처리 시간 고려해 넉넉히 설정


def _is_backend_alive() -> bool:
    """백엔드 서버가 실행 중인지 확인 (헬스체크)"""
    try:
        r = requests.get(f"{BASE_URL}/docs", timeout=3)
        return r.status_code < 500
    except Exception:
        return False


def upload_photos(files) -> dict:
    """
    POST /api/upload — multipart/form-data, 필드명 'photos'
    반환: {"uploaded_count": int, "photo_ids": [str]}
    """
    try:
        multipart = [("photos", (f.name, f.read(), "image/jpeg")) for f in files]
        r = requests.post(f"{BASE_URL}/api/upload", files=multipart, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "uploaded_count": 0, "photo_ids": []}


def get_albums() -> list:
    """
    GET /api/albums
    반환: [{album_id, country, date_range, photo_count, cover_photo_id}]
    백엔드 미구현 시 목업 반환
    """
    try:
        r = requests.get(f"{BASE_URL}/api/albums", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return mock_data.get_mock_albums()


def get_photos(album_id: str) -> list:
    """
    GET /api/photos?album_id=xxx
    반환: [photo_schema, ...]
    백엔드 미구현 시 목업 반환
    """
    try:
        r = requests.get(f"{BASE_URL}/api/photos", params={"album_id": album_id}, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return mock_data.get_mock_photos(album_id)


def get_report(album_id: str) -> Optional[dict]:
    """
    GET /api/report?album_id=xxx
    album_id 없으면 400. 백엔드 미구현 시 목업 반환
    """
    try:
        r = requests.get(f"{BASE_URL}/api/report", params={"album_id": album_id}, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return mock_data.get_mock_report(album_id)


def generate_post(style: str, report: dict, best_shot_ids: list) -> dict:
    """
    POST /api/generate-post
    style: "blog" or "instagram"
    반환: {"text": str}
    """
    try:
        payload = {"style": style, "report": report, "best_shot_ids": best_shot_ids}
        r = requests.post(f"{BASE_URL}/api/generate-post", json=payload, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        # 목업 응답: 실제 API 미구현 시
        if style == "blog":
            text = (
                "✈️ **독일 여행 후기 — 뮌헨에서의 4일**\n\n"
                "지난 8월, 오랜 꿈이었던 독일 여행을 다녀왔습니다. "
                "총 214장의 사진 중 베스트컷을 선별해 이번 여행의 하이라이트를 담았습니다.\n\n"
                "뮌헨 시내에서만 74장을 찍을 만큼 볼거리가 넘쳤고, "
                "셀카 42장, 음식 사진 18장, 풍경 사진 87장으로 여행의 다양한 순간을 기록했습니다. "
                "(목업 텍스트 — 백엔드 API 연동 후 실제 생성됩니다)"
            )
        else:
            text = (
                "🇩🇪 뮌헨 4일 ✨\n"
                "214장 중 베스트컷 셀렉 완료 📸\n"
                "풍경 87장, 셀카 42장, 음식 18장\n"
                "최고 미학 점수 9.2/10 🏆\n"
                "#독일여행 #뮌헨 #Munchen #여행스타그램 #TravelGram\n\n"
                "(목업 텍스트 — 백엔드 API 연동 후 실제 생성됩니다)"
            )
        return {"text": text, "_is_mock": True}
