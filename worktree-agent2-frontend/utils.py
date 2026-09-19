"""
utils.py — 화면 렌더링에 쓰이는 순수 함수들 (유닛테스트 대상)
Streamlit 임포트 없이 독립적으로 테스트 가능하도록 유지한다.
"""

from typing import Optional


def format_album_label(album: dict) -> str:
    """
    앨범 선택 UI 라벨 포맷.
    country가 None이면 날짜 범위만, 아니면 국가명+날짜+사진수 표시.
    예: "독일 (8/2~8/4, 214장)" 또는 "(7/28~7/31, 53장)"
    """
    dr = album.get("date_range", {})
    start = dr.get("start", "")
    end = dr.get("end", "")

    # 날짜 단축 표현 (YYYY-MM-DD → M/D)
    def shorten(d: str) -> str:
        if not d:
            return ""
        parts = d.split("-")
        if len(parts) == 3:
            return f"{int(parts[1])}/{int(parts[2])}"
        return d

    date_str = f"{shorten(start)}~{shorten(end)}"
    count = album.get("photo_count", 0)
    country = album.get("country")

    if country:
        return f"{country} ({date_str}, {count}장)"
    else:
        return f"({date_str}, {count}장)"


def sort_photos_by_score(photos: list) -> list:
    """aesthetic_score 내림차순 정렬. is_blurry=True는 맨 뒤로."""
    non_blurry = [p for p in photos if not p.get("is_blurry", False)]
    blurry = [p for p in photos if p.get("is_blurry", False)]
    non_blurry_sorted = sorted(non_blurry, key=lambda p: p.get("aesthetic_score", 0), reverse=True)
    return non_blurry_sorted + blurry


def filter_by_category(photos: list, category: str) -> list:
    """category('person' or 'general')로 필터링."""
    return [p for p in photos if p.get("category") == category]


def get_score_badge(score: float) -> str:
    """미학 점수를 배지 텍스트로 변환."""
    if score >= 9.0:
        return "🏆 TOP"
    elif score >= 8.0:
        return "⭐ 우수"
    elif score >= 6.0:
        return "✅ 양호"
    else:
        return "⚠️ 보통"


def format_score(score: float) -> str:
    return f"{score:.1f}"


def has_top_location(report: Optional[dict]) -> bool:
    """리포트에 top_location이 있으면 True (null이면 False)."""
    if report is None:
        return False
    return report.get("top_location") is not None


def get_portrait_status(photo: dict) -> str:
    """인물 사진의 눈감음/미소 상태 텍스트."""
    pb = photo.get("portrait_bonus")
    if not pb:
        return ""
    parts = []
    if pb.get("eyes_open"):
        parts.append("눈 뜸 ✅")
    else:
        parts.append("눈 감음 ❌")
    if pb.get("smiling"):
        parts.append("미소 ✅")
    return " · ".join(parts) if parts else ""


def get_dominant_tag(zero_shot_tags: dict, face_count: Optional[int] = None) -> str:
    """가장 높은 점수의 제로샷 태그 반환.

    face_count=0이 명시되면 'selfie' 태그는 후보에서 제외한다 (2026-09-19,
    사람이 보고: 얼굴이 없는 건축물/풍경 사진이 CLIP 제로샷 오분류로 셀카로
    표시되던 문제 — 백엔드 app/report.py의 동일 수정과 짝을 맞춘 것).
    face_count를 안 넘기면(None) 기존과 동일하게 동작한다.
    """
    if not zero_shot_tags:
        return ""
    candidates = zero_shot_tags
    if face_count == 0:
        candidates = {k: v for k, v in candidates.items() if k != "selfie"}
        if not candidates:
            return ""
    tag = max(candidates, key=lambda k: candidates[k])
    labels = {"selfie": "셀카", "food": "음식", "landscape": "풍경"}
    return labels.get(tag, tag)
