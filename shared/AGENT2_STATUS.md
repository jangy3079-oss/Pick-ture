# AGENT2_STATUS.md (Agent 2가 작성, Agent 1은 읽기 전용)

## 마지막 갱신: 반복 1+2 (전체 완료, 백엔드 연결 대기 중)

## 완료
- [P0] 업로드 UI — 완료. `st.file_uploader(accept_multiple_files=True)`, `st.spinner`, `st.progress` 스타일 피드백. 업로드 결과 `st.session_state`에 저장.
- [P0] 앨범 선택 UI — 완료. `GET /api/albums` 호출(목업 폴백), 1개이면 자동 선택/2개 이상이면 `st.selectbox`. 국가=null이면 날짜 범위만 라벨에 표시. `selected_album_id` session_state 저장.
- [P0] 베스트컷 랭킹 화면 — 완료. `GET /api/photos?album_id=...` (목업 폴백), `st.tabs(["인물", "일반"])` 탭 분리, `aesthetic_score` 내림차순, `is_blurry=True`는 맨 뒤, `st.columns(3)` 갤러리.
- [P1] 리포트 카드 UI — 완료. `GET /api/report?album_id=...` (목업 폴백), `st.metric`/`st.columns` 카드형. `top_location: null`이면 해당 카드 렌더링 안 함.
- [P1] 후기 글 생성 UI — 완료. 앨범 기준 `POST /api/generate-post` 호출, `st.radio`로 blog/instagram 선택, `st.code(text, language=None)` 출력.

## 진행 중 / 실패
- 없음

## 발견한 계약 불일치
- 없음

## 유닛테스트 결과
- **32개 테스트 전체 통과** (pytest, 0.29s)
- `test_utils.py` — 29개: format_album_label, sort_photos_by_score, filter_by_category, get_score_badge, has_top_location, get_portrait_status, get_dominant_tag, 앨범 선택 분기
- `test_smoke.py` — 3개: AppTest 스모크 (초기화, 업로드 섹션, 분석 버튼)

## 파일 목록 (worktree-agent2-frontend/)
- `app.py` — 메인 Streamlit 앱 (사이드바+데모모드 포함)
- `api_client.py` — FastAPI 백엔드(포트 8000) 호출 + 목업 폴백
- `mock_data.py` — CONTRACT.md 스키마 기반 목업 데이터 (null 케이스 포함)
- `utils.py` — 순수 함수 (정렬/필터/라벨 포맷 등)
- `test_utils.py` — 유닛테스트 (29개)
- `test_smoke.py` — AppTest 스모크 테스트 (3개)
- `requirements.txt` — streamlit>=1.45, requests>=2.34

## 실행 방법
```bash
cd worktree-agent2-frontend
streamlit run app.py  # http://localhost:8501
```

## 가정
- 가정: shared/ 및 worktree-agent2-frontend/ 디렉토리가 없어서 직접 생성함 (CONTRACT.md 1절 구조 참고)
- 가정: TASKS_FOR_AGENT2.md가 없으므로 PLAN_AGENT2.md의 기본 작업 목록을 따름
- 가정: 백엔드 API가 미구현(라우터 없음)이므로 CONTRACT.md 스키마 기반 목업 데이터로 화면 구현 후 백엔드 준비되면 자동 전환됨
- 가정: is_blurry=True인 사진은 정렬 시 맨 뒤로 배치 (흔들린 사진은 추천 안 함)
- 가정: 베스트컷 랭킹 갤러리는 3컬럼(st.columns(3))으로 배치
- 가정: 후기 글 생성 시 현재 선택된 앨범의 사진 중 상위 3장을 best_shot_ids로 전달

## Agent 1에게 요청
- `GET /api/photos?album_id=xxx` 엔드포인트 구현 시 단일 사진 조회(`/photo/{id}`)가 아니라 앨범 전체 목록을 배열로 반환하는 형태로 구현 필요 (CONTRACT.md 3장 "GET /api/photos" 섹션 참고)
- 백엔드 구현 완료 시 `TASKS_FOR_AGENT2.md`에 API 준비 완료 사실 기재 바람
