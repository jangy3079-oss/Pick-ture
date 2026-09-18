# PLAN.md — Agent 2 (실행자 겸 프론트엔드/결과화면, Streamlit)

역할: Agent 1의 지시(`/shared/TASKS_FOR_AGENT2.md`)를 그대로 따라 화면을 구현한다. **스스로 작업 우선순위를 정하지 않는다** — 상하관계상 우선순위 결정권은 Agent 1에게 있다. CONTRACT.md를 반드시 먼저 읽고 시작할 것.

**기술 스택: Streamlit(Python)으로 구현한다.** React/Vite 등 Node.js 기반 프레임워크는 쓰지 않는다(CONTRACT.md 0-1 참고). 백엔드(포트 8000, FastAPI)는 `requests`로 호출한다. 앱 실행은 `streamlit run app.py`, 기본 포트 8501.

**Streamlit 특유의 주의사항**: Streamlit은 위젯 상호작용이 있을 때마다 스크립트 전체가 재실행된다. 업로드한 사진이나 백엔드 응답, 선택된 앨범을 매 상호작용마다 다시 처리/재호출하지 않도록, 처리 결과와 선택 상태는 `st.session_state`에 저장해서 재사용한다 — 안 그러면 버튼 하나 누를 때마다 전체 파이프라인이 다시 돌아서 시간을 낭비한다.

**질문 금지**: 판단이 필요한 모호한 상황(정확한 문구, 색상, 레이아웃 디테일 등)에서 사람에게 묻지 않는다(CONTRACT.md 6-2). 합리적으로 가정하고 즉시 진행한 뒤, `/shared/AGENT2_STATUS.md`에 "가정: ..." 한 줄로 기록한다.

## 반복(iteration) 루틴

매 반복 시작 시 아래 순서를 지킨다:

1. `/shared/TASKS_FOR_AGENT2.md`를 다시 읽는다(캐시된 이전 내용 말고 최신본 — Agent 1이 매 반복 갱신할 수 있음).
2. 거기 적힌 우선순위 순서대로만 작업한다. 목록에 없는 작업은 임의로 시작하지 않는다.
3. API가 아직 미구현이라고 적혀 있으면, CONTRACT.md의 스키마대로 목업 데이터를 만들어 화면 작업을 먼저 진행한다(막혀서 대기하지 않는다).
4. 작업 결과(완료/실패, 사용한 API, 발견한 계약 불일치)를 `/shared/AGENT2_STATUS.md`에 기록한다. **이 기록(플랜 갱신) 전에도 "Plan 수정 시 파일 읽기 범위" 절차를 따른다.**
5. 작업 결과를 커밋한다(`git stash` 금지).

## Plan 수정 시 파일 읽기 범위

`/shared/AGENT2_STATUS.md`를 갱신하거나 안티그래비티 플랜/자기 작업 목록을 수정할 때는 자기 worktree 전체를 다시 훑지 않는다. 아래 세 가지만 특정해서 읽는다:

1. **수정 대상 파일**: 지금 만들거나 고치는 그 컴포넌트/화면 파일(또는 AGENT2_STATUS.md 자체)
2. **그 파일이 직접 의존하는 파일**: 호출하는 API 스키마(CONTRACT.md 해당 섹션만), import하는 컴포넌트
3. **그 파일에 직접 의존하는 파일**: 이 컴포넌트를 사용하는 상위 화면 — grep으로 의존 대상만 먼저 특정하고, 찾아진 파일만 연다

관련 없는 화면이나 Agent 1의 worktree 전체를 미리 읽지 않는다.

## 기본 작업 목록 (Agent 1이 갱신하지 않았을 경우의 기본값 — 항상 `TASKS_FOR_AGENT2.md` 최신본이 우선)

1. **[P0] 업로드 UI**: `st.file_uploader(accept_multiple_files=True)`로 여행 사진 다중 업로드, 업로드/처리 진행 상태는 `st.progress` 또는 `st.spinner`로 표시. 처리 결과는 `st.session_state`에 저장해서 재실행마다 다시 업로드/재처리하지 않게 한다
2. **[P0] 앨범 선택 UI**: `GET /api/albums` 호출, 앨범이 2개 이상이면 `st.selectbox`로 선택(국가명·날짜 범위·사진 수를 라벨에 함께 표시, 예: "독일 (8/2~8/4, 214장)"), 1개뿐이면 선택 UI 없이 자동 선택. `country`가 `null`인 앨범은 국가명 대신 날짜 범위만 라벨에 표시. 선택된 `album_id`를 `st.session_state`에 저장해서 이후 모든 화면이 이 값을 기준으로 동작하게 한다
3. **[P0] 베스트컷 랭킹 화면**: 선택된 `album_id`로 필터링된 `GET /api/photos/{photo_id}` 응답 기반, `st.tabs(["인물", "일반"])`로 `category`(person/general) 분리, `aesthetic_score` 내림차순 정렬해서 `st.columns` 갤러리로 표시
4. **[P1] 리포트 카드 UI**: `GET /api/report?album_id=<선택된 앨범>` 스키마 그대로 `st.metric`/`st.columns` 카드형 UI — `total_photos`, `selfie_count`/`food_count`/`landscape_count`, `blurry_count`, `eyes_closed_count`, `most_retaken`, `best_shot`, `best_group_photo`. `top_location`이 `null`이면 해당 카드는 렌더링하지 않는다(빈 카드로 보여주지 말 것)
5. **[P1] 후기 글 생성 UI**: 선택된 앨범 기준으로 `POST /api/generate-post` 호출(해당 앨범의 report를 그대로 전달), `st.radio`나 `st.toggle`로 블로그/인스타 스타일 선택, 결과는 `st.code(text, language=None)`로 표시 — Streamlit이 기본 제공하는 복사 아이콘을 그대로 활용하고 별도 복사 버튼은 구현하지 않는다

## 탈출 조건

- 각 작업 항목은 **최대 4회** 시도. 4회 실패 시 "실패: [이유]"를 `/shared/AGENT2_STATUS.md`에 남기고, `TASKS_FOR_AGENT2.md`의 다음 우선순위 작업으로 자동 이동한다. 멈춰서 기다리지 않는다.
- API가 CONTRACT.md 스키마와 다르게 응답하면, 코드를 임의로 우회하지 말고 `/shared/AGENT2_STATUS.md`에 불일치 내용을 정확히 기록한 뒤 목업으로 전환해서 계속 진행한다(Agent 1이 다음 반복에 확인).

## 검증 범위

- Streamlit UI 자체를 렌더링 테스트하기보다, API 응답을 화면에 맞게 가공하는 순수 함수(정렬, 필터링, null 처리 등)를 유닛테스트로 검증한다 — 더 빠르고 안정적이다
- `top_location: null` 같은 optional 필드 처리가 깨지지 않는지가 핵심 — 목업 데이터 작성 시 `null` 케이스도 반드시 포함해서 테스트
- 앨범이 1개일 때와 2개 이상일 때 둘 다 목업으로 만들어서, 선택 UI가 조건부로 잘 숨겨지는지 확인
- 여유가 있으면 `streamlit.testing.v1.AppTest`로 앱이 에러 없이 뜨는지 정도의 스모크 테스트만 추가

## `/shared/AGENT2_STATUS.md` 기록 형식 (매 반복 갱신)

```markdown
# AGENT2_STATUS.md (Agent 2가 작성, Agent 1은 읽기 전용)

## 마지막 갱신: [반복 번호]
## 완료
- [P0] 업로드 UI — 완료, 정상 동작 확인

## 진행 중 / 실패
- [P1] 리포트 카드 UI — 목업으로 화면 완성, GET /api/report 실제 연동 대기 중

## 발견한 계약 불일치
- (없으면 "없음"으로 명시)
```
