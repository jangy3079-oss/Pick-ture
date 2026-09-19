# 여행 사진 베스트컷 AI

여행 사진을 업로드하면 흔들린 사진과 중복 사진을 걸러내고, 여행지/국가별로 자동 앨범을 나누고, 사진마다 미학 점수를 매겨 베스트컷을 추려주고, 통계 리포트와 함께 블로그/인스타그램용 여행 후기 글까지 AI가 초안을 써주는 서비스입니다.

이 저장소는 동시에 두 가지를 담고 있습니다.

1. **서비스 자체**: FastAPI 백엔드(ML 파이프라인) + Streamlit 프론트엔드로 이루어진 실제 동작하는 앱
2. **멀티 에이전트 협업 실험**: 두 개의 Claude Code 에이전트가 서로 대화 없이, 오직 파일(`shared/`)만으로 지휘·보고·문제공유를 하며 이 서비스를 병렬로 만든 기록

아래에서 아이디어, 사용한 오픈소스 ML/DL 모델, API 계약, 에이전트 협업 구조, 각 에이전트의 작업 계획, 문제 공유 워크플로우를 순서대로 설명합니다.

---

## 1. 아이디어

여행에서 돌아오면 보통 수백 장의 사진이 쌓입니다. 그중 실제로 SNS에 올리거나 앨범에 남길 만한 "베스트컷"은 소수이고, 나머지는 흔들렸거나, 같은 장면을 여러 번 찍었거나, 정리가 안 된 채로 방치됩니다. 이 프로젝트는 그 정리 과정을 자동화하는 것이 목표입니다.

- **업로드 한 번으로 끝**: 사진 여러 장을 한꺼번에 올리면, 업로드 응답이 오는 시점에 이미 전처리·분류·점수화가 전부 끝나 있습니다(비동기 폴링 없음).
- **여행지별로 알아서 나뉘는 앨범**: 한 번에 여러 나라를 다녀온 사진을 섞어 올려도(예: 한국→독일→오스트리아→한국), 시간 간격과 GPS를 함께 봐서 "여행" 단위와 "국가" 단위로 스스로 앨범을 나눕니다.
- **취향이 아니라 기준으로 고르는 베스트컷**: 미학 점수(aesthetic score), 얼굴/표정, 블러 여부, 중복 여부를 근거로 순위를 매기지 사람이 일일이 고르지 않습니다.
- **숫자로 보는 여행 리포트**: 총 사진 수, 셀카/음식/풍경 비율, 흔들린 사진 수, 가장 많이 다시 찍은 장면, 가장 많이 등장한 인물, 가장 많이 방문한 장소 같은 통계를 자동 집계합니다.
- **후기 글 초안까지**: 위 리포트와 베스트컷을 근거로 Claude가 블로그 또는 인스타그램 스타일의 여행 후기 글 초안을 씁니다.

---

## 2. 아이디어별로 사용한 오픈소스 ML/DL 모델

| 하고 싶었던 것 | 사용한 오픈소스 모델/라이브러리 | 어떻게 썼는지 |
| --- | --- | --- |
| 사진에 사람이 몇 명, 어디 있는지 찾기 | **[MediaPipe](https://github.com/google-ai-edge/mediapipe) FaceDetector** (`blaze_face_short_range.tflite`) | 각 사진에서 얼굴 개수(`face_count`)를 세서 `person`/`general` 카테고리를 나누는 기준으로 사용 |
| 인물 사진의 눈감음/미소 보정 | **MediaPipe FaceLandmarker** (blendshape, `face_landmarker.task`) | 얼굴 랜드마크의 `eyeBlinkLeft/Right`, `mouthSmileLeft/Right` 블렌드셰입 점수로 눈뜸/미소 여부를 판정해 `portrait_bonus`(점수 가감) 계산 |
| "잘 찍은 사진"이라는 애매한 기준을 점수로 만들기 | **[simple-aesthetics-predictor](https://github.com/shunk031/simple-aesthetics-predictor)** + HuggingFace `transformers` CLIP, 체크포인트 [`shunk031/aesthetics-predictor-v2-sac-logos-ava1-l14-linearMSE`](https://huggingface.co/shunk031/aesthetics-predictor-v2-sac-logos-ava1-l14-linearMSE) | SAC/LogoIQA/AVA 데이터셋으로 학습된 선형 회귀 헤드를 CLIP ViT-L/14 임베딩 위에 얹은 모델. 사진 한 장을 넣으면 미학 점수(`aesthetic_score`) 하나가 나옴 — 베스트컷 랭킹의 핵심 지표 |
| 사진을 셀카/음식/풍경으로 자동 분류 | **[open_clip](https://github.com/mlfoundations/open_clip)** `ViT-B-32-quickgelu` (OpenAI 사전학습 가중치) | "a selfie photo of a person" / "a photo of food" / "a landscape or scenery photo" 세 문장과 사진의 CLIP 임베딩 코사인 유사도를 비교하는 제로샷(zero-shot) 분류 — 별도 학습 데이터 없이 바로 사용 가능 |
| 같은 장면을 여러 번 찍은 사진 묶기 | **[imagededup](https://github.com/idealo/imagededup)** (PHash) | 지각적 해시(perceptual hash) 기반으로 서로 비슷한 사진을 그룹핑, `duplicate_group_id` 부여 → 리포트의 "최다 재촬영" 집계에 사용 |
| 같은 사람이 여러 장에 등장하는지 찾기 | **open_clip 이미지 임베딩 재사용** (전용 얼굴인식 모델 없음) | mediapipe로 얼굴을 잘라낸(crop) 뒤 CLIP 이미지 임베딩을 뽑아 코사인 유사도 기반 그리디 클러스터링 → "가장 많이 찍힌 사람"(`most_photographed_person`) 산출. 전용 얼굴인식 모델(FaceNet 등)이 아니라 이미 로드된 CLIP을 재사용한 근사치라 정확도는 완벽하지 않음(P2, nice-to-have로 문서화됨) |
| GPS 좌표를 나라/도시 이름으로 바꾸기 | **[reverse_geocode](https://pypi.org/project/reverse-geocode/)** (오프라인 로컬 데이터, 모델 아님) | 네트워크 호출 없이 GPS 좌표 → 국가/도시명 변환. "무개입 루프" 환경에서 네트워크 지연 리스크를 없애기 위해 오프라인 방식 선택 |
| 흔들린 사진 걸러내기 | **OpenCV** Laplacian 분산 (고전 컴퓨터비전 기법, 딥러닝 모델 아님) | 이미지의 라플라시안 필터 분산이 임계값보다 낮으면 블러로 판정 |
| 촬영 시각/GPS 읽기 | **Pillow (PIL)** EXIF 파싱 (모델 아님) | `DateTimeOriginal`, `GPSInfo` 태그를 읽어 앨범 자동 분류의 입력으로 사용 |
| 여행 후기 글 작성 | **Anthropic Claude API** (`claude-sonnet-5`) — ⚠️ 오픈소스 아님, 유료 API | 리포트 통계 + 베스트컷 개수를 프롬프트에 넣어 블로그/인스타그램 스타일 후기 텍스트 생성 |

> 얼굴 검출/랜드마커는 `mediapipe==0.10.35`로 버전이 고정되어 있습니다. `1.0.1`은 이 프로젝트를 만든 macOS arm64 환경에서 GPU(Metal) 헬퍼 초기화 시 무조건 크래시하는 알려진 버그([google-ai-edge/mediapipe#6356](https://github.com/google-ai-edge/mediapipe/issues/6356))가 있어 다운그레이드했습니다.

### CLIP 제로샷 분류의 한계와 보정

`selfie`/`food`/`landscape` 3가지 중 하나를 무조건 골라야 하는 제로샷 분류 특성상, 애매한 사진(예: 사람이 없는 건축물 사진)에서 CLIP이 약한 확신(예: 셀카 51% vs 풍경 38%)으로 오분류하는 경우가 실제로 발견되었습니다. 반대로 얼굴이 프레임에 가려진 진짜 거울 셀카는 mediapipe가 얼굴을 놓치는 경우도 있었습니다. 그래서 `face_count == 0`이면서 CLIP의 selfie 확신도가 낮을 때(<90%)만 selfie 후보에서 제외하고, 확신도가 매우 높으면(mediapipe가 놓쳤을 가능성이 크므로) CLIP의 판단을 그대로 신뢰하는 보정 규칙을 백엔드(`app/report.py`)와 프론트(`utils.py`) 양쪽에 동일하게 적용했습니다.

---

## 3. API 계약 (CONTRACT.md)

두 에이전트가 실시간 대화 없이 협업하기 위해, API 스키마·폴더 구조·포트·네이밍 규칙을 **하나의 계약 문서**(`shared/CONTRACT.md`)로 먼저 고정했습니다. 백엔드를 만드는 에이전트가 이 문서를 소유하고, 프론트를 만드는 에이전트는 이 문서만 보고 화면을 만듭니다.

### 3.1 엔드포인트 요약

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `POST` | `/api/upload` | 사진 다중 업로드. 전처리(블러/중복)+앨범 분류까지 동기 처리 후 `{uploaded_count, photo_ids}` 반환. 같은 파일(콘텐츠 해시 동일)을 재업로드하면 새로 만들지 않고 기존 `photo_id`를 재사용 |
| `GET` | `/api/albums` | 자동 분류된 앨범 목록 |
| `GET` | `/api/photos?album_id=xxx` | 앨범 내 전체 사진 배열 |
| `GET` | `/api/photos/{photo_id}` | 사진 한 장의 상세 정보 (아래 스키마) |
| `GET` | `/api/photos/{photo_id}/image` | 실제 이미지 바이트. `?size=thumb`를 붙이면 짧은 변 300px 썸네일(원본 대비 약 1/80 용량) |
| `GET` | `/api/report?album_id=xxx` | 앨범 하나 기준 통계 리포트 (`album_id` 필수, 없으면 400) |
| `POST` | `/api/generate-post` | 리포트+베스트컷 기반 여행 후기 글 생성 (`style`: `blog` \| `instagram`) |

### 3.2 사진 스키마 (`GET /api/photos/{photo_id}`)

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
  "portrait_bonus": { "eyes_open": true, "smiling": true, "adjustment": 0.5 },
  "zero_shot_tags": { "selfie": 0.82, "food": 0.05, "landscape": 0.10 }
}
```

### 3.3 리포트 스키마 (`GET /api/report`)

```json
{
  "total_photos": 842,
  "selfie_count": 107,
  "food_count": 83,
  "landscape_count": 214,
  "blurry_count": 62,
  "eyes_closed_count": 19,
  "most_retaken": { "duplicate_group_id": "string", "count": 13, "representative_photo_id": "string" },
  "best_shot": { "photo_id": "string", "aesthetic_score": 9.2 },
  "best_group_photo": { "photo_id": "string", "aesthetic_score": 8.5, "face_count": 5 },
  "top_location": { "place": "string", "count": 74 },
  "most_photographed_person": { "count": 5, "representative_photo_id": "string" }
}
```

nullable 필드(`best_group_photo`, `top_location`, `most_photographed_person`, `duplicate_group_id` 등)는 값이 없으면 `null` — 프론트는 이 경우 해당 카드를 숨깁니다.

### 3.4 앨범 자동 분류 (2단계 클러스터링)

1. **1단계 (시간)**: EXIF 촬영 시각 기준 정렬 후, 연속된 두 사진 사이 간격이 48시간을 넘으면 새 "여행"으로 분리 (같은 나라를 다른 시기에 두 번 간 경우를 하나로 합치지 않기 위한 안전장치)
2. **2단계 (국가)**: 각 "여행" 덩어리 안에서 GPS를 오프라인 역지오코딩해 국가별로 재분류. 한국→독일→오스트리아→한국처럼 한 여행 안에서 같은 나라를 두 번 들르면 하나로 합쳐짐
3. GPS 없는 사진은 촬영 시각이 가장 가까운, GPS 있는 사진의 국가를 물려받음. 배치 전체에 GPS가 없으면 2단계를 건너뛰고 `country: null`

### 3.5 네이밍/규칙

- JSON 필드는 **snake_case** 고정
- 사진 식별자는 항상 서버가 발급한 `photo_id` (파일명 아님)
- 백엔드는 CORS 미들웨어를 두지 않음 — 프론트(Streamlit)가 브라우저 `fetch`가 아니라 서버사이드 `requests`로 호출하기 때문

전체 원문은 [`shared/CONTRACT.md`](shared/CONTRACT.md)에 있습니다.

---

## 4. 병렬 에이전트 협업 구조

이 프로젝트는 **두 개의 Claude Code 에이전트**가 서로 다른 git worktree에서 동시에(사람 개입 없이 최대 2시간) 작업해서 만들어졌습니다.

```
repo/ (git 저장소 루트, 이 README가 있는 곳)
├── worktree-agent1-backend/     # Agent 1 전용 — 백엔드/ML 파이프라인 (FastAPI)
├── worktree-agent2-frontend/    # Agent 2 전용 — 프론트엔드 (Streamlit)
└── shared/                      # 두 에이전트가 함께 참조하는 계약/통신 파일
    ├── CONTRACT.md              # API 스키마, 폴더 구조, 규칙 (양쪽 다 읽기, 수정은 Agent 1만)
    ├── TASKS_FOR_AGENT2.md      # Agent 1 → Agent 2 지시 (Agent 1만 쓰기)
    ├── AGENT1_STATUS.md         # Agent 1의 진행 상황 기록
    └── AGENT2_STATUS.md         # Agent 2 → Agent 1 보고 (Agent 2만 쓰기)
```

### 4.1 상하관계

| | Agent 1 | Agent 2 |
| --- | --- | --- |
| 역할 | 지휘자(오케스트레이터) 겸 백엔드 담당 | 실행자 겸 프론트엔드 담당 |
| 담당 | FastAPI + ML 파이프라인 | Streamlit 화면 |
| 우선순위 결정권 | O (API 스키마를 정의하고 Agent 2에게 작업을 지시) | X (Agent 1의 지시를 그대로 따름) |
| 쓸 수 있는 파일 | `worktree-agent1-backend/` 전체, `shared/*` | `worktree-agent2-frontend/` 전체, `shared/AGENT2_STATUS.md`, `shared/problem.md` |
| 상대 worktree | 계약 위반 검증을 위해 **읽기만** 가능, 직접 수정 금지 | 동일 |

지휘는 대화가 아니라 **오직 파일**로만 이루어집니다 — 두 에이전트는 서로 다른 프로세스라 실시간으로 말을 주고받을 수 없기 때문입니다. Agent 1이 API를 하나 완성하면 `TASKS_FOR_AGENT2.md`를 갱신하고, Agent 2는 매 반복 시작 시 그 파일을 다시 읽어서 최신 지시를 따릅니다.

### 4.2 기술 스택을 Python으로 통일한 이유

Agent 2(프론트엔드)도 React/Vite 같은 Node.js 프레임워크 대신 **Streamlit**을 썼습니다. 무개입 2시간 루프에서 npm 설치 실패 같은 별도 생태계 리스크를 없애기 위한 선택으로, 두 에이전트 모두 `pip`만으로 완결됩니다.

### 4.3 실전에서 벌어진 일 (계획과 실제의 차이)

- 방에 들어왔을 때 `shared/` 폴더도, git 저장소도 없었습니다 — CONTRACT.md가 전제한 구조를 Agent 1이 직접 만들었는데, **공교롭게도 Agent 2도 거의 같은 순간 독립적으로 같은 결론(구조가 없으니 직접 만든다)에 도달해서 충돌 없이 수렴**했습니다.
- 백엔드 기본 포트(8000)를 이 프로젝트와 무관한 다른 IDE 프로세스가 점유하고 있어서, 방 안에서 8001로 바꾸고 `CONTRACT.md`/`TASKS_FOR_AGENT2.md`를 갱신해 공지했습니다.
- 세션 도중 **Agent 2가 토큰을 소진**해 더 이상 작업할 수 없게 되었고, 사람이 "상호 worktree 수정 금지" 규칙을 그 시점부터 해제해서 Agent 1이 프론트엔드까지 이어받아 완성했습니다.

---

## 5. 각 에이전트의 작업 계획 (PLAN.md)

각 에이전트는 자기 worktree 루트에 `PLAN.md`를 갖고, 매 반복(iteration) 시작 시 정해진 루틴을 따릅니다.

### 5.1 공통 반복(iteration) 루틴

1. 상대방의 상태 파일을 다시 읽는다(캐시된 이전 내용 아님) — Agent 1은 `AGENT2_STATUS.md`, Agent 2는 `TASKS_FOR_AGENT2.md`
2. **`shared/problem.md`도 함께 다시 읽고, 계획에 반영한다** (6장 참고)
3. 우선순위가 가장 높은 미완료 작업을 진행한다
4. 스키마/계약에 영향을 주는 변경이면 즉시 관련 문서를 갱신해 상대방에게 공지한다
5. 상대 worktree는 계약 위반 검증 목적으로만 읽는다(수정 금지)
6. 결과를 커밋한다 (`git stash` 금지)

플랜을 수정하기 전에는 저장소 전체를 훑지 않고 **수정 대상 파일 + 그 파일이 의존하는 파일 + 그 파일에 의존하는 파일**만 특정해서 읽습니다(토큰 절약).

### 5.2 Agent 1 (백엔드) — [worktree-agent1-backend/PLAN.md](worktree-agent1-backend/PLAN.md)

| 순위 | 작업 |
| --- | --- |
| 사전확인 | `ANTHROPIC_API_KEY` 환경변수 + 전체 ML 패키지 설치 확인 (방 밖에서 끝내야 하는 사람 전용 작업) |
| P0 | 업로드 엔드포인트 + 전처리(블러 감지, imagededup 중복 그룹핑) |
| P0 | 앨범 자동 분류 + `GET /api/albums` (2단계 클러스터링) |
| P0 | 얼굴 검출 분기 + 점수화 (mediapipe + CLIP aesthetic + zero-shot) |
| P0 | `GET /api/photos/{photo_id}` — 스키마 정확히 일치하는지가 가장 중요한 테스트 |
| P0 | `TASKS_FOR_AGENT2.md` 초기 작성 |
| P1 | `GET /api/report` 통계 집계 |
| P1 | `POST /api/generate-post` (Claude API) |
| P2 | (시간 남으면) 얼굴 클러스터링 — "가장 많이 찍힌 사람" |

### 5.3 Agent 2 (프론트엔드) — [worktree-agent2-frontend/PLAN.md](worktree-agent2-frontend/PLAN.md)

| 순위 | 작업 |
| --- | --- |
| P0 | 업로드 UI (`st.file_uploader`, 다중 선택) — 처리 결과는 `st.session_state`에 저장해 재실행마다 재처리하지 않음 |
| P0 | 앨범 선택 UI — 2개 이상이면 `st.selectbox`, 1개면 자동 선택 |
| P0 | 베스트컷 랭킹 — `st.tabs(["인물", "일반"])`, `aesthetic_score` 내림차순 |
| P1 | 리포트 카드 UI — `st.metric`/`st.columns`, nullable 카드는 숨김 |
| P1 | 후기 글 생성 UI — 블로그/인스타 스타일 선택, `st.code`로 출력 |

Agent 2는 API가 아직 없으면 CONTRACT.md 스키마 그대로 목업 데이터를 만들어 화면 작업을 먼저 진행하고, 실제 API가 준비되면(`TASKS_FOR_AGENT2.md` 갱신을 보고) 자동으로 전환합니다.

### 5.4 공통 탈출 조건 (두 에이전트 동일)

- 작업당 **최대 4회** 시도. 초과하면 멈추지 말고 "실패: [이유]"를 기록한 뒤 다음 우선순위 작업으로 자동 이동
- 질문하거나 사람의 응답을 기다리며 멈추지 않음 — 모호하면 합리적으로 가정하고 그 가정을 기록한 뒤 즉시 진행 (6장 참고)
- 테스트 `skip` 금지, `git stash` 금지

---

## 6. `problem.md` — 상하위 에이전트 공용 이슈 로그 & 다음 루프 반영

이 프로젝트에서 가장 중요한 협업 장치는 [`problem.md`](problem.md)입니다. `TASKS_FOR_AGENT2.md`/`AGENT2_STATUS.md`가 한쪽에서 다른 쪽으로만 흐르는 단방향 채널인 것과 달리, `problem.md`는 **상위(Agent 1)와 하위(Agent 2)가 함께 쓰고 함께 읽는 양방향 로그**입니다. `shared/CONTRACT.md` 0-2절에 아래 규칙으로 공식화되어 있습니다.

### 6.1 언제 쓰는가

- CONTRACT.md/PLAN.md가 전제한 것과 실제 환경이 다를 때 (예: 폴더 구조가 없었음, 포트가 이미 점유돼 있었음)
- 되돌리기 어렵거나 중대한 가정을 내렸을 때
- 사람이 방에 돌아왔을 때 반드시 알아야 할 문제
- 상대 에이전트 산출물에서 발견한 버그의 **근본 원인 진단** (코드는 고치지 않고 진단만 기록 — 실제 수정 지시는 `TASKS_FOR_AGENT2.md`로 별도 전달)

### 6.2 어떻게 쓰는가

**항상 append만 한다 — 파일 전체를 덮어쓰지 않는다.** 두 에이전트가 동시에 파일 전체를 새로 쓰면 레이스 컨디션으로 내용이 통째로 사라질 수 있습니다(실제로 이 프로젝트에서 한 번 발생했고, git 마지막 커밋에서 복구했습니다). 이후로는 모든 기록을 Edit/append 방식으로만 남깁니다.

### 6.3 다음 루프에 어떻게 반영하는가

매 반복(iteration) 시작 시, 각 에이전트는 자기 쪽 상태 파일뿐 아니라 `problem.md`도 함께 다시 읽고 그 내용을 **그 반복의 작업 계획에 반영**합니다.

```
반복 N:        문제 발견 → problem.md에 append (append-only)
                    ↓
반복 N+1 시작: AGENT2_STATUS.md / TASKS_FOR_AGENT2.md 재확인
                    +
               problem.md 재확인  ──▶  이번 반복 계획을 조정
                    ↓                  (수정 작업을 최우선으로 올리거나,
               작업 진행                기록된 가정과 충돌 않게 범위 조정)
```

예를 들어 "셀카 분류가 이상하다"는 사람의 피드백을 받아 1차 수정을 했는데, 그 수정이 다른 케이스(거울 셀카)를 새로 망가뜨렸다는 사실이 발견되면, 그 진단을 `problem.md`에 남기고 다음 작업에서 근본 원인(mediapipe의 얼굴 미검출)까지 고려한 재수정으로 이어지는 식입니다.

### 6.4 사람을 위한 단일 진입점

`problem.md`는 사람이 방을 비운 동안 두 에이전트가 스스로 판단·가정하며 진행한 내용 중 **사람이 검토해야 할 것들의 단일 진입점**입니다. 개별 STATUS 파일보다 이 파일을 먼저 보면 전체 그림을 파악할 수 있도록 유지합니다.

---

## 7. 실행 방법

### 사전 준비

```bash
# 저장소 루트 기준
python -m venv .venv
source .venv/bin/activate

# 백엔드(ML 포함) 패키지
pip install -r worktree-agent1-backend/requirements.txt

# 프론트엔드 패키지
pip install -r worktree-agent2-frontend/requirements.txt

# .env에 Claude API 키 설정 (후기 글 생성용)
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
echo "ANTHROPIC_MODEL=claude-sonnet-5" >> .env
```

### 백엔드 실행 (포트 8001)

```bash
cd worktree-agent1-backend
uvicorn app.main:app --port 8001
```

### 프론트엔드 실행 (포트 8501)

```bash
cd worktree-agent2-frontend
streamlit run app.py --server.port 8501
```

브라우저에서 `http://localhost:8501`을 열면 됩니다.

### 테스트

```bash
# 백엔드
cd worktree-agent1-backend && pytest

# 프론트엔드
cd worktree-agent2-frontend && python -m pytest
```

---

## 8. 프로젝트 구조

```
repo/
├── README.md                        # 이 파일
├── problem.md                       # 상하위 에이전트 공용 이슈 로그 (6장 참고)
├── dataset/                         # 파이프라인 테스트용 실제 여행 사진 샘플
├── shared/
│   ├── CONTRACT.md                  # API 계약 + 협업 규칙 (3, 4, 6장 원문)
│   ├── TASKS_FOR_AGENT2.md          # Agent 1 → Agent 2 지시
│   ├── AGENT1_STATUS.md             # Agent 1 진행 기록
│   └── AGENT2_STATUS.md             # Agent 2 진행 기록
├── worktree-agent1-backend/         # FastAPI + ML 파이프라인
│   ├── PLAN.md                      # Agent 1 작업 계획 (5.2장)
│   ├── app/
│   │   ├── main.py                  # API 라우트
│   │   ├── models.py                # Pydantic 스키마 (CONTRACT.md 3장과 1:1 대응)
│   │   ├── storage.py               # 인메모리 저장소
│   │   ├── preprocessing.py         # 블러 감지, 중복 그룹핑
│   │   ├── albums.py                # 2단계 앨범 클러스터링
│   │   ├── vision.py                # mediapipe + CLIP 추론
│   │   ├── face_clustering.py       # 인물 클러스터링 (P2)
│   │   ├── report.py                # 리포트 집계
│   │   └── generate_post.py         # Claude API 호출
│   ├── models/                      # mediapipe .tflite/.task 가중치
│   └── tests/
└── worktree-agent2-frontend/        # Streamlit 화면
    ├── PLAN.md                      # Agent 2 작업 계획 (5.3장)
    ├── app.py                       # 메인 화면
    ├── api_client.py                # 백엔드 호출 (BASE_URL 단일 관리)
    ├── utils.py                     # 정렬/필터/라벨 등 순수 함수
    ├── .streamlit/config.toml       # 화이트 미니멀 테마
    └── test_*.py
```

---

## 9. 알려진 한계

- **인메모리 저장소**: 백엔드를 재시작하면 업로드한 사진이 전부 사라집니다(데모 규모 가정, 영속 DB 없음).
- **얼굴 클러스터링은 근사치**: 전용 얼굴인식 모델이 아니라 CLIP 이미지 임베딩을 재사용한 방식이라 "가장 많이 찍힌 사람" 정확도가 완벽하지 않을 수 있습니다.
- **CLIP 제로샷 3지선다의 한계**: `selfie`/`food`/`landscape` 중 하나를 강제로 고르는 구조라, "그 어느 것도 아님"에 해당하는 사진은 억지로 셋 중 하나로 분류됩니다. 위 2.1절의 얼굴 개수 기반 보정으로 가장 흔한 오류(얼굴 없는 사진이 셀카로 분류)는 완화했지만 완전히 없애지는 못합니다.
- **48시간 임계값은 고정값**: 여행 간 시간 간격 클러스터링 기준(48시간)은 팀 실제 사진으로 캘리브레이션을 권장하는 값이며, 매우 짧은 여행이나 매우 긴 이동이 섞인 경우 오분류될 수 있습니다.
