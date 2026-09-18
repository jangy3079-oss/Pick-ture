"""
app.py — 여행 사진 베스트컷 서비스 (Agent 2, Streamlit)
실행: streamlit run app.py
포트: 8501 (기본값)

CONTRACT.md 준수 사항:
- 백엔드(포트 8001) FastAPI를 requests로 서버사이드 호출
- 목업 데이터 없음 — 실제 백엔드만 사용
- 모든 처리 결과/선택 상태는 st.session_state에 저장 (재실행 시 재처리 방지)
- best_group_photo, most_retaken, most_photographed_person 등 nullable 필드는 null이면 카드 숨김
"""

import streamlit as st
import requests as req
from io import BytesIO
import sys
import os

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

.stApp {
    background: linear-gradient(135deg, #0f0c29 0%, #1a1040 40%, #0d1b3e 100%);
    min-height: 100vh;
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
    text-align: center;
}
.hero-subtitle {
    color: #94a3b8;
    font-size: 1.1rem;
    margin-top: 0.5rem;
    text-align: center;
}

.metric-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 14px;
    padding: 1.25rem 1rem;
    text-align: center;
    transition: background 0.2s;
}
.metric-card:hover { background: rgba(255,255,255,0.08); }
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
.metric-icon { font-size: 1.5rem; margin-bottom: 0.4rem; }

.section-header {
    font-size: 1.4rem;
    font-weight: 600;
    color: #e2e8f0;
    margin: 2rem 0 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
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

.status-ok {
    background: rgba(52,211,153,0.1);
    border: 1px solid rgba(52,211,153,0.3);
    border-radius: 10px;
    padding: 0.75rem 1rem;
    color: #34d399;
    font-size: 0.9rem;
    margin: 0.5rem 0;
}
.status-warn {
    background: rgba(251,191,36,0.1);
    border: 1px solid rgba(251,191,36,0.3);
    border-radius: 10px;
    padding: 0.75rem 1rem;
    color: #fbbf24;
    font-size: 0.9rem;
    margin: 0.5rem 0;
}
.status-err {
    background: rgba(239,68,68,0.1);
    border: 1px solid rgba(239,68,68,0.3);
    border-radius: 10px;
    padding: 0.75rem 1rem;
    color: #f87171;
    font-size: 0.9rem;
    margin: 0.5rem 0;
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
.stButton > button:hover { opacity: 0.85 !important; }

div[data-testid="stFileUploaderDropzone"] {
    background: rgba(167,139,250,0.07) !important;
    border: 2px dashed rgba(167,139,250,0.4) !important;
    border-radius: 12px !important;
}
</style>
""", unsafe_allow_html=True)


# ── 헬퍼: 이미지 바이트 로드 ─────────────────────────────────────────────────
def _load_image(image_url: str):
    """image_url에서 이미지 바이트 로드. 실패 시 None 반환."""
    try:
        r = req.get(image_url, timeout=8)
        if r.status_code == 200:
            return BytesIO(r.content)
    except Exception:
        pass
    return None


# ── 헬퍼: 사진 카드 렌더링 ───────────────────────────────────────────────────
def _render_photo_card(photo: dict, rank: int | None = None):
    score = photo.get("aesthetic_score", 0)
    is_blurry = photo.get("is_blurry", False)

    rank_str = f"#{rank} " if rank else ""
    badge = utils.get_score_badge(score)
    blurry_tag = ' <span class="blurry-badge">흔들림</span>' if is_blurry else ""

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
        f'<span style="color:#94a3b8;font-size:0.8rem;font-weight:600;">{rank_str}</span>'
        f'<span class="score-badge">{badge} {utils.format_score(score)}</span>'
        f'{blurry_tag}</div>',
        unsafe_allow_html=True
    )

    img_url = photo.get("image_url", "")
    img_bytes = _load_image(img_url) if img_url else None
    if img_bytes:
        st.image(img_bytes, use_container_width=True)
    else:
        st.markdown(
            '<div style="background:linear-gradient(135deg,#1e1b4b,#312e81);'
            'border-radius:10px;height:180px;display:flex;align-items:center;'
            'justify-content:center;color:#6366f1;font-size:2rem;">📷</div>',
            unsafe_allow_html=True
        )

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
            '<div style="color:#94a3b8;font-size:0.75rem;margin-top:4px;">'
            + " · ".join(meta_parts) + "</div>",
            unsafe_allow_html=True
        )


# ── 세션 상태 초기화 ─────────────────────────────────────────────────────────
defaults = {
    "uploaded": False,
    "upload_result": None,
    "albums": None,
    "selected_album_id": None,
    "photos": None,
    "report": None,
    "backend_alive": None,
    "last_error": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# 백엔드 연결 상태 (세션당 1회 체크, 사이드바 재시도 버튼으로 갱신 가능)
if st.session_state.backend_alive is None:
    st.session_state.backend_alive = api_client.is_backend_alive()


# ── 사이드바 ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📊 서비스 정보")
    st.markdown("---")

    alive = st.session_state.backend_alive
    color = "#34d399" if alive else "#f87171"
    icon = "🟢" if alive else "🔴"
    label = "연결됨 (:8001)" if alive else "연결 안 됨 (:8001)"
    st.markdown(
        f'<div style="padding:0.5rem;background:rgba(255,255,255,0.05);'
        f'border-radius:8px;margin-bottom:0.5rem;">'
        f'<span>{icon} 백엔드: </span>'
        f'<span style="color:{color};font-weight:600;">{label}</span>'
        f'</div>',
        unsafe_allow_html=True
    )
    if st.button("🔄 연결 재시도", key="retry_backend", use_container_width=True):
        st.session_state.backend_alive = api_client.is_backend_alive()
        st.rerun()

    st.markdown("---")
    st.markdown("### ℹ️ 실행 정보")
    st.markdown("- **포트**: 8501 (Streamlit)")
    st.markdown("- **백엔드**: FastAPI :8001")
    st.markdown("- **Agent**: Agent 2 (프론트엔드)")

    if st.session_state.last_error:
        st.markdown("---")
        st.markdown("### ⚠️ 최근 오류")
        st.error(st.session_state.last_error)


# ── 헤더 ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding: 2.5rem 1rem 1.5rem; text-align: center;">
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

st.markdown(
    '<div class="status-ok">✅ 백엔드 서버 연결됨 (http://localhost:8001)</div>',
    unsafe_allow_html=True
)

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# [P0] Task 1: 업로드 UI
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📤 사진 업로드</div>', unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "여행 사진을 선택하세요 (여러 장 동시 선택 가능)",
    type=["jpg", "jpeg", "png", "heic"],
    accept_multiple_files=True,
    key="file_uploader",
    help="JPEG, PNG, HEIC 형식 지원 · 다중 선택 가능"
)

col_btn, col_info = st.columns([1, 4])
with col_btn:
    process_btn = st.button(
        "🚀 분석 시작",
        disabled=not uploaded_files,
        use_container_width=True,
    )
with col_info:
    if uploaded_files:
        st.markdown(
            f'<div style="color:#94a3b8;padding-top:0.6rem;">'
            f'{len(uploaded_files)}장 선택됨 — 분석 시작을 누르면 블러 감지, 중복 제거, 앨범 분류가 실행됩니다'
            f'</div>',
            unsafe_allow_html=True
        )

if process_btn and uploaded_files:
    with st.spinner(f"📊 {len(uploaded_files)}장 사진 분석 중... (ML 처리 시간이 걸릴 수 있습니다)"):
        try:
            result = api_client.upload_photos(uploaded_files)
            st.session_state.upload_result = result
            st.session_state.uploaded = True
            # 업로드 완료 → 앨범 목록 즉시 로드
            st.session_state.albums = api_client.get_albums()
            st.session_state.selected_album_id = None
            st.session_state.photos = None
            st.session_state.report = None
            st.session_state.last_error = None
        except Exception as e:
            err = str(e)
            st.session_state.last_error = f"업로드 실패: {err}"
            st.markdown(f'<div class="status-err">❌ 업로드 실패: {err}</div>', unsafe_allow_html=True)

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
        album = albums[0]
        label = utils.format_album_label(album)
        st.markdown(
            f'<div class="status-ok">🗂️ 앨범 자동 선택: <strong>{label}</strong></div>',
            unsafe_allow_html=True
        )
        if st.session_state.selected_album_id != album["album_id"]:
            st.session_state.selected_album_id = album["album_id"]
            st.session_state.photos = None
            st.session_state.report = None
    else:
        labels = [utils.format_album_label(a) for a in albums]
        album_ids = [a["album_id"] for a in albums]

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
            st.session_state.photos = None
            st.session_state.report = None

    # 선택된 앨범의 사진 로드 (session_state 캐시)
    if st.session_state.selected_album_id and st.session_state.photos is None:
        with st.spinner("사진 목록 불러오는 중..."):
            try:
                st.session_state.photos = api_client.get_photos(st.session_state.selected_album_id)
                st.session_state.last_error = None
            except Exception as e:
                err = str(e)
                st.session_state.last_error = f"사진 목록 조회 실패: {err}"
                st.markdown(f'<div class="status-err">❌ 사진 목록 조회 실패: {err}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# [P0] Task 3: 베스트컷 랭킹 화면
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

    COLS = 3

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
    st.markdown('<div class="section-header">📊 여행 리포트</div>', unsafe_allow_html=True)

    if st.session_state.report is None:
        with st.spinner("리포트 집계 중..."):
            try:
                st.session_state.report = api_client.get_report(st.session_state.selected_album_id)
                st.session_state.last_error = None
            except Exception as e:
                err = str(e)
                st.session_state.last_error = f"리포트 조회 실패: {err}"
                st.markdown(f'<div class="status-err">❌ 리포트 조회 실패: {err}</div>', unsafe_allow_html=True)

    report = st.session_state.report

    if report:
        # ── 상단 숫자 지표 5개 ──────────────────────────────────────────────
        st.markdown("#### 📈 통계 요약")
        mc1, mc2, mc3, mc4, mc5 = st.columns(5)
        metrics = [
            (mc1, "🖼️", report.get("total_photos", 0), "총 사진"),
            (mc2, "🤳", report.get("selfie_count", 0), "셀카"),
            (mc3, "🍽️", report.get("food_count", 0), "음식"),
            (mc4, "🏞️", report.get("landscape_count", 0), "풍경"),
            (mc5, "💨", report.get("blurry_count", 0), "흔들린 사진"),
        ]
        for col, icon, val, lbl in metrics:
            with col:
                st.markdown(
                    f'<div class="metric-card"><div class="metric-icon">{icon}</div>'
                    f'<div class="metric-value">{val}</div>'
                    f'<div class="metric-label">{lbl}</div></div>',
                    unsafe_allow_html=True
                )

        st.markdown("")

        # ── 하이라이트 카드 (nullable 필드는 null이면 숨김) ─────────────────
        st.markdown("#### 🌟 하이라이트")

        highlight_cards = []

        # 베스트컷 (best_shot은 항상 있음)
        best = report.get("best_shot")
        if best:
            highlight_cards.append(("🏆", "#a78bfa", "베스트컷",
                                    str(best.get("aesthetic_score", "—")), "미학 점수"))

        # 최고 단체사진 (null이면 숨김)
        group = report.get("best_group_photo")
        if group:
            highlight_cards.append(("👥", "#60a5fa", "최고 단체사진",
                                    str(group.get("aesthetic_score", "—")),
                                    f'{group.get("face_count", 0)}명 등장'))

        # 눈 감은 사진 (항상 표시)
        eyes_closed = report.get("eyes_closed_count", 0)
        highlight_cards.append(("😑", "#f472b6", "눈 감은 사진", str(eyes_closed), "장"))

        # 최다 재촬영 (null이면 숨김)
        retaken = report.get("most_retaken")
        if retaken:
            highlight_cards.append(("🔁", "#fb923c", "최다 재촬영",
                                    str(retaken.get("count", 0)), "장 같은 장면"))

        # 가장 많이 찍힌 인물 (P2 신규 필드, null이면 숨김)
        person = report.get("most_photographed_person")
        if person:
            highlight_cards.append(("🙋", "#34d399", "최다 등장 인물",
                                    str(person.get("count", 0)), "장 등장"))

        # 카드를 행 단위로 렌더링 (3열)
        hcols_per_row = 3
        for row_start in range(0, len(highlight_cards), hcols_per_row):
            batch = highlight_cards[row_start:row_start + hcols_per_row]
            cols = st.columns(hcols_per_row)
            for i, (icon, color, title, val, sub) in enumerate(batch):
                with cols[i]:
                    st.markdown(
                        f'<div class="metric-card">'
                        f'<div class="metric-icon">{icon}</div>'
                        f'<div style="color:{color};font-weight:600;font-size:0.95rem;">{title}</div>'
                        f'<div class="metric-value" style="font-size:1.8rem;">{val}</div>'
                        f'<div class="metric-label">{sub}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

        # top_location: null이면 카드 렌더링하지 않음 (CONTRACT.md 3장)
        loc = report.get("top_location")
        if loc:
            st.markdown("")
            st.markdown(
                f'<div class="metric-card" style="max-width:320px;">'
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
                st.markdown('<div class="status-ok">✅ AI 후기 글 생성 완료</div>', unsafe_allow_html=True)
                # CONTRACT.md: st.code(text, language=None) 으로 표시 (내장 복사 아이콘 활용)
                st.code(result["text"], language=None)
            except Exception as e:
                err = str(e)
                st.session_state.last_error = f"후기 글 생성 실패: {err}"
                st.markdown(f'<div class="status-err">❌ 후기 글 생성 실패: {err}</div>', unsafe_allow_html=True)


# ── 푸터 ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<div style="text-align:center;color:#475569;font-size:0.8rem;padding:1rem;">'
    '여행 베스트컷 AI · Agent 2 (Streamlit :8501) ↔ Agent 1 (FastAPI :8001)'
    '</div>',
    unsafe_allow_html=True
)
