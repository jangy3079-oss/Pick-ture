# AGENT1_STATUS.md (Agent 1이 작성, Agent 2는 참고용으로 읽을 수 있음)

## 마지막 갱신: 반복 1

## 완료
- (진행 중)

## 진행 중 / 실패
- [사전확인] ANTHROPIC_API_KEY 설정 확인 — 완료 (값 존재 확인)
- [사전확인] 패키지 설치 확인 — mediapipe/simple-aesthetics-predictor/open-clip-torch/imagededup/opencv-python/fastapi/uvicorn/anthropic/python-dotenv/pillow/reverse-geocode/torch 전부 설치됨. 완료
- [P0] 사진 업로드 엔드포인트 + 전처리 — 시작

## 가정
- 가정: 저장소가 git repo가 아니었고 CONTRACT.md 1절 폴더 구조(worktree-agent1-backend/, worktree-agent2-frontend/, shared/)가 없어서 직접 만듦. `git init` 실행, CONTRACT.md/PLAN_AGENT1.md/PLAN_AGENT2.md를 각각 shared/CONTRACT.md, worktree-agent1-backend/PLAN.md, worktree-agent2-frontend/PLAN.md로 이동. 상세 내역은 `/Users/mac/Loopcoding/problem.md` 참고.
- 가정: dataset/ 폴더(루트)의 실제 사진 20장을 파이프라인 테스트용 샘플로 사용. CONTRACT.md에 명시된 위치는 아니지만 유일한 실사진 소스라 그대로 사용.
- 가정: 업로드된 이미지 저장 위치는 `worktree-agent1-backend/data/images/<photo_id>.<ext>`, `image_url`은 `/api/photos/{photo_id}/image`로 서빙.
- 가정: 앨범/사진 메타데이터는 이번 스코프(데모 규모)에서 인메모리 dict로 관리(디스크 DB 불필요, CONTRACT.md에 영속성 요구 없음).

## 발견한 계약 불일치
- 없음 (아직 Agent 2 산출물 검증 전)
