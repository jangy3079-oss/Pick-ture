# TASKS_FOR_AGENT2.md (Agent 1이 작성/갱신, Agent 2는 읽기 전용)

## 지금 확정된 API
- (아직 구현된 엔드포인트 없음 — 백엔드 작업 시작 단계)
- `GET /api/albums`, `GET /api/photos/{photo_id}` 구현 완료 시 즉시 이 파일을 갱신하고 "변경 이력"에 기록함

## 중요 알림
- **git 저장소가 초기화되었습니다** (`/Users/mac/Loopcoding`가 이제 git repo root). AGENT2_STATUS.md에 남긴 "git 초기화 안 되어 있으면 파일 기록으로 대체"라는 가정은 더 이상 유효하지 않습니다 — 지금부터는 `git add`/`git commit`으로 결과를 남겨주세요 (`git stash` 금지, CONTRACT.md 6-3).
- 폴더 구조(`shared/`, `worktree-agent1-backend/`, `worktree-agent2-frontend/`)는 Agent 1과 Agent 2가 독립적으로 동일하게 CONTRACT.md 1절대로 만들어서 충돌 없이 수렴했습니다. 계속 이 구조를 유지해주세요.

## 우선순위
1. [P0] 업로드 UI (다중 파일 선택) — 계속 진행
2. [P0] 앨범 선택 UI — GET /api/albums 호출, 앨범이 2개 이상이면 선택 UI, 1개면 자동 선택 — 목업으로 먼저 진행, 백엔드 완료되면 재공지
3. [P0] 베스트컷 랭킹 화면 — 선택된 album_id로 필터링된 GET /api/photos/{photo_id} 응답을 aesthetic_score 기준 정렬 표시 — 목업으로 먼저 진행
4. [P1] 리포트 카드 UI — GET /api/report?album_id=... 는 아직 미구현, 목업 데이터로 먼저 화면만 만들어둘 것
5. [P1] 후기 글 생성 UI — POST /api/generate-post 완료되면 다시 공지

## 백엔드 진행 상황 (참고용)
- 포트 8000에서 FastAPI 서버 구현 시작. 아직 실행 가능한 엔드포인트 없음 — 목업 데이터 계속 사용할 것.

## 변경 이력
- 반복 1: 최초 작성. git 초기화 알림 추가.
