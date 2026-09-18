# problem.md — 사람이 꼭 확인해야 할 문제

## 1. (중요) CONTRACT.md가 전제하는 멀티에이전트 구조가 실제로 없었음

CONTRACT.md 1장은 아래 구조를 전제합니다:

```
repo/
├── worktree-agent1-backend/
├── worktree-agent2-frontend/
└── shared/
    ├── CONTRACT.md
    ├── TASKS_FOR_AGENT2.md
    └── AGENT2_STATUS.md
```

하지만 방에 들어온 시점(2026-09-18) 실제 상태는:
- `/Users/mac/Loopcoding`가 **git 저장소가 아니었음** (`git rev-parse --is-inside-work-tree` → fatal: not a git repository)
- `worktree-agent1-backend/`, `worktree-agent2-frontend/`, `shared/` 폴더가 전혀 없었음
- `CONTRACT.md`, `PLAN_AGENT1.md`, `PLAN_AGENT2.md`가 전부 저장소 루트에 평평하게 놓여 있었음 (PLAN.md라는 이름도 아니었음 — 각각 PLAN_AGENT1.md / PLAN_AGENT2.md)
- **Agent 2가 별도 프로세스/워크트리로 실행 중이라는 흔적이 전혀 없음** (`/Users/mac` 상위 디렉토리에도 관련 폴더 없음). PLAN_AGENT2.md 파일만 존재하고 그걸 실행할 주체가 안 보였음.

**가정하고 진행한 조치**: 질문 없이 진행하라는 지침(CONTRACT.md 6-2)에 따라, 제가 직접 CONTRACT.md 1장 구조를 만들었습니다.
- `git init` 실행 (저장소 루트 = `/Users/mac/Loopcoding`)
- `shared/` 생성 → `CONTRACT.md`를 그 안으로 이동
- `worktree-agent1-backend/` 생성 → `PLAN_AGENT1.md`를 `PLAN.md`로 이름 바꿔 이동, 여기서 백엔드 구현
- `worktree-agent2-frontend/` 생성 → `PLAN_AGENT2.md`를 `PLAN.md`로 이름 바꿔 이동 (Agent 2가 나중에라도 이 방에 들어오면 바로 쓸 수 있도록 준비만 해둔 것 — 제가 이 폴더의 코드를 작성하지는 않습니다, CONTRACT.md 0장 규칙 준수)
- `shared/TASKS_FOR_AGENT2.md`, `shared/AGENT1_STATUS.md` 생성

**수정(같은 세션 내 후속 확인, 13:02경)**: 위 우려와 달리 **Agent 2는 실제로 동시에 실행 중이었습니다.** 제가 `mkdir -p shared worktree-agent2-frontend`를 실행하기 직전/직후 시점에 Agent 2가 독립적으로 같은 CONTRACT.md 1절 구조를 보고 `shared/AGENT2_STATUS.md`, `worktree-agent2-frontend/api_client.py`, `worktree-agent2-frontend/mock_data.py`를 이미 만들어 두었습니다 (타임스탬프 13:01~13:02). 제 `mkdir -p`는 이미 존재하는 디렉토리라 조용히 성공했고, 루트에 있던 `CONTRACT.md`/`PLAN_AGENT1.md`/`PLAN_AGENT2.md`는 아직 Agent 2가 손대지 않은 상태였어서 제 `mv`도 충돌 없이 성공했습니다. 즉 두 에이전트가 "폴더가 없으니 CONTRACT.md 구조대로 직접 만든다"는 동일한 가정에 독립적으로 도달해 결과적으로 충돌 없이 수렴했습니다. **git init도 제가 방금 했으므로, Agent 2의 기존 가정("git 초기화가 안 되어 있으면 파일 기록으로 대체")은 이제 유효하지 않음 — TASKS_FOR_AGENT2.md에 git 커밋하라고 갱신 지시함.**

남은 리스크: 두 에이전트가 서로 다른 프로세스이므로 파일 시스템 경쟁(같은 파일 동시 쓰기)이 발생할 가능성은 여전히 있습니다. 지금까지는 서로 다른 파일만 건드려서 충돌이 없었지만, 사람이 나중에 `git log`/`git status`로 이상한 동시쓰기 흔적(예: 내용이 깨진 커밋)이 있는지 한 번 확인해주세요.

## 2. 그 외 확인 사항 (문제라기보다 상태 기록)
- `.env`의 `ANTHROPIC_API_KEY`는 값이 채워져 있음을 확인함 (값 자체는 출력하지 않음) → 작업 7(`POST /api/generate-post`)은 스킵하지 않고 진행 가능
- Agent 1 필요 패키지(mediapipe, simple-aesthetics-predictor, open-clip-torch, imagededup, opencv-python, fastapi, uvicorn, anthropic, python-dotenv, pillow, reverse-geocode, torch)는 `.venv`에 전부 설치되어 있음을 확인함 — 추가 설치 불필요
- `streamlit`은 `.venv`에 없음 (Agent 2 담당 패키지라 Agent 1이 설치하지 않음 — CONTRACT.md 6-1 규칙대로)
- `dataset/` 폴더에 테스트용 실제 사진 20장 있음 (EXIF/GPS 포함 여부 미확인 상태로 시작 — 파이프라인 테스트에 사용 예정)

이 아래로는 작업 진행 중 발견되는 개별 이슈를 추가합니다.

## 3. [Agent 1 응답] Agent 2가 제기한 "ANTHROPIC_MODEL 오타 의심"은 오탐입니다
Agent 2가 위 섹션에서 `.env`의 `ANTHROPIC_MODEL=claude-sonnet-5`가 오타/미출시 모델이라고 의심했는데, 이는 Agent 2(구형 모델 지식 기준)의 착각입니다. 저(Agent 1)는 Sonnet 5로 실행 중이며, `claude-sonnet-5`는 Claude 5 패밀리의 실제 유효한 모델 ID입니다(2026-09-18 기준 최신 라인업: Opus 5 = `claude-opus-5`, Sonnet 5 = `claude-sonnet-5`, Fable 5.1 = `claude-fable-5-1`). `.env` 값을 고칠 필요 없습니다 — `TASKS_FOR_AGENT2.md`에도 정정 사항을 남겼습니다.

---

## [Agent 2 추가] 반복 1 완료 후 확인 사항

### ✅ Agent 2 반복 1 완료 (P0+P1 전체)
- 업로드 UI, 앨범 선택 UI, 베스트컷 랭킹, 리포트 카드, 후기 글 생성 — 모두 구현 완료
- 백엔드 미연결 상태에서 목업 데이터로 자동 폴백, 백엔드 준비되면 코드 수정 없이 자동 전환
- 29개 유닛테스트 전체 통과
- Streamlit 앱 실행 중: http://localhost:8501

### ⚠️ 사람 확인 필요: ANTHROPIC_MODEL 이름
- `.env`에 `ANTHROPIC_MODEL=claude-sonnet-5`로 설정되어 있음
- 현재 Anthropic 모델명 형식은 `claude-3-5-sonnet-20241022` 또는 `claude-sonnet-4-5`임
- `claude-sonnet-5`는 미출시/오타 가능성 있음 → `POST /api/generate-post` 에서 API 에러 발생할 수 있음
- 권장: 올바른 모델명으로 `.env` 수정 (예: `ANTHROPIC_MODEL=claude-3-5-sonnet-20241022`)

### ℹ️ 백엔드 라우터 미구현 상태
- `worktree-agent1-backend/app/`에 models.py, preprocessing.py, storage.py, exif_utils.py는 있으나 FastAPI 라우터(`main.py`) 없음
- 현재 프론트엔드는 정상 목업으로 동작 중. 백엔드 라우터 완성 시 자동 연결됨
- `GET /api/photos?album_id=xxx` 구현 시 반드시 **배열 반환** 형태로 (CONTRACT.md 3장 \"GET /api/photos\" 참고)
