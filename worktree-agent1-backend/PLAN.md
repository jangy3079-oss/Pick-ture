# PLAN.md — Agent 1 (지휘자 겸 백엔드/파이프라인)

역할: (1) 백엔드/파이프라인을 직접 구현하고, (2) 매 반복마다 Agent 2에게 줄 작업 지시서(`/shared/TASKS_FOR_AGENT2.md`)를 쓰고 갱신하며, (3) Agent 2의 산출물이 CONTRACT.md와 맞는지 검증한다. CONTRACT.md를 반드시 먼저 읽고 시작할 것.

Agent 2는 Streamlit(Python)으로 구현된다(CONTRACT.md 0-1 참고). 브라우저 `fetch`가 아니라 서버사이드에서 `requests`로 호출하므로 CORS 설정은 필요 없다 — FastAPI에 별도 CORS 미들웨어를 추가하지 않는다.

**질문 금지**: 판단이 필요한 모호한 상황에서 사람에게 묻지 않는다(CONTRACT.md 6-2). 합리적으로 가정하고 즉시 진행한 뒤, `AGENT1_STATUS.md`(신규 생성 가능)에 "가정: ..." 한 줄로 기록한다.

## 반복(iteration) 루틴

매 반복 시작 시 아래 순서를 지킨다:

1. `/shared/AGENT2_STATUS.md`를 다시 읽는다(캐시된 이전 내용 말고 최신본).
2. 아래 작업 목록에서 우선순위가 가장 높은 미완료 작업을 진행한다.
3. 작업이 API/스키마에 영향을 주면, 완료 즉시 `/shared/TASKS_FOR_AGENT2.md`를 갱신해서 Agent 2가 다음 반복에 반영할 수 있게 한다. **이 갱신(플랜 수정) 전에는 "Plan 수정 시 파일 읽기 범위" 절차를 따른다.**
4. Agent 2의 worktree를 읽어서(수정은 금지) CONTRACT.md 위반이 있으면, 코드를 고치지 말고 `TASKS_FOR_AGENT2.md`에 수정 지시를 추가한다.
5. 작업 결과를 커밋한다(`git stash` 금지).

## Plan 수정 시 파일 읽기 범위

`TASKS_FOR_AGENT2.md`를 갱신하거나, 안티그래비티 플랜/자기 작업 목록을 수정할 때는 저장소를 다시 훑지 않는다. 아래 세 가지만 특정해서 읽는다:

1. **수정 대상 파일**: 지금 바꾸려는 그 파일(예: 특정 API 핸들러, 또는 TASKS_FOR_AGENT2.md 자체)
2. **그 파일이 직접 의존하는 파일**: 그 파일이 import하거나 호출하는 모듈, 참조하는 스키마(CONTRACT.md 해당 섹션만)
3. **그 파일에 직접 의존하는 파일**: 그 파일을 import/호출하는 쪽 — 변경이 깨뜨릴 수 있는 대상. 이건 grep(예: 파일명/함수명 검색)으로 의존 대상만 특정해서 찾고, 찾아진 파일만 연다

worktree 전체를 열람하거나, 관련 없는 화면/모듈까지 미리 읽고 판단하지 않는다. 의존 관계가 불명확하면 grep으로 먼저 범위를 좁힌 뒤 그 결과에 있는 파일만 읽는다.

## 작업 목록 (우선순위 순)

0. **[방 들어가기 전 사전 확인, 루프 시작 대상 아님]** `ANTHROPIC_API_KEY` 환경변수 설정 확인 + 전체 패키지 설치(`pip install mediapipe simple-aesthetics-predictor open-clip-torch imagededup opencv-python fastapi uvicorn anthropic python-dotenv pillow reverse-geocode`, CONTRACT.md 6-1 참고). 전부 사람만 할 수 있는 사전 작업이라 방에 들어간 뒤 발견하면 해결 불가 — 방 밖에서 반드시 끝내둘 것. `reverse-geocode`는 로컬 데이터 기반이라 설치만 미리 끝내두면 런타임에 네트워크가 필요 없다. API 키가 없는 채로 방에 들어갔다면 작업 7(`POST /api/generate-post`)을 이번 사이클에서 제외하고 실패 기록 후 건너뛴다.
1. **[P0] 사진 업로드 엔드포인트 + 전처리**: 업로드 API, blur 감지(OpenCV Laplacian), imagededup으로 중복 그룹핑
2. **[P0] 앨범 자동 분류 + `GET /api/albums` 구현**: CONTRACT.md 3-1의 2단계 로직 — (1단계) EXIF `DateTimeOriginal` 기준 시간 간격 클러스터링(기본 임계값 48시간)으로 "여행" 단위를 나누고, (2단계) 각 여행 덩어리 안에서 `reverse-geocode`로 GPS→국가 변환 후 국가별로 재분류. 예: 한국-독일-오스트리아-한국 한 여행이면 한국/독일/오스트리아 3개 앨범으로 나뉘어야 함(같은 여행 안 동일 국가는 병합). GPS 없는 사진은 시간상 가장 가까운 GPS 있는 사진의 국가를 물려받고, 배치 전체에 GPS가 없으면 2단계를 건너뛰고 1단계 결과만 사용(이 경우 `country`는 전부 `null`). 각 사진에 `album_id` 부여. 팀 실제 샘플 사진으로 시간 임계값이 적절한지 한 번 확인해볼 것
3. **[P0] 얼굴 검출 분기 + 점수화**: mediapipe로 얼굴 검출 → `person`/`general` 분류, CLIP aesthetic 점수(simple-aesthetics-predictor + open-clip-torch), 인물일 경우 mediapipe blendshape로 눈감음/미소 보정
4. **[P0] `GET /api/photos/{photo_id}` 구현**: CONTRACT.md 3장 스키마(album_id 필드 포함) 그대로 반환하는 유닛테스트 작성 후 통과 확인
5. **[P0] `/shared/TASKS_FOR_AGENT2.md` 초기 작성**: Agent 2가 만들 화면 목록과 그 시점까지 확정된 API(GET /api/albums, GET /api/photos/{photo_id})를 명시 (아래 "초기 지시 예시" 참고). 참고: 이 항목이 아직 안 끝났어도 Agent 2는 자기 PLAN.md의 기본 작업 목록으로 먼저 움직이므로 대기 상태가 되지 않는다 — 이 항목은 "최초 시작 신호"가 아니라 "최신 지시로 갱신"이다
6. **[P1] `GET /api/report` 구현**: 통계 집계 (총 장수, 셀카/음식/풍경 비율은 CLIP 제로샷, 흔들림/눈감음 카운트, 최다 재촬영 그룹, 베스트컷, 단체사진 BEST). `album_id` 쿼리 파라미터 필수(CONTRACT.md 3장) — 특정 앨범 하나만 집계, 없으면 400. `top_location`은 EXIF GPS 있는 사진이 하나라도 있을 때만 채우고, 없으면 `null` 반환 — 억지로 만들지 말 것
7. **[P1] `POST /api/generate-post` 구현**: Claude API 호출로 리포트+베스트컷 기반 후기 글 생성, `style` 파라미터로 블로그/인스타 분기. 요청의 `report`는 항상 단일 앨범 기준(여러 앨범 합산 금지)
8. **[P2] (시간 남으면) 얼굴 클러스터링**: "가장 많이 찍힌 사람" — 이번 사이클에서 시간이 부족하면 스킵하고 실패 기록만 남긴 뒤 다음 작업으로 이동

## 탈출 조건

- 각 작업 항목은 **최대 4회** 시도. 4회 실패 시 멈추지 말고 "실패: [이유]"를 커밋 메시지와 `/shared/AGENT2_STATUS.md` 옆에 `AGENT1_STATUS.md`(신규 생성 가능)로 남긴 뒤, 다음 우선순위 작업으로 자동 이동한다.
- P0 항목이 모두 끝나기 전에는 P1로 넘어가지 않는다. P0가 4회 실패로 넘어갔다면 예외적으로 P1을 먼저 시도해도 된다(단, 이유를 기록).

## 검증 범위

- 통합 E2E 대신, 각 API 엔드포인트에 대한 유닛테스트(입력 → 스키마 일치 확인)로 한정
- `GET /api/photos/{photo_id}` 응답이 CONTRACT.md 3장 스키마와 필드명까지 정확히 일치하는지가 가장 중요한 테스트 — 여기서 어긋나면 Agent 2 전체가 막힘
- `GET /api/albums` 클러스터링은 극단적인 케이스(사진 전부 같은 시각, EXIF 전혀 없음, GPS 전혀 없음)에서도 에러 없이 앨범 1개(`country: null`)로 처리되는지 테스트. 한국-독일-오스트리아-한국처럼 같은 시간 덩어리 안에 같은 나라가 두 번 나오는 케이스도 병합되어 앨범 1개로 처리되는지 확인

## `/shared/TASKS_FOR_AGENT2.md` 초기 지시 예시 (첫 반복에 이 내용으로 작성)

```markdown
# TASKS_FOR_AGENT2.md (Agent 1이 작성/갱신, Agent 2는 읽기 전용)

## 지금 확정된 API
- GET /api/albums — 사용 가능 (CONTRACT.md 3장 스키마)
- GET /api/photos/{photo_id} — 사용 가능 (CONTRACT.md 3장 스키마, album_id 필드 포함)

## 우선순위
1. [P0] 업로드 UI (다중 파일 선택)
2. [P0] 앨범 선택 UI — GET /api/albums 호출, 앨범이 2개 이상이면 선택 UI, 1개면 자동 선택
3. [P0] 베스트컷 랭킹 화면 — 선택된 album_id로 필터링된 GET /api/photos/{photo_id} 응답을 aesthetic_score 기준 정렬 표시
4. [P1] 리포트 카드 UI — GET /api/report?album_id=... 는 아직 미구현, 목업 데이터로 먼저 화면만 만들어둘 것
5. [P1] 후기 글 생성 UI — POST /api/generate-post 완료되면 다시 공지

## 변경 이력
- (최초 작성)
```
