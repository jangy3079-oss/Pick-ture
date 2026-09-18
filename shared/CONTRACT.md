# CONTRACT.md — 여행 사진 베스트컷 서비스

## 0. 에이전트 관계 (상하관계 고정)

- **Agent 1 = 지휘자(오케스트레이터) 겸 백엔드/파이프라인 담당**
- **Agent 2 = 실행자 겸 프론트엔드/결과화면 담당**

Agent 1은 자기 파트(백엔드) 구현과 동시에, Agent 2가 할 작업을 `/shared/TASKS_FOR_AGENT2.md`에 지시하고 그 산출물을 검증할 책임을 진다. Agent 2는 매 반복(iteration) 시작 시 `/shared/TASKS_FOR_AGENT2.md`를 다시 읽고, 거기 적힌 우선순위대로만 작업한다. 두 에이전트는 프로세스가 분리되어 있어 실시간 대화가 불가능하므로, **지휘는 대화가 아니라 파일로만** 이루어진다.

- Agent 1 → Agent 2 지시: `/shared/TASKS_FOR_AGENT2.md` (Agent 1만 쓰기, Agent 2는 읽기 전용)
- Agent 2 → Agent 1 보고: `/shared/AGENT2_STATUS.md` (Agent 2만 쓰기, Agent 1은 읽기 전용)
- **서로의 worktree 코드를 직접 수정하는 것은 금지.** Agent 1은 Agent 2의 worktree를 읽어서 계약 위반 여부만 확인하고, 문제가 있으면 코드를 직접 고치지 말고 `TASKS_FOR_AGENT2.md`에 수정 지시를 추가한다.

## 0-1. 기술 스택 (확정)

- **Agent 1 (백엔드)**: Python + FastAPI
- **Agent 2 (프론트엔드)**: Python + **Streamlit** — Node.js/React는 쓰지 않는다. 무개입 2시간 루프에서 npm 설치 실패 같은 별도 생태계 리스크를 없애기 위한 선택. Agent 2는 FastAPI 서버(포트 8000)를 `requests`로 서버사이드 호출해서 결과를 렌더링한다(CORS 설정 불필요).
- 프로젝트 전체가 Python 하나로 통일되므로, 두 에이전트 모두 `pip`만 쓰면 된다 — Node/npm은 이 프로젝트에 없다.

## 1. 폴더 구조

```
repo/
├── worktree-agent1-backend/     # Agent 1 전용, 백엔드/파이프라인
├── worktree-agent2-frontend/    # Agent 2 전용, 프론트엔드 (Streamlit)
└── shared/
    ├── CONTRACT.md              # 이 파일 (양쪽 다 읽기 전용, 수정 시 재합의 필요)
    ├── TASKS_FOR_AGENT2.md      # Agent 1 → Agent 2 지시
    └── AGENT2_STATUS.md         # Agent 2 → Agent 1 보고
```

각 에이전트는 **자기 worktree + `/shared`만** 참조한다. 상대 worktree 전체를 읽지 않는다(검증 목적의 최소 열람 제외).

## 2. 포트 배정

| 서비스 | 포트 |
| --- | --- |
| 백엔드 API (Agent 1) | 8000 |
| Streamlit 앱 (Agent 2) | 8501 (기본값) |

## 3. API 응답 스키마 (Agent 1이 정의, Agent 2가 그대로 소비)

### POST /api/upload

요청: `multipart/form-data`, 필드명 `photos`(다중 파일).

응답:
```json
{
  "uploaded_count": 12,
  "photo_ids": ["string", "string"]
}
```

이 엔드포인트 안에서 전처리(블러/중복)와 3-1 앨범 분류까지 **동기적으로** 실행하고 끝난 뒤 응답한다(비동기 작업 큐/상태 폴링은 이번 스코프에 없음 — 사진 수가 적은 데모 규모에서는 동기 처리로 충분하다는 가정). 응답이 오면 그 즉시 `GET /api/albums`, `GET /api/photos`로 결과를 조회할 수 있다.

### GET /api/photos

`GET /api/photos?album_id=xxx` — 해당 앨범의 전체 사진 목록. 아래 각 원소는 `GET /api/photos/{photo_id}` 하나와 동일한 스키마다(배열로 묶여 나올 뿐). Agent 2는 화면을 그릴 때 이 목록 엔드포인트로 한 번에 가져온다 — `photo_id`를 미리 알고 있어야만 조회 가능한 `GET /api/photos/{photo_id}`만으로는 목록 화면을 만들 수 없다.

### GET /api/photos/{photo_id}

```json
{
  "photo_id": "string",
  "filename": "string",
  "album_id": "string",
  "image_url": "string",
  "is_blurry": false,
  "duplicate_group_id": "string | null",
  "face_count": 1,
  "category": "person",
  "aesthetic_score": 7.8,
  "portrait_bonus": {
    "eyes_open": true,
    "smiling": true,
    "adjustment": 0.5
  },
  "zero_shot_tags": {
    "selfie": 0.82,
    "food": 0.05,
    "landscape": 0.10
  }
}
```

`category`는 `"person"` 또는 `"general"` 둘 중 하나. `portrait_bonus`는 `category`가 `"person"`일 때만 존재. `album_id`는 3-1의 앨범 자동 분류 결과. **`image_url`은 실제 이미지 바이트를 내려주는 정적 경로**(예: `/api/photos/{photo_id}/image`, `Content-Type: image/jpeg`) — Agent 2는 `st.image(image_url)` 또는 `requests`로 받아온 바이트를 그대로 렌더링한다. 이 필드가 없으면 화면에 사진 자체를 못 띄운다.

### GET /api/albums

```json
[
  {
    "album_id": "string",
    "country": "string | null",
    "date_range": { "start": "2026-08-01", "end": "2026-08-04" },
    "photo_count": 214,
    "cover_photo_id": "string"
  }
]
```

업로드된 사진들을 3-1 로직으로 분류한 앨범 목록. `country`는 국가별 재분류가 가능했을 때만 채워지고(예: `"Germany"`), GPS가 전혀 없는 배치라면 `null`. 프론트는 이걸로 앨범 선택 UI를 만든다. 앨범이 1개뿐이면(단일 여행, 단일 국가) 리스트 길이가 1 — 이 경우 프론트가 선택 UI 없이 자동으로 그 앨범을 쓴다.

### GET /api/report

```json
{
  "total_photos": 842,
  "selfie_count": 107,
  "food_count": 83,
  "landscape_count": 214,
  "blurry_count": 62,
  "eyes_closed_count": 19,
  "most_retaken": {
    "duplicate_group_id": "string",
    "count": 13,
    "representative_photo_id": "string"
  },
  "best_shot": { "photo_id": "string", "aesthetic_score": 9.2 },
  "best_group_photo": { "photo_id": "string", "aesthetic_score": 8.5, "face_count": 5 },
  "top_location": null
}
```

`top_location`은 EXIF GPS 데이터가 있을 때만 값이 채워짐(`{ "place": "string", "count": 74 }`), 없으면 `null` — 프론트는 null일 때 해당 카드를 숨긴다. `place`는 3-1 국가별 재분류 과정에서 이미 계산해둔 도시 단위 지명(reverse-geocode의 `city`)을 그대로 재사용한다 — 별도 계산 불필요.

**쿼리 파라미터 `album_id` 필수**: `GET /api/report?album_id=xxx`. 이 엔드포인트는 항상 특정 앨범(여행) 하나를 기준으로 집계한다 — 여러 여행이 섞인 채로 집계하지 않는다. `album_id`가 없거나 존재하지 않으면 400 에러를 반환한다(조용히 전체를 합쳐서 계산하지 않는다).

### POST /api/generate-post

요청:
```json
{ "style": "blog", "report": { /* GET /api/report 응답 그대로 */ }, "best_shot_ids": ["string"] }
```
`style`은 `"blog"` 또는 `"instagram"`. `report`는 특정 앨범의 `GET /api/report` 응답을 그대로 넣는다 — 여러 앨범을 섞어서 넣지 않는다(한 번에 한 여행 후기만 생성).

응답:
```json
{ "text": "string" }
```

## 3-1. 앨범 자동 분류 (여러 여행지 동시 업로드 대응)

**2단계 클러스터링**: 먼저 시간으로 큰 "여행" 단위를 나누고, 그 안에서 GPS 기반 국가별로 다시 나눈다. 예: 한국-독일-오스트리아-한국을 한 번에 다녀온 여행이면, 1단계에서 하나의 시간 덩어리로 묶이고, 2단계에서 국가별로 재분류되어 한국/독일/오스트리아 앨범 3개가 만들어진다(같은 여행 안에서 두 번 걸친 한국은 하나로 합쳐짐).

**1단계 — 시간 간격 클러스터링**: EXIF `DateTimeOriginal` 기준으로 사진을 촬영 시각순 정렬 후, 연속된 두 사진 사이 간격이 임계값(기본 48시간)을 넘으면 새 "여행" 경계로 본다. 이건 서로 다른 시기에 갔던 같은 나라 여행(예: 작년 일본 여행과 올해 일본 여행)을 하나로 합치지 않기 위한 안전장치 — 국가만으로 나누면 이 둘이 잘못 합쳐진다.

**2단계 — 국가별 재분류**: 1단계로 나눈 각 "여행" 덩어리 안에서, GPS 좌표를 오프라인 역지오코딩(`reverse-geocode` 패키지, PyPI `reverse-geocode`)으로 국가 코드/도시명으로 변환하고 국가별로 앨범을 나눈다. 네트워크 호출 없이 로컬 데이터로 동작하므로 방 안에서도 안전하다.

**GPS 없는 사진**: 촬영 시각 기준으로 가장 가까운, GPS가 있는 사진의 국가를 그대로 물려받는다(nearest-neighbor 보간). 배치 전체에 GPS가 하나도 없으면 2단계를 건너뛰고 1단계 결과만 앨범으로 쓴다 — 이 경우 `country`는 전부 `null`(억지로 나누지 않는다).

**임계값(48시간)은 팀 실제 사진으로 캘리브레이션 권장** — 너무 짧으면 한 여행이 여러 앨범으로 쪼개지고, 너무 길면 서로 다른 여행이 하나로 합쳐진다.

업로드 직후(전처리 단계)에 한 번 실행되어 각 사진에 `album_id`를 부여하고, `GET /api/albums`로 결과를 조회할 수 있게 한다.

## 4. 네이밍 규칙

- JSON 필드는 **snake_case** 고정 (camelCase 섞지 않는다)
- 사진 식별자는 항상 `photo_id` (파일명이 아니라 서버가 발급한 id)

## 5. 컨텍스트/토큰 규칙

```markdown
- 각 에이전트는 자기 담당 worktree + /shared 폴더만 참조
- 검증은 통합 테스트가 아니라 해당 모듈 유닛테스트로 한정
- 최대 반복 횟수: 작업당 4회. 초과 시 멈추지 말고 실패 기록 남기고 다음 작업으로 자동 이동
- Agent 1은 /shared/AGENT2_STATUS.md를, Agent 2는 /shared/TASKS_FOR_AGENT2.md를 매 반복 시작 시 다시 읽고 최신 상태를 기준으로 작업한다 (이전에 읽은 캐시된 내용으로 판단하지 않는다)
- 파일을 수정하거나 플랜(TASKS_FOR_AGENT2.md 포함)을 갱신하기 전에는, 수정 대상 파일 + 그 파일이 직접 의존하는 파일 + 그 파일에 직접 의존하는 파일만 특정해서 읽는다. 관련 없는 파일이나 worktree 전체를 미리 훑지 않는다
```

## 6-1. 환경 변수 / 외부 의존성

**Claude API 키 (후기 글 생성용, `POST /api/generate-post`)**

- `ANTHROPIC_API_KEY` 환경변수로 주입한다. 코드에 하드코딩 금지, `.env`에 두고 `.gitignore`에 포함.
- **루프룸에 들어가기 전에 미리 발급해서 환경변수로 설정해둘 것.** API 키 발급(console.anthropic.com 로그인 후 생성)은 사람만 할 수 있는 작업이라, 방 안에서 키가 없다는 걸 발견하면 루프가 스스로 해결할 수 없다 — 이 상태로 방에 들어가면 개입(-1점)이 사실상 확정된다.
- 방에 들어간 뒤 키가 없거나 만료된 게 확인되면: Agent 1은 `POST /api/generate-post` 작업을 이번 사이클 범위에서 제외하고 실패로 기록한 뒤 다음 작업으로 넘어간다(탈출조건과 동일 원리, 사람을 부르지 않는다).

**Agent 1 패키지 (사전 설치 필수)**

```bash
pip install mediapipe simple-aesthetics-predictor open-clip-torch imagededup opencv-python fastapi uvicorn anthropic python-dotenv pillow reverse-geocode
```

| 역할 | 패키지 |
| --- | --- |
| 얼굴 검출 (인물/일반 분기) | mediapipe |
| 인물 표정 보정 (눈감음/미소) | mediapipe (Face Landmarker blendshape) |
| 미학 점수 + 카테고리 제로샷 분류 | simple-aesthetics-predictor + open-clip-torch |
| 블러 컷 감지 | opencv-python (Laplacian variance, 모델 아님) |
| 중복/유사 사진 그룹핑 | imagededup |
| 앨범 1단계: EXIF 시각 읽기 | pillow (모델 아님) |
| 앨범 2단계: GPS→국가/도시 오프라인 변환 | reverse-geocode (모델 아님, 로컬 데이터 기반) |
| API 서버 | fastapi + uvicorn |
| Claude API 호출 (후기 글 생성) | anthropic |
| `.env` 환경변수 로딩 | python-dotenv |

사전학습 가중치는 최초 실행 시 자동 다운로드되므로, 방에 들어가기 전 한 번 실행해서 가중치를 미리 받아두는 것을 권장(네트워크 지연으로 반복 횟수를 낭비하지 않기 위함).

**Agent 2 패키지 (사전 설치 필수)**

```bash
pip install streamlit requests
```

Agent 2는 0-1에서 확정한 대로 Streamlit이라 Node/npm이 필요 없다. 백엔드(포트 8000)는 `requests`로 호출한다. ML/비전 패키지는 Agent 2에 설치하지 않는다 — 그건 전부 Agent 1 담당이고, Agent 2는 API 응답 JSON만 받아서 화면에 그린다.

## 6-2. 질문 대신 가정하고 진행

두 에이전트 모두 방 안에서는 사람에게 질문하거나 응답을 기다리며 멈추지 않는다. 무개입이 원칙이므로, 질문을 던지는 순간 사실상 루프가 멈춘 것과 같다.

- CONTRACT.md/PLAN.md에 이미 명시된 내용(API 스키마, 우선순위, 폴더 규칙 등)은 그대로 따른다 — 이건 "가정"의 대상이 아니라 이미 정해진 계약이다.
- 명시되지 않은 세부사항(정확한 문구, 색상, 엣지 케이스 처리 방식 등)이 모호하면, 가장 합리적인 기본값으로 스스로 판단해서 즉시 진행한다.
- 그 판단은 반드시 기록한다 — 커밋 메시지나 `AGENT1_STATUS.md`/`AGENT2_STATUS.md`에 "가정: [무엇을 왜 이렇게 정했는지]" 한 줄로 남긴다. 방이 열렸을 때 사람이 이 기록을 보고 필요하면 고친다.
- 판단이 서비스 핵심 동작을 바꿀 만큼 중대하고 잘못되면 되돌리기 어렵다고 느껴져도, 질문 대신 가장 보수적인 선택(기존 계약 유지, 해당 기능 범위 축소·스킵)을 하고 기록만 남긴다. 판단은 사람이 다음 사이클에 재조정한다.

## 6-3. 하지 말 것

- 질문하거나 사람의 응답을 기다리며 멈추는 것 금지 (6-2 참고 — 가정하고 진행, 기록만 남긴다)
- 서로의 worktree에 직접 쓰기 금지 (지시는 `TASKS_FOR_AGENT2.md`로만)
- `git stash` 금지 — 커밋으로 상태 남길 것
- 테스트 `skip` 처리 금지
- 실패했다고 멈춰서 대기하지 말 것 — 반드시 기록 후 다음 작업으로 이동
- CONTRACT.md의 스키마를 임의로 바꾸지 말 것 — 바꿔야 한다면 Agent 1이 여기(CONTRACT.md)를 직접 갱신하고 그 사실을 `TASKS_FOR_AGENT2.md`에 명시
