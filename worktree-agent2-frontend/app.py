"""
app.py — 여행 사진 베스트컷 서비스 (Agent 2, Streamlit)
실행: streamlit run app.py
포트: 8501 (기본값)

CONTRACT.md 준수 사항:
- 백엔드(포트 8000) FastAPI를 requests로 서버사이드 호출
- 모든 처리 결과와 선택 상태는 st.session_state에 저장해서 재실행마다 재처리 방지
- API 미구현 시 mock_data.py의 목업 데이터로 폴백
"""

import streamlit as st
import requests as req
from io import BytesIO
import sys
import os

# worktree 내 모듈 임포트
sys.path.insert(0, os.path.dirname(__file__))
import api_client
import utils

# ── 페이지 설정 ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="여행 베스트컷 | Travel Photo AI",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── 전역 CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
}

/* 전체 배경 */
.stApp {
    background: linear-gradient(135deg, #0f0c29 0%, #1a1040 40%, #0d1b3e 100%);
    min-height: 100vh;
}

/* 헤더 영역 */
.hero-header {
    text-align: center;
    padding: 2.5rem 1rem 1.5rem;
}
.hero-title {
    font-size: 3rem;
    font-weight: 700;
    background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0;
    line-height: 1.2;
}
.hero-subtitle {
    color: #94a3b8;
    font-size: 1.1rem;
    margin-top: 0.5rem;
}

/* 업로드 섹션 */
.upload-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(167,139,250,0.3);
    border-radius: 16px;
    padding: 2rem;
    margin: 1rem 0;
    backdrop-filter: blur(10px);
}

/* 앨범 카드 */
.album-select-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(96,165,250,0.25);
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1rem 0;
}

/* 사진 카드 */
.photo-card {
    background: rgba(255,255,255,0.05);
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.08);
    transition: transform 0.2s ease, border-color 0.2s ease;
    margin-bottom: 1rem;
}
.photo-card:hover {
    transform: translateY(-2px);
    border-color: rgba(167,139,250,0.5);
}
.score-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    background: linear-gradient(90deg, #7c3aed, #4f46e5);
    color: white;
}
.blurry-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    background: rgba(239,68,68,0.2);
    color: #f87171;
    border: 1px solid rgba(239,68,68,0.3);
}

/* 메트릭 카드 */
.metric-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 14px;
    padding: 1.25rem 1rem;
    text-align: center;
    transition: background 0.2s;
}
.metric-card:hover {
    background: rgba(255,255,255,0.08);
}
.metric-value {
    font-size: 2.2rem;
    font-weight: 700;
    color: #a78bfa;
    line-height: 1;
}
.metric-label {
    font-size: 0.85rem;
    color: #94a3b8;
    margin-top: 0.35rem;
}
.metric-icon {
    font-size: 1.5rem;
    margin-bottom: 0.4rem;
}

/* 섹션 헤더 */
.section-header {
    font-size: 1.4rem;
    font-weight: 600;
    color: #e2e8f0;
    margin: 2rem 0 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* 후기 글 박스 */
.post-output {
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(167,139,250,0.3);
    border-radius: 12px;
    padding: 1.5rem;
}

/* Streamlit 기본 요소 스타일 오버라이드 */
div[data-testid="stFileUploaderDropzone"] {
    background: rgba(167,139,250,0.07) !important;
    border: 2px dashed rgba(167,139,250,0.4) !important;
    border-radius: 12px !important;
}
div[data-testid="stTabs"] button {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 500 !important;
}
.stButton > button {
    background: linear-gradient(135deg, #7c3aed, #4f46e5) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.6rem 1.5rem !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover {
    opacity: 0.85 !important;
}

/* 상태 알림 배너 */
.status-banner {
    background: rgba(52,211,153,0.1);
    border: 1px solid rgba(52,211,153,0.3);
    border-radius: 10px;
    padding: 0.75rem 1rem;
    color: #34d399;
    font-size: 0.9rem;
    margin: 0.5rem 0;
}
.status-banner-warn {
    background: rgba(251,191,36,0.1);
    border: 1px solid rgba(251,191,36,0.3);
    border-radius: 10px;
    padding: 0.75rem 1rem;
    color: #fbbf24;
    font-size: 0.9rem;
    margin: 0.5rem 0;
}
.mock-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 0.7rem;
    background: rgba(251,191,36,0.15);
    color: #fbbf24;
    border: 1px solid rgba(251,191,36,0.3);
    vertical-align: middle;
    margin-left: 6px;
}
</style>
""", unsafe_allow_html=True)


# ── 헬퍼 함수 ─────────────────────────────────────────────────────────────────

def _backend_alive() -> bool:
    try:
        r = req.get("http://localhost:8000/docs", timeout=2)
        return r.status_code < 500
    except Exception:
        return False


def _load_image_bytes(image_url: str):
    """image_url에서 이미지 바이트를 가져온다. 실패 시 None 반환."""
    try:
        r = req.get(image_url, timeout=5)
        if r.status_code == 200:
            return BytesIO(r.content)
    except Exception:
        pass
    return None


def _render_photo_card(photo: dict, rank: int | None = None):
    """사진 1장 카드 렌더링. image_url로 이미지 로드 시도."""
    score = photo.get("aesthetic_score", 0)
    is_blurry = photo.get("is_blurry", False)

    # 이미지 로드
    img_bytes = _load_image_bytes(photo.get("image_url", ""))

    # 카드 헤더 (순위 + 점수)
    rank_str = f"#{rank} " if rank else ""
    badge = utils.get_score_badge(score)
    blurry_tag = ' <span class="blurry-badge">흔들림</span>' if is_blurry else ""

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
        f'<span style="color:#94a3b8;font-size:0.8rem;font-weight:600;">{rank_str}</span>'
        f'<span class="score-badge">{badge} {utils.format_score(score)}</span>'
        f'{blurry_tag}'
        f'</div>',
        unsafe_allow_html=True
    )

    # 이미지 출력
    if img_bytes:
        st.image(img_bytes, use_container_width=True)
    else:
        # 이미지 없는 경우 플레이스홀더
        st.markdown(
            f'<div style="background:linear-gradient(135deg,#1e1b4b,#312e81);'
            f'border-radius:10px;height:180px;display:flex;align-items:center;'
            f'justify-content:center;color:#6366f1;font-size:2rem;">📷</div>',
            unsafe_allow_html=True
        )

    # 메타 정보
    dominant = utils.get_dominant_tag(photo.get("zero_shot_tags", {}))
    portrait_status = utils.get_portrait_status(photo)
    face_count = photo.get("face_count", 0)

    meta_parts = []
    if dominant:
        meta_parts.append(dominant)
    if face_count > 0:
        meta_parts.append(f"👤 {face_count}명")
    if portrait_status:
        meta_parts.append(portrait_status)
    if photo.get("duplicate_group_id"):
        meta_parts.append("🔁 중복 그룹")

    if meta_parts:
        st.markdown(
            f'<div style="color:#94a3b8;font-size:0.75rem;margin-top:4px;">'
            + " · ".join(meta_parts) + "</div>",
            unsafe_allow_html=True
        )


# ── 세션 상태 초기화 ─────────────────────────────────────────────────────────
if "uploaded" not in st.session_state:
    st.session_state.uploaded = False
if "upload_result" not in st.session_state:
    st.session_state.upload_result = None
if "albums" not in st.session_state:
    st.session_state.albums = None
if "selected_album_id" not in st.session_state:
    st.session_state.selected_album_id = None
if "photos" not in st.session_state:
    st.session_state.photos = None
if "report" not in st.session_state:
    st.session_state.report = None
if "use_mock" not in st.session_state:
    st.session_state.use_mock = not _backend_alive()


# ── 헤더 ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-header">
    <h1 class="hero-title">📸 여행 베스트컷 AI</h1>
    <p class="hero-subtitle">여행 사진을 업로드하면 AI가 베스트컷을 골라드립니다</p>
</div>
""", unsafe_allow_html=True)

# 백엔드 상태 표시
if st.session_state.use_mock:
    st.markdown(
        '<div class="status-banner-warn">⚠️ 백엔드 서버(포트 8000)에 연결할 수 없습니다 — 목업 데이터로 화면을 표시합니다</div>',
        unsafe_allow_html=True
    )
else:
    st.markdown(
        '<div class="status-banner">✅ 백엔드 서버 연결됨</div>',
        unsafe_allow_html=True
    )

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# [P0] Task 1: 업로드 UI
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📤 사진 업로드</div>', unsafe_allow_html=True)

with st.container():
    uploaded_files = st.file_uploader(
        "여행 사진을 선택하세요 (여러 장 동시 선택 가능)",
        type=["jpg", "jpeg", "png", "heic"],
        accept_multiple_files=True,
        key="file_uploader",
        help="JPEG, PNG, HEIC 형식 지원 · 다중 선택 가능"
    )

    col_btn, col_status = st.columns([1, 3])
    with col_btn:
        process_btn = st.button(
            "🚀 분석 시작",
            disabled=(not uploaded_files),
            use_container_width=True,
        )

    if process_btn and uploaded_files:
        with st.spinner(f"📊 {len(uploaded_files)}장 사진을 분석 중입니다... (블러 감지, 중복 제거, 앨범 분류)"):
            if st.session_state.use_mock:
                # 목업: 업로드 성공 응답 시뮬레이션
                st.session_state.upload_result = {
                    "uploaded_count": len(uploaded_files),
                    "photo_ids": [f"photo-{i:03d}" for i in range(len(uploaded_files))]
                }
                # 목업 앨범과 사진 데이터 로드
                st.session_state.albums = api_client.get_albums()
                st.session_state.photos = None  # 앨범 선택 후 로드
                st.session_state.report = None
                st.session_state.uploaded = True
                st.session_state.selected_album_id = None
            else:
                result = api_client.upload_photos(uploaded_files)
                if "error" in result:
                    st.error(f"업로드 실패: {result['error']}")
                else:
                    st.session_state.upload_result = result
                    st.session_state.albums = api_client.get_albums()
                    st.session_state.uploaded = True
                    st.session_state.selected_album_id = None
                    st.session_state.photos = None
                    st.session_state.report = None

        if st.session_state.uploaded:
            st.success(f"✅ {st.session_state.upload_result['uploaded_count']}장 업로드 완료! 앨범이 자동 분류되었습니다.")

if st.session_state.uploaded and st.session_state.upload_result:
    res = st.session_state.upload_result
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-icon">🖼️</div>'
            f'<div class="metric-value">{res["uploaded_count"]}</div>'
            f'<div class="metric-label">업로드된 사진</div></div>',
            unsafe_allow_html=True
        )
    with c2:
        album_count = len(st.session_state.albums) if st.session_state.albums else "—"
        st.markdown(
            f'<div class="metric-card"><div class="metric-icon">🗂️</div>'
            f'<div class="metric-value">{album_count}</div>'
            f'<div class="metric-label">분류된 앨범</div></div>',
            unsafe_allow_html=True
        )

# ══════════════════════════════════════════════════════════════════════════════
# [P0] Task 2: 앨범 선택 UI
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.uploaded and st.session_state.albums:
    st.markdown("---")
    st.markdown('<div class="section-header">🗂️ 앨범 선택</div>', unsafe_allow_html=True)

    albums = st.session_state.albums

    if len(albums) == 1:
        # 앨범 1개: 자동 선택, UI 없음
        album = albums[0]
        label = utils.format_album_label(album)
        st.markdown(
            f'<div class="status-banner">🗂️ 앨범 자동 선택: <strong>{label}</strong></div>',
            unsafe_allow_html=True
        )
        if st.session_state.selected_album_id != album["album_id"]:
            st.session_state.selected_album_id = album["album_id"]
            st.session_state.photos = None
            st.session_state.report = None

    else:
        # 앨범 2개 이상: selectbox로 선택
        labels = [utils.format_album_label(a) for a in albums]
        album_ids = [a["album_id"] for a in albums]

        # 현재 선택된 앨범의 인덱스 찾기
        current_idx = 0
        if st.session_state.selected_album_id in album_ids:
            current_idx = album_ids.index(st.session_state.selected_album_id)

        selected_label = st.selectbox(
            "여행 앨범을 선택하세요",
            options=labels,
            index=current_idx,
            key="album_selectbox",
        )
        selected_idx = labels.index(selected_label)
        new_album_id = album_ids[selected_idx]

        if new_album_id != st.session_state.selected_album_id:
            st.session_state.selected_album_id = new_album_id
            st.session_state.photos = None  # 앨범 바뀌면 사진/리포트 초기화
            st.session_state.report = None

    # 선택된 앨범의 사진 로드 (session_state에 캐시)
    if st.session_state.selected_album_id and st.session_state.photos is None:
        with st.spinner("사진 목록 불러오는 중..."):
            st.session_state.photos = api_client.get_photos(st.session_state.selected_album_id)


# ══════════════════════════════════════════════════════════════════════════════
# [P0] Task 3: 베스트컷 랭킹 화면
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.photos is not None:
    st.markdown("---")
    mock_tag = '<span class="mock-badge">목업</span>' if st.session_state.use_mock else ""
    st.markdown(
        f'<div class="section-header">🏆 베스트컷 랭킹{mock_tag}</div>',
        unsafe_allow_html=True
    )

    photos = st.session_state.photos
    person_photos = utils.sort_photos_by_score(utils.filter_by_category(photos, "person"))
    general_photos = utils.sort_photos_by_score(utils.filter_by_category(photos, "general"))

    tab_person, tab_general = st.tabs([
        f"👤 인물 ({len(person_photos)}장)",
        f"🏞️ 일반 ({len(general_photos)}장)"
    ])

    COLS = 3  # 한 줄에 3장

    with tab_person:
        if not person_photos:
            st.info("인물 사진이 없습니다.")
        else:
            for row_start in range(0, len(person_photos), COLS):
                batch = person_photos[row_start:row_start + COLS]
                cols = st.columns(COLS)
                for i, photo in enumerate(batch):
                    with cols[i]:
                        _render_photo_card(photo, rank=row_start + i + 1)

    with tab_general:
        if not general_photos:
            st.info("일반 사진이 없습니다.")
        else:
            for row_start in range(0, len(general_photos), COLS):
                batch = general_photos[row_start:row_start + COLS]
                cols = st.columns(COLS)
                for i, photo in enumerate(batch):
                    with cols[i]:
                        _render_photo_card(photo, rank=row_start + i + 1)


# ══════════════════════════════════════════════════════════════════════════════
# [P1] Task 4: 리포트 카드 UI
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.selected_album_id:
    st.markdown("---")
    mock_tag = '<span class="mock-badge">목업</span>' if st.session_state.use_mock else ""
    st.markdown(
        f'<div class="section-header">📊 여행 리포트{mock_tag}</div>',
        unsafe_allow_html=True
    )

    # 리포트 로드 (session_state 캐시)
    if st.session_state.report is None:
        with st.spinner("리포트 생성 중..."):
            st.session_state.report = api_client.get_report(st.session_state.selected_album_id)

    report = st.session_state.report

    if report:
        # ── 상단 숫자 지표 ─────────────────────────────────────────────────
        st.markdown("#### 📈 통계 요약")
        mc1, mc2, mc3, mc4, mc5 = st.columns(5)
        metrics = [
            (mc1, "🖼️", report.get("total_photos", 0), "총 사진"),
            (mc2, "🤳", report.get("selfie_count", 0), "셀카"),
            (mc3, "🍽️", report.get("food_count", 0), "음식"),
            (mc4, "🏞️", report.get("landscape_count", 0), "풍경"),
            (mc5, "💨", report.get("blurry_count", 0), "흔들린 사진"),
        ]
        for col, icon, val, label in metrics:
            with col:
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-icon">{icon}</div>'
                    f'<div class="metric-value">{val}</div>'
                    f'<div class="metric-label">{label}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        st.markdown("")

        # ── 하단 하이라이트 카드 ───────────────────────────────────────────
        st.markdown("#### 🌟 하이라이트")
        hc1, hc2, hc3 = st.columns(3)

        # 베스트컷
        best = report.get("best_shot", {})
        with hc1:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-icon">🏆</div>'
                f'<div style="color:#a78bfa;font-weight:600;font-size:0.95rem;">베스트컷</div>'
                f'<div class="metric-value">{best.get("aesthetic_score", "—")}</div>'
                f'<div class="metric-label">미학 점수</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        # 최고 단체사진
        group = report.get("best_group_photo", {})
        with hc2:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-icon">👥</div>'
                f'<div style="color:#60a5fa;font-weight:600;font-size:0.95rem;">최고 단체사진</div>'
                f'<div class="metric-value">{group.get("aesthetic_score", "—")}</div>'
                f'<div class="metric-label">{group.get("face_count", 0)}명 등장</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        # 눈 감은 사진 / 최다 재촬영
        eyes_closed = report.get("eyes_closed_count", 0)
        most_retaken = report.get("most_retaken", {})
        with hc3:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-icon">😑</div>'
                f'<div style="color:#f472b6;font-weight:600;font-size:0.95rem;">눈 감은 사진</div>'
                f'<div class="metric-value">{eyes_closed}</div>'
                f'<div class="metric-label">최다 재촬영 {most_retaken.get("count", 0)}장</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        # top_location: null이면 카드 렌더링하지 않음 (CONTRACT.md 3장)
        if utils.has_top_location(report):
            loc = report["top_location"]
            st.markdown("")
            st.markdown(
                f'<div class="metric-card" style="max-width:300px;">'
                f'<div class="metric-icon">📍</div>'
                f'<div style="color:#34d399;font-weight:600;font-size:1rem;">{loc["place"]}</div>'
                f'<div class="metric-label">가장 많이 찍은 장소 · {loc["count"]}장</div>'
                f'</div>',
                unsafe_allow_html=True
            )


# ══════════════════════════════════════════════════════════════════════════════
# [P1] Task 5: 후기 글 생성 UI
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.report and st.session_state.selected_album_id:
    st.markdown("---")
    mock_tag = '<span class="mock-badge">목업</span>' if st.session_state.use_mock else ""
    st.markdown(
        f'<div class="section-header">✍️ 여행 후기 글 생성{mock_tag}</div>',
        unsafe_allow_html=True
    )

    style_choice = st.radio(
        "글 스타일 선택",
        options=["blog", "instagram"],
        format_func=lambda x: "📝 블로그 스타일" if x == "blog" else "📱 인스타그램 스타일",
        horizontal=True,
        key="post_style_radio",
    )

    gen_col, _ = st.columns([1, 3])
    with gen_col:
        generate_btn = st.button("✨ 후기 글 생성", key="generate_post_btn", use_container_width=True)

    if generate_btn:
        report = st.session_state.report
        # 베스트컷 상위 3장의 photo_id 추출
        photos = st.session_state.photos or []
        sorted_all = utils.sort_photos_by_score(photos)
        best_ids = [p["photo_id"] for p in sorted_all[:3]]

        with st.spinner("AI가 후기 글을 작성 중입니다..."):
            result = api_client.generate_post(style_choice, report, best_ids)

        if "text" in result:
            is_mock = result.get("_is_mock", False)
            if is_mock:
                st.markdown(
                    '<div class="status-banner-warn">ℹ️ 백엔드 미연결 — 예시 텍스트입니다. 실제 API 연결 후 Claude AI가 생성합니다.</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<div class="status-banner">✅ AI 후기 글 생성 완료</div>',
                    unsafe_allow_html=True
                )
            # CONTRACT.md: st.code(text, language=None)으로 표시 (내장 복사 아이콘 활용)
            st.code(result["text"], language=None)
        else:
            st.error("글 생성에 실패했습니다.")

# ── 푸터 ──────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<div style="text-align:center;color:#475569;font-size:0.8rem;padding:1rem;">'
    '여행 베스트컷 AI · Agent 2 (Streamlit) · 백엔드: Agent 1 (FastAPI :8000)'
    '</div>',
    unsafe_allow_html=True
)
