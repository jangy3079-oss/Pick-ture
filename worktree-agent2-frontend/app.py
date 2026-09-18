"""
app.py — 여행 사진 베스트컷 서비스 (Agent 2, Streamlit)
실행: streamlit run app.py  →  http://localhost:8501
백엔드: http://localhost:8001 (Agent 1, FastAPI)

CONTRACT.md 준수:
- 목업/하드코딩 없음, 실 백엔드만 사용
- 모든 상태는 st.session_state에 저장 (재실행 시 재처리 방지)
- nullable 필드(best_group_photo, top_location 등) null이면 카드 숨김
- 이미지: st.image(절대_URL)으로 브라우저 직접 로드 (서버사이드 바이트 요청 없음 → 빠름)
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import api_client
import utils

# ── 페이지 설정 ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="여행 베스트컷 | Travel Photo AI",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── 전역 CSS: 화이트 미니멀 테마 ────────────────────────────────────────────────
# 가정(2026-09-18, 사람 요청 "화이트 배경 미니멀 UI, 좌우 여백 확대, 비대칭 수정"):
# 정확한 색상/여백 수치는 지정되지 않아 합리적인 기본값으로 판단해 적용함.
# 포인트 컬러는 짙은 남색(#1E293B) 하나만 사용, 카드는 테두리 없이 얇은 구분선 +
# 여백으로만 구획, 본문 최대폭을 제한해 중앙 정렬(좌우 여백 확보).
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }

:root {
    --accent: #1E293B;
    --text-primary: #1A1A1A;
    --text-secondary: #6B7280;
    --divider: #E5E7EB;
    --surface: #FAFAFA;
}

.stApp { background: #FFFFFF; min-height: 100vh; }

/* 본문 폭 제한 + 좌우 여백 확보 (비대칭 방지, 중앙 정렬) */
.block-container {
    max-width: 1080px; margin: 0 auto;
    padding-left: 3rem !important; padding-right: 3rem !important;
    padding-top: 2rem !important;
}

/* 헤더 */
.hero-title {
    font-size: 2.4rem; font-weight: 700; color: var(--text-primary);
    margin: 0; line-height: 1.2; text-align: center;
}
.hero-subtitle { color: var(--text-secondary); font-size:1rem; margin-top:0.5rem; text-align:center; }

/* 섹션 헤더 */
.section-header {
    font-size:1.2rem; font-weight:600; color: var(--text-primary);
    margin:2.2rem 0 1.1rem; padding-bottom:0.6rem;
    border-bottom: 1px solid var(--divider);
    display:flex; align-items:center; gap:0.5rem;
}

/* 메트릭 카드 — 테두리 대신 여백+얇은 구분선 */
.metric-card {
    background: var(--surface); border: 1px solid var(--divider);
    border-radius:10px; padding:1.2rem 0.9rem; text-align:center;
    height: 100%;
}
.metric-value { font-size:1.9rem; font-weight:700; color: var(--text-primary); line-height:1; }
.metric-label { font-size:0.8rem; color: var(--text-secondary); margin-top:0.35rem; }
.metric-icon { font-size:1.3rem; margin-bottom:0.4rem; opacity: 0.7; }

/* 사진 카드 */
.photo-meta {
    color: var(--text-secondary); font-size:0.72rem; margin-top:4px;
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}
.rank-badge {
    display:inline-block; padding:1px 8px; border-radius:20px;
    font-size:0.72rem; font-weight:600;
    background: var(--accent); color:white; margin-bottom:4px;
}
.blurry-badge {
    display:inline-block; padding:1px 8px; border-radius:20px;
    font-size:0.72rem; font-weight:600;
    background:#FEF2F2; color:#DC2626;
    border:1px solid #FECACA; margin-bottom:4px; margin-left:4px;
}

/* 상태 배너 */
.status-ok {
    background:#F0FDF4; border:1px solid #BBF7D0;
    border-radius:8px; padding:0.65rem 1rem; color:#15803D; font-size:0.85rem; margin:0.4rem 0;
}
.status-warn {
    background:#FFFBEB; border:1px solid #FDE68A;
    border-radius:8px; padding:0.65rem 1rem; color:#B45309; font-size:0.85rem; margin:0.4rem 0;
}
.status-err {
    background:#FEF2F2; border:1px solid #FECACA;
    border-radius:8px; padding:0.65rem 1rem; color:#B91C1C; font-size:0.85rem; margin:0.4rem 0;
}

/* 버튼 — 절제된 단색 */
.stButton > button {
    background: var(--accent) !important;
    color:white !important; border:none !important; border-radius:8px !important;
    padding:0.5rem 1.3rem !important; font-family:'Outfit',sans-serif !important;
    font-weight:500 !important; transition:opacity 0.2s !important; box-shadow:none !important;
}
.stButton > button:hover { opacity:0.85 !important; }
.stButton > button:disabled { opacity:0.35 !important; }

/* 보조 버튼(사진 크게 보기 등) */
.stButton > button[kind="secondary"] {
    background: #FFFFFF !important; color: var(--accent) !important;
    border: 1px solid var(--divider) !important;
}

/* 파일 업로더 */
div[data-testid="stFileUploaderDropzone"] {
    background: var(--surface) !important;
    border:1.5px dashed #D1D5DB !important;
    border-radius:10px !important;
}

/* 이미지 캡션 */
.stImage > figcaption { color: var(--text-secondary) !important; font-size:0.75rem !important; }

/* 썸네일 컨테이너 */
.thumb-container {
    background: var(--surface);
    border:1px solid var(--divider);
    border-radius:8px; overflow:hidden; margin-bottom:8px;
}

hr { border-color: var(--divider) !important; }
</style>
""", unsafe_allow_html=True)


# ── 사진 크게 보기 (모달) ────────────────────────────────────────────────────
# 사람 요청(2026-09-18): 리포트 카드의 사진도 버튼을 눌러 크게 볼 수 있어야 함.
@st.dialog("사진 보기", width="large")
def _show_photo_dialog(photo: dict, label: str = ""):
    img_url = api_client.build_image_url(photo.get("image_url", ""))
    if img_url:
        st.image(img_url, use_container_width=True)
    caption_parts = [p for p in [label, photo.get("filename")] if p]
    score = photo.get("aesthetic_score")
    if score is not None:
        caption_parts.append(f"미학 점수 {score:.1f}")
    if caption_parts:
        st.caption(" · ".join(caption_parts))


def _view_button(photo: dict, label: str, key: str):
    """리포트 카드 등에서 "크게 보기" 버튼 하나를 렌더링, 누르면 원본 화질 모달."""
    if st.button("🔍 크게 보기", key=key, use_container_width=True):
        _show_photo_dialog(photo, label)


# ── 갤러리 렌더링 헬퍼 ───────────────────────────────────────────────────────
GALLERY_DEFAULT = 12  # 처음 보여줄 장수
GALLERY_COLS = 4      # 컬럼 수
PLACEHOLDER_HTML = (
    '<div style="background:#F5F5F5;border:1px solid #E5E7EB;border-radius:8px;'
    'height:160px;display:flex;align-items:center;justify-content:center;'
    'color:#9CA3AF;font-size:1.8rem;">📷</div>'
)


def _render_gallery(photos: list, session_key: str):
    """
    photos 리스트를 그리드로 렌더링한다.
    - 그리드에는 썸네일(?size=thumb, 300px)을 써서 로딩을 빠르게 하고,
      "크게 보기" 버튼을 누르면 원본 화질을 모달로 보여준다.
    - 12장 초과 시 "더 보기" 버튼 제공
    - session_key: "더 보기" 상태를 구분하기 위한 고유 키
    """
    if not photos:
        st.info("사진이 없습니다.")
        return

    # "더 보기" 상태 초기화
    expand_key = f"gallery_expand_{session_key}"
    if expand_key not in st.session_state:
        st.session_state[expand_key] = False

    show_all = st.session_state[expand_key]
    display_photos = photos if show_all else photos[:GALLERY_DEFAULT]

    # 그리드 렌더링
    for row_start in range(0, len(display_photos), GALLERY_COLS):
        batch = display_photos[row_start:row_start + GALLERY_COLS]
        cols = st.columns(GALLERY_COLS)
        for i, photo in enumerate(batch):
            with cols[i]:
                rank = row_start + i + 1
                score = photo.get("aesthetic_score", 0)
                is_blurry = photo.get("is_blurry", False)
                # image_url은 api_client.get_photos()가 이미 절대 URL로 정규화해서
                # 주지만, 방어적으로 한 번 더 build_image_url()을 통과시킨다
                # (build_image_url은 이미 절대 URL이면 그대로 반환하는 멱등 함수).
                img_url = api_client.build_image_url(photo.get("image_url", ""))

                # 배지 (순위 + 점수)
                badge_html = (
                    f'<div>'
                    f'<span class="rank-badge">#{rank} · {score:.1f}점</span>'
                )
                if is_blurry:
                    badge_html += '<span class="blurry-badge">흔들림</span>'
                badge_html += '</div>'
                st.markdown(badge_html, unsafe_allow_html=True)

                # 이미지 — 그리드에서는 썸네일(빠름), 원본은 버튼으로
                if img_url:
                    try:
                        st.image(f"{img_url}?size=thumb", use_container_width=True)
                    except Exception:
                        st.markdown(PLACEHOLDER_HTML, unsafe_allow_html=True)
                    if st.button(
                        "🔍 크게 보기", key=f"view_{session_key}_{photo.get('photo_id', rank)}",
                        use_container_width=True,
                    ):
                        _show_photo_dialog(photo, f"#{rank}")
                else:
                    st.markdown(PLACEHOLDER_HTML, unsafe_allow_html=True)

                # 메타 태그
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
                    meta_parts.append("🔁 중복")
                if meta_parts:
                    st.markdown(
                        f'<div class="photo-meta">' + " · ".join(meta_parts) + "</div>",
                        unsafe_allow_html=True
                    )

    # 더 보기 / 접기 버튼
    if len(photos) > GALLERY_DEFAULT:
        remaining = len(photos) - GALLERY_DEFAULT
        if not show_all:
            if st.button(f"📂 더 보기 ({remaining}장 더)", key=f"expand_{session_key}"):
                st.session_state[expand_key] = True
                st.rerun()
        else:
            if st.button(f"▲ 접기", key=f"collapse_{session_key}"):
                st.session_state[expand_key] = False
                st.rerun()


def _render_photo_thumb(photo_id: str, label: str, photos_lookup: dict):
    """
    리포트 카드 내 단일 사진 썸네일 렌더링 + "크게 보기" 버튼.
    photos_lookup: {photo_id: photo_dict} 형태.
    """
    photo = photos_lookup.get(photo_id)
    if not photo:
        st.caption(f"{label}: 사진 정보 없음")
        return
    img_url = api_client.build_image_url(photo.get("image_url", ""))
    score = photo.get("aesthetic_score", 0)
    st.markdown(
        f'<div style="font-size:0.78rem;color:#6B7280;margin-bottom:4px;">'
        f'{label} · {score:.1f}점</div>',
        unsafe_allow_html=True
    )
    if img_url:
        try:
            st.image(f"{img_url}?size=thumb", use_container_width=True)
        except Exception:
            st.markdown(PLACEHOLDER_HTML, unsafe_allow_html=True)
        _view_button(photo, label, key=f"view_thumb_{photo_id}")
    else:
        st.markdown(PLACEHOLDER_HTML, unsafe_allow_html=True)


# ── 세션 상태 초기화 ──────────────────────────────────────────────────────────
_defaults = {
    "uploaded": False,
    "upload_result": None,
    "albums": None,
    "selected_album_id": None,
    "photos": None,
    "photos_lookup": None,   # {photo_id: photo} — 리포트 썸네일 조회용
    "report": None,
    "backend_alive": None,
    "last_error": None,
    "post_result": None,     # 생성된 후기 글 (재실행 시 유지)
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.backend_alive is None:
    st.session_state.backend_alive = api_client.is_backend_alive()


# ── 사이드바 ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📊 서비스 정보")
    st.markdown("---")
    alive = st.session_state.backend_alive
    color, icon, label = ("#15803D", "🟢", "연결됨 (:8001)") if alive else ("#B91C1C", "🔴", "연결 안 됨 (:8001)")
    st.markdown(
        f'<div style="padding:0.5rem;background:#FAFAFA;border:1px solid #E5E7EB;border-radius:8px;">'
        f'{icon} 백엔드: <span style="color:{color};font-weight:600;">{label}</span></div>',
        unsafe_allow_html=True
    )
    if st.button("🔄 연결 재시도", key="retry_backend", use_container_width=True):
        st.session_state.backend_alive = api_client.is_backend_alive()
        st.rerun()
    st.markdown("---")
    st.markdown("**포트** 8501 (Streamlit)")
    st.markdown("**백엔드** FastAPI :8001")
    if st.session_state.last_error:
        st.markdown("---")
        st.error(st.session_state.last_error)


# ── 헤더 ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding:2rem 1rem 1rem;text-align:center;">
    <h1 class="hero-title">📸 여행 베스트컷 AI</h1>
    <p class="hero-subtitle">여행 사진을 업로드하면 AI가 베스트컷을 골라드립니다</p>
</div>
""", unsafe_allow_html=True)

if not st.session_state.backend_alive:
    st.markdown(
        '<div class="status-err">🔴 백엔드 서버(http://localhost:8001)에 연결할 수 없습니다.'
        ' 사이드바의 [연결 재시도] 버튼을 눌러 다시 시도하세요.</div>',
        unsafe_allow_html=True
    )
    st.stop()

st.markdown('<div class="status-ok">✅ 백엔드 서버 연결됨 (http://localhost:8001)</div>',
            unsafe_allow_html=True)
st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# [P0] 1. 업로드 UI
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📤 사진 업로드</div>', unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "여행 사진을 선택하세요 (여러 장 동시 선택 가능)",
    type=["jpg", "jpeg", "png", "heic"],
    accept_multiple_files=True,
    key="file_uploader",
    help="JPEG / PNG / HEIC · 다중 선택 가능"
)

col_btn, col_info = st.columns([1, 4])
with col_btn:
    process_btn = st.button("🚀 분석 시작", disabled=not uploaded_files, use_container_width=True)
with col_info:
    if uploaded_files:
        st.markdown(
            f'<div style="color:#6B7280;padding-top:0.6rem;">'
            f'{len(uploaded_files)}장 선택됨 — 분석 시작을 누르면 블러 감지, 중복 제거, 앨범 분류가 실행됩니다'
            f'</div>', unsafe_allow_html=True
        )

if process_btn and uploaded_files:
    with st.spinner(f"📊 {len(uploaded_files)}장 분석 중... (ML 처리로 1~2분 소요될 수 있습니다)"):
        try:
            result = api_client.upload_photos(uploaded_files)
            st.session_state.upload_result = result
            st.session_state.uploaded = True
            st.session_state.albums = api_client.get_albums()
            st.session_state.selected_album_id = None
            st.session_state.photos = None
            st.session_state.photos_lookup = None
            st.session_state.report = None
            st.session_state.post_result = None
            st.session_state.last_error = None
        except Exception as e:
            err = str(e)
            st.session_state.last_error = f"업로드 실패: {err}"
            st.markdown(f'<div class="status-err">❌ 업로드 실패: {err}</div>',
                        unsafe_allow_html=True)

if st.session_state.uploaded and st.session_state.upload_result:
    res = st.session_state.upload_result
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-icon">🖼️</div>'
            f'<div class="metric-value">{res["uploaded_count"]}</div>'
            f'<div class="metric-label">업로드된 사진</div></div>', unsafe_allow_html=True)
    with c2:
        ac = len(st.session_state.albums) if st.session_state.albums else "—"
        st.markdown(
            f'<div class="metric-card"><div class="metric-icon">🗂️</div>'
            f'<div class="metric-value">{ac}</div>'
            f'<div class="metric-label">분류된 앨범</div></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# [P0] 2. 앨범 선택 UI
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.uploaded and st.session_state.albums:
    st.markdown("---")
    st.markdown('<div class="section-header">🗂️ 앨범 선택</div>', unsafe_allow_html=True)

    albums = st.session_state.albums

    if len(albums) == 1:
        album = albums[0]
        label = utils.format_album_label(album)
        st.markdown(f'<div class="status-ok">🗂️ 앨범 자동 선택: <strong>{label}</strong></div>',
                    unsafe_allow_html=True)
        if st.session_state.selected_album_id != album["album_id"]:
            st.session_state.selected_album_id = album["album_id"]
            st.session_state.photos = None
            st.session_state.photos_lookup = None
            st.session_state.report = None
            st.session_state.post_result = None
    else:
        labels = [utils.format_album_label(a) for a in albums]
        album_ids = [a["album_id"] for a in albums]
        current_idx = album_ids.index(st.session_state.selected_album_id) \
            if st.session_state.selected_album_id in album_ids else 0

        selected_label = st.selectbox("여행 앨범을 선택하세요", options=labels,
                                      index=current_idx, key="album_selectbox")
        new_album_id = album_ids[labels.index(selected_label)]
        if new_album_id != st.session_state.selected_album_id:
            st.session_state.selected_album_id = new_album_id
            st.session_state.photos = None
            st.session_state.photos_lookup = None
            st.session_state.report = None
            st.session_state.post_result = None

    # 사진 목록 로드 (session_state 캐시)
    if st.session_state.selected_album_id and st.session_state.photos is None:
        with st.spinner("사진 목록 불러오는 중..."):
            try:
                photos_list = api_client.get_photos(st.session_state.selected_album_id)
                st.session_state.photos = photos_list
                # 리포트 썸네일용 lookup dict 빌드
                st.session_state.photos_lookup = {p["photo_id"]: p for p in photos_list}
                st.session_state.last_error = None
            except Exception as e:
                err = str(e)
                st.session_state.last_error = f"사진 목록 조회 실패: {err}"
                st.markdown(f'<div class="status-err">❌ 사진 목록 조회 실패: {err}</div>',
                            unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# [P0] 3. 베스트컷 랭킹 화면
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.photos is not None:
    st.markdown("---")
    st.markdown('<div class="section-header">🏆 베스트컷 랭킹</div>', unsafe_allow_html=True)

    photos = st.session_state.photos
    person_photos = utils.sort_photos_by_score(utils.filter_by_category(photos, "person"))
    general_photos = utils.sort_photos_by_score(utils.filter_by_category(photos, "general"))

    tab_person, tab_general = st.tabs([
        f"👤 인물 ({len(person_photos)}장)",
        f"🏞️ 일반 ({len(general_photos)}장)"
    ])

    with tab_person:
        _render_gallery(person_photos, session_key="person")

    with tab_general:
        _render_gallery(general_photos, session_key="general")


# ══════════════════════════════════════════════════════════════════════════════
# [P1] 4. 리포트 카드 UI
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.selected_album_id:
    st.markdown("---")
    st.markdown('<div class="section-header">📊 여행 리포트</div>', unsafe_allow_html=True)

    if st.session_state.report is None:
        with st.spinner("리포트 집계 중..."):
            try:
                st.session_state.report = api_client.get_report(st.session_state.selected_album_id)
                st.session_state.last_error = None
            except Exception as e:
                err = str(e)
                st.session_state.last_error = f"리포트 조회 실패: {err}"
                st.markdown(f'<div class="status-err">❌ 리포트 조회 실패: {err}</div>',
                            unsafe_allow_html=True)

    report = st.session_state.report
    photos_lookup = st.session_state.photos_lookup or {}

    if report:
        # ── 통계 숫자 카드 5개 ────────────────────────────────────────────────
        st.markdown("#### 📈 통계 요약")
        mc = st.columns(5)
        stats = [
            ("🖼️", report.get("total_photos", 0), "총 사진"),
            ("🤳", report.get("selfie_count", 0), "셀카"),
            ("🍽️", report.get("food_count", 0), "음식"),
            ("🏞️", report.get("landscape_count", 0), "풍경"),
            ("💨", report.get("blurry_count", 0), "흔들린 사진"),
        ]
        for col, (icon, val, lbl) in zip(mc, stats):
            with col:
                st.markdown(
                    f'<div class="metric-card"><div class="metric-icon">{icon}</div>'
                    f'<div class="metric-value">{val}</div>'
                    f'<div class="metric-label">{lbl}</div></div>', unsafe_allow_html=True)

        st.markdown("")

        # ── 하이라이트 (사진이 있는 항목은 전부 카드+썸네일을 대칭 1:1로 배치) ──
        # 사람 요청: 리포트 카드에서 버튼으로 원본 사진을 볼 수 있어야 하고,
        # 레이아웃 비대칭도 정리할 것 — best_shot/best_group_photo/most_retaken/
        # most_photographed_person을 전부 같은 [1, 1] 카드+썸네일 패턴으로 통일.
        st.markdown("#### 🌟 하이라이트")

        highlight_cards = []  # (icon, title, value_html, sub, photo_id, thumb_label)

        best = report.get("best_shot")
        if best:
            highlight_cards.append((
                "🏆", "베스트컷", best.get("aesthetic_score", "—"), "미학 점수",
                best["photo_id"], "베스트컷",
            ))

        group = report.get("best_group_photo")
        if group:
            highlight_cards.append((
                "👥", "최고 단체사진", group.get("aesthetic_score", "—"),
                f'{group.get("face_count", 0)}명 등장', group["photo_id"], "단체사진",
            ))

        retaken = report.get("most_retaken")
        if retaken:
            highlight_cards.append((
                "🔁", "최다 재촬영", retaken.get("count", 0), "장 같은 장면",
                retaken.get("representative_photo_id"), "재촬영 대표컷",
            ))

        person_star = report.get("most_photographed_person")
        if person_star:
            highlight_cards.append((
                "🙋", "최다 등장 인물", person_star.get("count", 0), "장 등장",
                person_star.get("representative_photo_id"), "대표 사진",
            ))

        for icon, title, value, sub, photo_id, thumb_label in highlight_cards:
            c1, c2 = st.columns([1, 1])
            with c1:
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-icon">{icon}</div>'
                    f'<div style="color:var(--accent);font-weight:600;">{title}</div>'
                    f'<div class="metric-value">{value}</div>'
                    f'<div class="metric-label">{sub}</div>'
                    f'</div>', unsafe_allow_html=True)
            with c2:
                if photo_id:
                    _render_photo_thumb(photo_id, thumb_label, photos_lookup)
                else:
                    st.caption("사진 정보 없음")
            st.markdown("")

        # 사진이 없는 통계 카드 (눈 감은 사진 등)
        eyes_closed = report.get("eyes_closed_count", 0)
        other_cols = st.columns(2)
        with other_cols[0]:
            st.markdown(
                f'<div class="metric-card"><div class="metric-icon">😑</div>'
                f'<div style="color:var(--accent);font-weight:600;font-size:0.9rem;">눈 감은 사진</div>'
                f'<div class="metric-value" style="font-size:1.7rem;">{eyes_closed}</div>'
                f'<div class="metric-label">장</div></div>', unsafe_allow_html=True)

        # top_location (null이면 숨김, photo_id 없어 썸네일은 불가)
        loc = report.get("top_location")
        if loc:
            with other_cols[1]:
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-icon">📍</div>'
                    f'<div style="color:var(--accent);font-weight:600;">{loc["place"]}</div>'
                    f'<div class="metric-label">가장 많이 찍은 장소 · {loc["count"]}장</div>'
                    f'</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# [P1] 5. 후기 글 생성 UI
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.report and st.session_state.selected_album_id:
    st.markdown("---")
    st.markdown('<div class="section-header">✍️ 여행 후기 글 생성</div>', unsafe_allow_html=True)

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
        photos = st.session_state.photos or []
        sorted_all = utils.sort_photos_by_score(photos)
        best_ids = [p["photo_id"] for p in sorted_all[:3]]

        with st.spinner("AI가 후기 글을 작성 중입니다 (Claude API 호출)..."):
            try:
                result = api_client.generate_post(style_choice, report, best_ids)
                st.session_state.post_result = result.get("text", "")
                st.session_state.last_error = None
            except Exception as e:
                err = str(e)
                st.session_state.last_error = f"후기 글 생성 실패: {err}"
                st.markdown(f'<div class="status-err">❌ 후기 글 생성 실패: {err}</div>',
                            unsafe_allow_html=True)

    # 생성된 결과 표시 (session_state에 저장 → 재실행 시 유지)
    if st.session_state.post_result:
        st.markdown('<div class="status-ok">✅ AI 후기 글 생성 완료</div>', unsafe_allow_html=True)
        # CONTRACT.md: st.code(text, language=None) — 내장 복사 아이콘 활용
        st.code(st.session_state.post_result, language=None)


# ── 푸터 ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<div style="text-align:center;color:#9CA3AF;font-size:0.78rem;padding:0.8rem;">'
    '여행 베스트컷 AI · Streamlit :8501 · FastAPI :8001'
    '</div>',
    unsafe_allow_html=True
)
