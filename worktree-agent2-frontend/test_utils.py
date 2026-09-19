"""
test_utils.py — utils.py 순수 함수 유닛테스트
실행: python -m pytest test_utils.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pytest
from utils import (
    format_album_label,
    sort_photos_by_score,
    filter_by_category,
    get_score_badge,
    format_score,
    has_top_location,
    get_portrait_status,
    get_dominant_tag,
)


# ── format_album_label ───────────────────────────────────────────────────────

class TestFormatAlbumLabel:
    def test_with_country(self):
        album = {
            "album_id": "a1",
            "country": "Germany",
            "date_range": {"start": "2026-08-01", "end": "2026-08-04"},
            "photo_count": 214,
            "cover_photo_id": "p1"
        }
        label = format_album_label(album)
        assert "Germany" in label
        assert "214장" in label
        assert "8/1" in label
        assert "8/4" in label

    def test_without_country_null(self):
        album = {
            "album_id": "a2",
            "country": None,  # GPS 없음
            "date_range": {"start": "2026-07-28", "end": "2026-07-31"},
            "photo_count": 53,
            "cover_photo_id": "p2"
        }
        label = format_album_label(album)
        assert "None" not in label
        assert "53장" in label
        assert "7/28" in label

    def test_empty_date_range(self):
        album = {
            "album_id": "a3",
            "country": "Japan",
            "date_range": {},
            "photo_count": 0,
            "cover_photo_id": "p3"
        }
        label = format_album_label(album)
        assert "Japan" in label  # 국가는 있어야 함


# ── sort_photos_by_score ─────────────────────────────────────────────────────

class TestSortPhotosByScore:
    def _make_photo(self, photo_id, score, is_blurry=False, category="general"):
        return {
            "photo_id": photo_id,
            "aesthetic_score": score,
            "is_blurry": is_blurry,
            "category": category,
            "duplicate_group_id": None,
            "face_count": 0,
            "portrait_bonus": None,
            "zero_shot_tags": {}
        }

    def test_sorted_desc(self):
        photos = [
            self._make_photo("p1", 7.0),
            self._make_photo("p2", 9.2),
            self._make_photo("p3", 8.5),
        ]
        result = sort_photos_by_score(photos)
        scores = [p["aesthetic_score"] for p in result]
        assert scores == sorted(scores, reverse=True)

    def test_blurry_goes_last(self):
        photos = [
            self._make_photo("p1", 9.0, is_blurry=False),
            self._make_photo("p2", 9.5, is_blurry=True),  # 높은 점수지만 blurry
            self._make_photo("p3", 7.0, is_blurry=False),
        ]
        result = sort_photos_by_score(photos)
        assert result[-1]["photo_id"] == "p2"

    def test_empty_list(self):
        assert sort_photos_by_score([]) == []

    def test_all_blurry(self):
        photos = [
            self._make_photo("p1", 8.0, is_blurry=True),
            self._make_photo("p2", 9.0, is_blurry=True),
        ]
        result = sort_photos_by_score(photos)
        assert len(result) == 2


# ── filter_by_category ───────────────────────────────────────────────────────

class TestFilterByCategory:
    def test_person(self):
        photos = [
            {"category": "person", "photo_id": "p1"},
            {"category": "general", "photo_id": "p2"},
            {"category": "person", "photo_id": "p3"},
        ]
        result = filter_by_category(photos, "person")
        assert len(result) == 2
        assert all(p["category"] == "person" for p in result)

    def test_general(self):
        photos = [
            {"category": "person", "photo_id": "p1"},
            {"category": "general", "photo_id": "p2"},
        ]
        result = filter_by_category(photos, "general")
        assert len(result) == 1
        assert result[0]["photo_id"] == "p2"

    def test_empty(self):
        assert filter_by_category([], "person") == []

    def test_no_match(self):
        photos = [{"category": "general", "photo_id": "p1"}]
        assert filter_by_category(photos, "person") == []


# ── get_score_badge ──────────────────────────────────────────────────────────

class TestGetScoreBadge:
    def test_top(self):
        assert "TOP" in get_score_badge(9.5)
        assert "TOP" in get_score_badge(9.0)

    def test_excellent(self):
        badge = get_score_badge(8.5)
        assert "우수" in badge

    def test_good(self):
        badge = get_score_badge(6.5)
        assert "양호" in badge

    def test_average(self):
        badge = get_score_badge(4.0)
        assert "보통" in badge


# ── has_top_location ─────────────────────────────────────────────────────────

class TestHasTopLocation:
    def test_with_location(self):
        report = {"top_location": {"place": "Munich", "count": 74}}
        assert has_top_location(report) is True

    def test_null_location(self):
        report = {"top_location": None}
        assert has_top_location(report) is False

    def test_missing_key(self):
        report = {}
        assert has_top_location(report) is False

    def test_none_report(self):
        assert has_top_location(None) is False


# ── get_portrait_status ──────────────────────────────────────────────────────

class TestGetPortraitStatus:
    def test_eyes_open_smiling(self):
        photo = {"portrait_bonus": {"eyes_open": True, "smiling": True, "adjustment": 0.5}}
        status = get_portrait_status(photo)
        assert "눈 뜸" in status
        assert "미소" in status

    def test_eyes_closed(self):
        photo = {"portrait_bonus": {"eyes_open": False, "smiling": False, "adjustment": 0.0}}
        status = get_portrait_status(photo)
        assert "눈 감음" in status

    def test_no_portrait_bonus(self):
        photo = {"portrait_bonus": None}
        assert get_portrait_status(photo) == ""

    def test_general_photo_no_bonus_key(self):
        photo = {}
        assert get_portrait_status(photo) == ""


# ── get_dominant_tag ─────────────────────────────────────────────────────────

class TestGetDominantTag:
    def test_landscape(self):
        tags = {"selfie": 0.05, "food": 0.03, "landscape": 0.85}
        assert get_dominant_tag(tags) == "풍경"

    def test_selfie(self):
        tags = {"selfie": 0.72, "food": 0.01, "landscape": 0.05}
        assert get_dominant_tag(tags) == "셀카"

    def test_food(self):
        tags = {"selfie": 0.02, "food": 0.78, "landscape": 0.02}
        assert get_dominant_tag(tags) == "음식"

    def test_empty(self):
        assert get_dominant_tag({}) == ""

    def test_face_count_zero_low_confidence_excludes_selfie(self):
        """2026-09-19 사람 보고: 얼굴 없는 사진이 낮은 확신으로 셀카 오분류되던 버그."""
        tags = {"selfie": 0.51, "food": 0.11, "landscape": 0.38}
        assert get_dominant_tag(tags, face_count=0) == "풍경"

    def test_face_count_zero_high_confidence_keeps_selfie(self):
        """2026-09-19 후속 보고: 거울 셀카 등에서 mediapipe가 얼굴을 놓쳐도
        CLIP이 90%+ 확신이면 selfie를 그대로 믿는다 (안 그러면 food/landscape가
        0.3%/0.1% 같은 의미 없는 값으로 '승리'해버림)."""
        tags = {"selfie": 0.9956, "food": 0.0031, "landscape": 0.0014}
        assert get_dominant_tag(tags, face_count=0) == "셀카"

    def test_face_count_none_keeps_old_behavior(self):
        tags = {"selfie": 0.51, "food": 0.11, "landscape": 0.38}
        assert get_dominant_tag(tags) == "셀카"

    def test_face_count_one_allows_selfie(self):
        tags = {"selfie": 0.9, "food": 0.05, "landscape": 0.05}
        assert get_dominant_tag(tags, face_count=1) == "셀카"


# ── 앨범 수 조건 (1개 vs 여러 개) 확인용 헬퍼 ──────────────────────────────

class TestAlbumSelectCondition:
    """앨범 선택 UI 조건 분기 — Streamlit 없이 로직만 검증"""

    def test_single_album_auto_select(self):
        """앨범 1개면 자동 선택 — UI 없음 분기 진입"""
        albums = [{"album_id": "a1", "country": "Japan",
                   "date_range": {"start": "2026-09-01", "end": "2026-09-05"},
                   "photo_count": 120, "cover_photo_id": "p1"}]
        should_show_selectbox = len(albums) > 1
        assert should_show_selectbox is False

    def test_multiple_albums_show_selectbox(self):
        """앨범 2개 이상이면 selectbox 표시"""
        albums = [
            {"album_id": "a1", "country": "Germany",
             "date_range": {"start": "2026-08-01", "end": "2026-08-04"},
             "photo_count": 214, "cover_photo_id": "p1"},
            {"album_id": "a2", "country": "Austria",
             "date_range": {"start": "2026-08-04", "end": "2026-08-07"},
             "photo_count": 98, "cover_photo_id": "p10"},
        ]
        should_show_selectbox = len(albums) > 1
        assert should_show_selectbox is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
