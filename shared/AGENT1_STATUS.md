# AGENT1_STATUS.md (Agent 1이 작성, Agent 2는 참고용으로 읽을 수 있음)

## 마지막 갱신: 반복 3

## 완료
- [사전확인] ANTHROPIC_API_KEY 설정 확인 — 완료
- [사전확인] 패키지 설치 확인 — 전부 설치됨 (mediapipe는 0.10.35로 다운그레이드 필요했음, 아래 "해결한 이슈" 참고)
- [P0] 사진 업로드 엔드포인트 + 전처리 (blur, dedup) — 완료. `dataset/` 실사진 20장으로 실측 검증
- [P0] 앨범 자동 분류 (`GET /api/albums`) — 완료. 2단계 클러스터링(시간+국가) 구현, 유닛테스트 7개(단일앨범/48h분할/한국-독일-오스트리아-한국 병합 시나리오/GPS보간) 통과, 실사진으로도 검증(프라하 단일 앨범 정상 생성)
- [P0] 얼굴 검출 분기 + 점수화 — 완료. mediapipe 얼굴수/블렌드셰입, CLIP aesthetic score, zero-shot 태그(selfie/food/landscape) 전부 실사진 검증됨
- [P0] `GET /api/photos/{photo_id}` — 완료. CONTRACT.md 3장 스키마 필드명 정확히 일치 확인(유닛테스트 + 실제 서버 응답 모두 확인)
- [P0] `shared/TASKS_FOR_AGENT2.md` 갱신 — 완료 (아래 "최종 API 상태" 참고)
- [P1] `GET /api/report` — 완료. 실사진 업로드로 통계 산출 확인(셀카11/음식4/풍경5/블러5/most_retaken/best_shot/top_location 전부 정상)
- [P1] `POST /api/generate-post` — 완료. 실제 Claude API 호출로 블로그 후기 생성 성공 확인(style=blog)

## 최종 API 상태 (포트 8001 — 8000 아님, 아래 "해결한 이슈" 참고)
POST /api/upload, GET /api/albums, GET /api/photos, GET /api/photos/{photo_id}, GET /api/photos/{photo_id}/image, GET /api/report, POST /api/generate-post — 전부 구현 및 실동작 검증 완료. `worktree-agent1-backend/tests/` 27개 유닛테스트 전체 통과.

- [P2] 얼굴 클러스터링("가장 많이 찍힌 사람") — 완료. 전용 얼굴인식 모델 없이 기존 CLIP 임베딩을 얼굴 크롭에 재사용하는 근사 방식으로 구현(정확도는 완벽하지 않을 수 있음, 코드 주석에 명시). `GET /api/report`에 `most_photographed_person` 필드 추가(nullable, 가산적 변경) — CONTRACT.md와 TASKS_FOR_AGENT2.md에 반영. 실사진 업로드로 확인: count=3.

## 진행 중 / 실패
- (없음 — PLAN.md 작업 목록 전체 완료: P0 1~5, P1 6~7, P2 8)

## 해결한 이슈
- **mediapipe 1.0.1이 이 macOS(arm64) 환경에서 얼굴 검출/랜드마커 호출 시 무조건 크래시함** (`Check failed: service_ Service is unavailable.` in DrishtiMetalHelper, delegate=CPU를 명시해도 재현됨 — TensorsToDetectionsCalculator가 delegate 설정과 무관하게 Metal GPU 헬퍼를 초기화하려다 실패, abort()라서 Python에서 catch 불가). WebSearch로 확인한 known issue(google-ai-edge/mediapipe #6356)의 권장 조치대로 `pip install mediapipe==0.10.35`로 다운그레이드하여 해결함. `.venv`에 이미 설치되어 있던 1.0.1은 이 환경에서 사실상 못 쓰는 버전이었음 — CONTRACT.md 6-1의 사전 설치 패키지 목록에 버전 고정이 없었던 것이 원인. 이후 누군가 `pip install mediapipe`로 재설치하면 다시 깨질 수 있으니 주의.

## 가정
- 가정: 저장소가 git repo가 아니었고 CONTRACT.md 1절 폴더 구조(worktree-agent1-backend/, worktree-agent2-frontend/, shared/)가 없어서 직접 만듦. `git init` 실행, CONTRACT.md/PLAN_AGENT1.md/PLAN_AGENT2.md를 각각 shared/CONTRACT.md, worktree-agent1-backend/PLAN.md, worktree-agent2-frontend/PLAN.md로 이동. 상세 내역은 `/Users/mac/Loopcoding/problem.md` 참고.
- 가정: dataset/ 폴더(루트)의 실제 사진 20장을 파이프라인 테스트용 샘플로 사용. CONTRACT.md에 명시된 위치는 아니지만 유일한 실사진 소스라 그대로 사용.
- 가정: 업로드된 이미지 저장 위치는 `worktree-agent1-backend/data/images/<photo_id>.<ext>`, `image_url`은 `/api/photos/{photo_id}/image`로 서빙.
- 가정: 앨범/사진 메타데이터는 이번 스코프(데모 규모)에서 인메모리 dict로 관리(디스크 DB 불필요, CONTRACT.md에 영속성 요구 없음).

## 반복 3 (재검증 + 인시던트 대응)
- 사람 지시로 3개 핵심 엔드포인트(POST /api/upload, GET /api/photos?album_id=xxx 배열 반환, image_url+/api/photos/{id}/image 정적 서빙) 재검증: 이미 구현되어 있었고, `test_get_photo_image_serves_real_bytes`(dataset/ 실제 JPEG 바이트를 바이트 단위로 비교) 등 유닛테스트 2개를 추가로 작성해 명시적으로 커버함. 유닛테스트 36개 전체 통과.
- 서버 재기동 후 업로드→앨범→목록→상세→이미지→리포트→후기생성 전체 파이프라인 재실행, 에러 없음 확인(스모크 테스트).
- **인시던트**: 작업 중 `/problem.md`가 0바이트로 비어있는 것을 발견 — Agent 2가 같은 파일에 동시 쓰기를 시도하다 레이스 컨디션이 발생한 것으로 추정. 마지막 커밋에서 즉시 복구하고 커밋함(상세: problem.md 3-1절). 이후 이 파일은 전체 덮어쓰기 대신 append/Edit만 사용하고 더 자주 커밋하기로 함.
- 목업/하드코딩 데이터 사용 여부 점검: `app/` 프로덕션 코드에 mock/dummy/fake/placeholder 패턴 없음 확인(grep). 전부 실제 ML 파이프라인 결과만 사용.
- Agent 2도 같은 시점에 `api_client.py`에서 mock_data.py 의존성 제거 + BASE_URL을 8001로 전환하는 작업을 진행 중이었음(우리 worktree 아니므로 커밋은 Agent 2 몫으로 남겨둠, 코드는 읽기만 함).

## 발견한 계약 불일치
- 없음 (Agent 2의 api_client.py는 CONTRACT.md 필드명/엔드포인트와 정확히 일치하는 것으로 확인됨)

## 반복 4 — Agent 2 토큰 소진, Agent 1이 프론트엔드까지 직접 담당 (사람 승인)
- 백엔드: `POST /api/upload`에 콘텐츠 해시 dedup 추가(재업로드 누적 방지). 유닛테스트 3개 추가(41개 통과).
- 프론트: `app.py`/`.streamlit/config.toml` 직접 수정 — 이미지 안 보임 버그 수정(build_image_url 방어적 재적용), 리포트 카드 "크게 보기" 모달(st.dialog) 추가, 화이트 미니멀 테마 전면 교체, 하이라이트 카드 [1,1] 대칭 레이아웃 통일, 갤러리 썸네일 최적화(?size=thumb). `streamlit.testing.v1.AppTest`로 실 백엔드 데이터 주입 검증(신규 3개 테스트, 프론트 전체 35개 통과).
- 클린 재부팅 후 전체 흐름(업로드→앨범→리포트→후기생성→재업로드dedup) 재검증 완료, 에러 없음.
- 상세 내역은 `shared/AGENT2_STATUS.md` 반복4 절 참고.
