# TASKS_FOR_AGENT2.md (Agent 1이 작성/갱신, Agent 2는 읽기 전용)

## 지금 확정된 API — 전부 구현 완료, 실사진으로 실동작 검증됨
**Base URL: `http://localhost:8001`** (8000 아님 — 아래 "중요 알림" 참고)

- `POST /api/upload` — multipart, 필드명 `photos` (다중 파일)
- `GET /api/albums`
- `GET /api/photos?album_id=xxx` — 배열 반환
- `GET /api/photos/{photo_id}`
- `GET /api/photos/{photo_id}/image` — 실제 이미지 바이트(Content-Type: image/jpeg 등), `st.image()`에 그대로 사용 가능
- `GET /api/report?album_id=xxx` — album_id 없으면 400
- `POST /api/generate-post` — `{style, report, best_shot_ids}` 요청, `{text}` 응답. 실제 Claude API 호출로 한국어 블로그 후기 생성 확인됨(style=instagram도 지원)

전부 CONTRACT.md 3장 스키마 그대로(snake_case, 필드명 동일). 지금부터 목업 대신 실제 백엔드를 호출해도 됩니다.

## 중요 알림
- **🚨 백엔드 포트 변경: 8000 → 8001.** 이 머신에서 8000번은 무관한 다른 IDE(Antigravity)의 웹뷰어가 이미 점유 중이고 자동으로 계속 재기동되어 확보 불가능함을 확인했습니다(`/problem.md` 3-0/3-1절, `shared/CONTRACT.md` 2장에도 반영함). **api_client.py의 base URL을 `http://localhost:8001`로 바꿔주세요.**
- **ANTHROPIC_MODEL 오타 아님**: `.env`의 `ANTHROPIC_MODEL=claude-sonnet-5`는 정정할 필요 없습니다. `claude-sonnet-5`는 실제 유효한 최신 모델 ID입니다(Claude 5 패밀리). AGENT2_STATUS.md에 남긴 의심은 오탐이니 수정하지 마세요. 자세한 내용은 `/problem.md` 3절 참고.
- **git 저장소가 초기화되었습니다** (`/Users/mac/Loopcoding`가 이제 git repo root). 지금부터는 `git add`/`git commit`으로 결과를 남겨주세요 (`git stash` 금지, CONTRACT.md 6-3).
- 폴더 구조(`shared/`, `worktree-agent1-backend/`, `worktree-agent2-frontend/`)는 Agent 1과 Agent 2가 독립적으로 동일하게 CONTRACT.md 1절대로 만들어서 충돌 없이 수렴했습니다. 계속 이 구조를 유지해주세요.
- 백엔드 서버가 지금 `localhost:8001`에서 계속 실행 중입니다(제 세션에서 백그라운드로 띄워둠). 재시작이 필요하면 `cd worktree-agent1-backend && <repo venv>/bin/uvicorn app.main:app --port 8001`.

## 우선순위 (목업 → 실 API 전환)
1. [P0] 업로드 UI — `POST /api/upload`로 전환 가능
2. [P0] 앨범 선택 UI — `GET /api/albums`로 전환 가능 (앨범 1개면 자동 선택 로직 유지)
3. [P0] 베스트컷 랭킹 화면 — `GET /api/photos?album_id=...`로 전환 가능 (album_id로 필터링된 배열이 바로 옴, photo_id 미리 몰라도 됨)
4. [P1] 리포트 카드 UI — `GET /api/report?album_id=...`로 전환 가능
5. [P1] 후기 글 생성 UI — `POST /api/generate-post`로 전환 가능

## 검증 참고 (Agent 1이 실사진 20장으로 확인한 실제 응답 예시)
- 앨범: 1개, country="Czech Republic", photo_count=20
- 리포트: total_photos=20, selfie_count=11, food_count=4, landscape_count=5, blurry_count=5, eyes_closed_count=0, best_group_photo=null(그룹샷 없음), top_location={"place":"Malá Strana","count":10}
- best_group_photo나 most_retaken이 null일 수 있으니 프론트에서 null 처리(카드 숨김) 꼭 확인해주세요 — CONTRACT.md에 이미 명시된 내용입니다.

## 스키마 추가 (반복 2, P2 — 선택적으로 반영하면 됨, 필수 아님)
`GET /api/report` 응답에 `most_photographed_person` 필드가 추가되었습니다 (CONTRACT.md에도 반영됨):
```json
"most_photographed_person": { "count": 5, "representative_photo_id": "string" }
```
`person` 카테고리 사진이 2장 미만이거나 동일 인물 반복 등장이 없으면 `null` — 다른 nullable 카드(top_location 등)와 동일하게 null이면 카드 숨기면 됩니다. 리포트 카드 UI가 이미 완료되어 있다면, 시간 될 때 이 카드 하나만 추가해주세요(필수는 아님, P2).

## 재확인 완료 (반복 3) — 아래 3개는 사용 가능 상태 재검증됨
- `POST /api/upload` — multipart 필드명 `photos`, 응답 `{uploaded_count, photo_ids}` 정확히 일치. 유닛테스트 + 실사진 20장 업로드로 재확인.
- `GET /api/photos?album_id=xxx` — **배열** 반환(단일 조회 아님), 각 원소는 `GET /api/photos/{photo_id}`와 동일 스키마. 유닛테스트(`test_list_photos_by_album_returns_array`) + 실사진으로 재확인.
- `image_url` 필드 + `GET /api/photos/{photo_id}/image` 정적 서빙 — dataset/의 실제 JPEG 바이트를 그대로 내려주는지 바이트 단위로 비교하는 유닛테스트 추가(`test_get_photo_image_serves_real_bytes`), Content-Type: image/jpeg 확인. `st.image(image_url)`에 그대로 써도 됩니다.
- 전체 파이프라인(업로드→앨범분류→점수화→리포트→후기생성) 재기동 후 처음부터 끝까지 에러 없이 통과 확인(2026-09-18, base URL 8001).

⚠️ **테스트 시 참고**: 백엔드는 인메모리 저장소라 서버를 재시작하지 않고 같은 사진 세트를 두 번 업로드하면 이전 배치와 합쳐져서 총 장수가 누적됩니다(예: 20장을 두 번 올리면 40장으로 집계) — 버그 아니라 의도된 동작(데모 스코프, CONTRACT.md에 다중 배치 병합 규칙이 없어서 Agent 1이 "매 업로드마다 스토어 전체로 재클러스터링"으로 가정함, `shared/AGENT1_STATUS.md` 참고). 프론트에서 반복 테스트할 때 이 점 감안해주세요 — 정확한 수치가 필요하면 백엔드를 재시작하고 한 번만 업로드하세요.

## ⚠️ problem.md 동시쓰기 주의
방금 `/problem.md`가 통째로 0바이트가 되어있는 걸 발견하고 마지막 커밋에서 복구했습니다 — 두 에이전트가 같은 파일에 거의 동시에 쓰다가 레이스 컨디션이 난 것으로 추정됩니다(상세: problem.md 3-1절). **앞으로 problem.md에 쓸 때는 파일 전체를 새로 쓰기(overwrite)보다 기존 내용에 append하는 방식을 써주세요** — 전체 덮어쓰기 중 타이밍이 겹치면 서로의 내용을 지울 수 있습니다. 저도 이제부터 그렇게 하고, 커밋도 더 자주 하겠습니다.

## 변경 이력
- 반복 1: 최초 작성. git 초기화 알림 추가.
- 반복 2: 백엔드 P0+P1 전체 완료. 포트 8001로 확정, 모든 엔드포인트 사용 가능 상태로 전환. P2 `most_photographed_person` 필드 추가.
- 반복 3: 업로드/앨범목록/이미지서빙 3개 엔드포인트 유닛테스트로 재검증 + 전체 파이프라인 재기동 스모크 테스트 통과. 반복 업로드 시 누적되는 동작 방식 안내 추가.
