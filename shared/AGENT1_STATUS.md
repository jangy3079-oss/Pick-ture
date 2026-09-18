# AGENT1_STATUS.md (Agent 1이 작성, Agent 2는 참고용으로 읽을 수 있음)

## 마지막 갱신: 반복 1

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

## 진행 중 / 실패
- [P2] 얼굴 클러스터링("가장 많이 찍힌 사람") — 아직 시작 전, 시간 남으면 진행

## 해결한 이슈
- **mediapipe 1.0.1이 이 macOS(arm64) 환경에서 얼굴 검출/랜드마커 호출 시 무조건 크래시함** (`Check failed: service_ Service is unavailable.` in DrishtiMetalHelper, delegate=CPU를 명시해도 재현됨 — TensorsToDetectionsCalculator가 delegate 설정과 무관하게 Metal GPU 헬퍼를 초기화하려다 실패, abort()라서 Python에서 catch 불가). WebSearch로 확인한 known issue(google-ai-edge/mediapipe #6356)의 권장 조치대로 `pip install mediapipe==0.10.35`로 다운그레이드하여 해결함. `.venv`에 이미 설치되어 있던 1.0.1은 이 환경에서 사실상 못 쓰는 버전이었음 — CONTRACT.md 6-1의 사전 설치 패키지 목록에 버전 고정이 없었던 것이 원인. 이후 누군가 `pip install mediapipe`로 재설치하면 다시 깨질 수 있으니 주의.

## 가정
- 가정: 저장소가 git repo가 아니었고 CONTRACT.md 1절 폴더 구조(worktree-agent1-backend/, worktree-agent2-frontend/, shared/)가 없어서 직접 만듦. `git init` 실행, CONTRACT.md/PLAN_AGENT1.md/PLAN_AGENT2.md를 각각 shared/CONTRACT.md, worktree-agent1-backend/PLAN.md, worktree-agent2-frontend/PLAN.md로 이동. 상세 내역은 `/Users/mac/Loopcoding/problem.md` 참고.
- 가정: dataset/ 폴더(루트)의 실제 사진 20장을 파이프라인 테스트용 샘플로 사용. CONTRACT.md에 명시된 위치는 아니지만 유일한 실사진 소스라 그대로 사용.
- 가정: 업로드된 이미지 저장 위치는 `worktree-agent1-backend/data/images/<photo_id>.<ext>`, `image_url`은 `/api/photos/{photo_id}/image`로 서빙.
- 가정: 앨범/사진 메타데이터는 이번 스코프(데모 규모)에서 인메모리 dict로 관리(디스크 DB 불필요, CONTRACT.md에 영속성 요구 없음).

## 발견한 계약 불일치
- 없음 (아직 Agent 2 산출물 검증 전)
