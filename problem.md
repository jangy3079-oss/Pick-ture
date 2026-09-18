# problem.md — 사람이 꼭 확인해야 할 문제

(2026-09-18, 사람이 이전 내용을 확인하고 초기화함. 이 시점부터 새로 기록합니다.)

## 1. [Agent 1 진단] "탭을 눌러도 사진이 안 보이고 개수만 뜨는" 버그 — 백엔드 정상, 프론트 쪽 이슈
**확인 결과 백엔드는 정상입니다.** 직접 검증한 내용:
- `GET /api/photos?album_id=xxx` 응답 60장 전부 `image_url` 필드가 빠짐없이 채워져 있음(누락 0건).
- `GET /api/photos/{id}/image`를 서로 다른 사진 15장에 대해 연속 호출 — 전부 200, `Content-Type: image/jpeg`, 올바른 바이트 크기 반환. 실패 없음.

**원인은 프론트(Agent 2) 쪽으로 보입니다** (코드는 읽기만 했고 직접 수정하지 않음, CONTRACT.md 0장 규칙 준수):
`worktree-agent2-frontend/app.py`의 `_render_photo_card()`(약 193~196번째 줄)가 `photo.get("image_url", "")`를 **BASE_URL 접두사 없이 그대로** `_load_image()` → `requests.get(image_url, ...)`에 넘기고 있습니다. 그런데 `image_url`은 CONTRACT.md 스펙대로 `/api/photos/{id}/image` 같은 **상대경로**라서, `requests.get("/api/photos/.../image")`는 스킴이 없어 예외(`MissingSchema`)가 발생하고, `_load_image()`가 그 예외를 조용히 삼켜서 `None`을 반환 → 화면엔 플레이스홀더만 뜨고 사진은 안 보이는 것으로 보입니다. 흥미롭게도 Agent 2는 이미 `api_client.py`에 이 문제를 위한 `build_image_url()` 헬퍼(상대경로면 BASE_URL을 붙여주는 함수)를 만들어뒀는데, `_render_photo_card()`가 그 헬퍼를 안 쓰고 있는 것으로 보입니다. `TASKS_FOR_AGENT2.md`에 이 지점을 콕 집어 공지했습니다. 코드 수정은 하지 않았습니다.
