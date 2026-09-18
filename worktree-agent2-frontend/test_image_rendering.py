"""
test_image_rendering.py — 리포트 카드에 실제 사진 썸네일이 렌더링되는지 검증.

브라우저 자동화 도구가 이 환경에 없어서, Streamlit의 AppTest(streamlit.testing.v1)로
실제 살아있는 백엔드(http://localhost:8001) 데이터를 session_state에 주입한 뒤
스크립트를 실행하고, 렌더링된 st.image 요소의 URL이 절대경로(build_image_url 적용됨)인지
직접 확인한다. 2026-09-18 "사진 안 보임" 버그 수정 검증용(이터레이션 4).

실행: python -m pytest test_image_rendering.py -v
(백엔드가 http://localhost:8001에서 실행 중이어야 하고, 앨범이 최소 1개 있어야 함)
"""
import os
import sys

import pytest
import requests

sys.path.insert(0, os.path.dirname(__file__))

BACKEND = "http://localhost:8001"


def _live_backend_data():
    """실제 백엔드에서 앨범+사진+리포트를 가져온다. 백엔드가 없거나 앨범이
    없으면 스킵(별도 인프라 문제이지 이 테스트의 관심사가 아님)."""
    try:
        albums = requests.get(f"{BACKEND}/api/albums", timeout=5).json()
    except Exception as e:
        pytest.skip(f"백엔드 연결 불가: {e}")
    if not albums:
        pytest.skip("업로드된 앨범이 없음 — 먼저 사진을 업로드해야 이 테스트를 돌릴 수 있음")

    album_id = albums[0]["album_id"]
    photos = requests.get(f"{BACKEND}/api/photos", params={"album_id": album_id}, timeout=15).json()
    report = requests.get(f"{BACKEND}/api/report", params={"album_id": album_id}, timeout=15).json()
    return album_id, albums, photos, report


def test_report_highlight_cards_render_real_image_urls():
    from streamlit.testing.v1 import AppTest

    album_id, albums, photos, report = _live_backend_data()
    if not report.get("best_shot"):
        pytest.skip("best_shot이 없는 리포트 — 이 데이터셋으로는 검증 불가")

    # api_client.get_photos()가 하는 것과 동일하게 image_url을 절대 URL로 정규화
    import api_client
    for p in photos:
        p["image_url"] = api_client.build_image_url(p["image_url"])
    photos_lookup = {p["photo_id"]: p for p in photos}

    app_path = os.path.join(os.path.dirname(__file__), "app.py")
    at = AppTest.from_file(app_path, default_timeout=60)
    at.session_state["backend_alive"] = True
    at.session_state["uploaded"] = True
    at.session_state["upload_result"] = {"uploaded_count": len(photos), "photo_ids": list(photos_lookup)}
    at.session_state["albums"] = albums
    at.session_state["selected_album_id"] = album_id
    at.session_state["photos"] = photos
    at.session_state["photos_lookup"] = photos_lookup
    at.session_state["report"] = report
    at.run()

    assert not at.exception, f"앱 실행 중 예외 발생: {at.exception}"

    image_urls = [url for img in at.image for url in img.value]
    assert image_urls, "리포트 화면에 st.image가 하나도 렌더링되지 않음"

    # 모든 이미지 URL이 절대경로(백엔드 주소로 시작)여야 함 — 상대경로가 그대로
    # requests.get()에 넘어가던 예전 버그(problem.md 참고)가 재발하지 않았는지 확인.
    for url in image_urls:
        assert url.startswith(BACKEND), f"상대경로가 그대로 남아있음: {url}"

    best_shot_id = report["best_shot"]["photo_id"]
    best_shot_photo = photos_lookup[best_shot_id]
    expected_prefix = best_shot_photo["image_url"]
    assert any(u.startswith(expected_prefix) for u in image_urls), (
        f"베스트컷(photo_id={best_shot_id}) 썸네일이 렌더링된 이미지 목록에 없음: {image_urls}"
    )


def test_gallery_tabs_render_real_image_urls():
    """베스트컷 랭킹 탭(인물/일반)도 절대 URL 썸네일로 렌더링되는지 확인."""
    from streamlit.testing.v1 import AppTest

    album_id, albums, photos, report = _live_backend_data()

    import api_client
    for p in photos:
        p["image_url"] = api_client.build_image_url(p["image_url"])
    photos_lookup = {p["photo_id"]: p for p in photos}

    app_path = os.path.join(os.path.dirname(__file__), "app.py")
    at = AppTest.from_file(app_path, default_timeout=60)
    at.session_state["backend_alive"] = True
    at.session_state["uploaded"] = True
    at.session_state["upload_result"] = {"uploaded_count": len(photos), "photo_ids": list(photos_lookup)}
    at.session_state["albums"] = albums
    at.session_state["selected_album_id"] = album_id
    at.session_state["photos"] = photos
    at.session_state["photos_lookup"] = photos_lookup
    at.session_state["report"] = report
    at.run()

    assert not at.exception, f"앱 실행 중 예외 발생: {at.exception}"
    image_urls = [url for img in at.image for url in img.value]
    assert image_urls, "갤러리 탭에 st.image가 하나도 렌더링되지 않음"
    for url in image_urls:
        assert url.startswith(BACKEND), f"상대경로가 그대로 남아있음: {url}"
    # 그리드는 썸네일(?size=thumb)을 써야 함 — 성능 최적화 반영 확인
    assert any("size=thumb" in u for u in image_urls), (
        f"갤러리 썸네일이 ?size=thumb를 쓰지 않음: {image_urls[:3]}"
    )


def test_view_button_exists_for_best_shot():
    """리포트 카드에 "크게 보기" 버튼이 있는지 확인 (사람 요청: 버튼으로 원본 보기)."""
    from streamlit.testing.v1 import AppTest

    album_id, albums, photos, report = _live_backend_data()
    if not report.get("best_shot"):
        pytest.skip("best_shot이 없는 리포트 — 이 데이터셋으로는 검증 불가")

    import api_client
    for p in photos:
        p["image_url"] = api_client.build_image_url(p["image_url"])
    photos_lookup = {p["photo_id"]: p for p in photos}

    app_path = os.path.join(os.path.dirname(__file__), "app.py")
    at = AppTest.from_file(app_path, default_timeout=60)
    at.session_state["backend_alive"] = True
    at.session_state["uploaded"] = True
    at.session_state["upload_result"] = {"uploaded_count": len(photos), "photo_ids": list(photos_lookup)}
    at.session_state["albums"] = albums
    at.session_state["selected_album_id"] = album_id
    at.session_state["photos"] = photos
    at.session_state["photos_lookup"] = photos_lookup
    at.session_state["report"] = report
    at.run()

    assert not at.exception
    button_labels = [b.label for b in at.button]
    assert any("크게 보기" in label for label in button_labels), (
        f"'크게 보기' 버튼이 없음. 버튼 목록: {button_labels}"
    )
