"""POST /api/generate-post: Claude API call to draft a trip recap post.

Assumption: ANTHROPIC_MODEL env var names the model (CONTRACT.md 6-1 only
mandates ANTHROPIC_API_KEY explicitly; ANTHROPIC_MODEL is present in .env so we
use it rather than hardcoding a model id). Falls back to "claude-sonnet-5" if
unset — the current default Claude model as of this session (2026-09-18).
"""
from __future__ import annotations

import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

from app.models import ReportOut

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

DEFAULT_MODEL = "claude-sonnet-5"

_STYLE_INSTRUCTIONS = {
    "blog": (
        "블로그 여행 후기 글을 써줘. 문단 2~4개, 편안한 구어체, 사진 통계를 자연스럽게 녹여서 "
        "여행의 하이라이트를 이야기하듯 서술해줘."
    ),
    "instagram": (
        "인스타그램 캡션을 써줘. 3~5문장 이내로 짧고 감성적으로, 어울리는 해시태그 5~8개를 "
        "마지막 줄에 붙여줘."
    ),
}


def _client() -> Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    return Anthropic(api_key=api_key)


def _report_summary(report: ReportOut) -> str:
    lines = [
        f"총 사진 수: {report.total_photos}",
        f"셀카: {report.selfie_count}장, 음식: {report.food_count}장, 풍경: {report.landscape_count}장",
        f"흔들린 사진: {report.blurry_count}장, 눈 감은 사진: {report.eyes_closed_count}장",
    ]
    if report.top_location:
        lines.append(f"가장 많이 방문한 장소: {report.top_location.place} ({report.top_location.count}장)")
    if report.most_retaken:
        lines.append(f"가장 많이 다시 찍은 장면: {report.most_retaken.count}번 연속 촬영")
    if report.best_shot:
        lines.append(f"베스트컷 미학 점수: {report.best_shot.aesthetic_score}")
    if report.best_group_photo:
        lines.append(
            f"베스트 단체컷: 얼굴 {report.best_group_photo.face_count}명, "
            f"미학 점수 {report.best_group_photo.aesthetic_score}"
        )
    return "\n".join(lines)


def generate_post(style: str, report: ReportOut, best_shot_ids: list[str]) -> str:
    instruction = _STYLE_INSTRUCTIONS.get(style, _STYLE_INSTRUCTIONS["blog"])
    model = os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL

    prompt = (
        f"{instruction}\n\n다음은 이번 여행의 사진 통계 리포트야:\n{_report_summary(report)}\n\n"
        f"베스트컷으로 선정된 사진 수: {len(best_shot_ids)}장\n\n"
        "위 정보만 사용해서 실제 있었던 일처럼 지어내지 말고, 통계에 기반한 자연스러운 후기를 작성해줘."
    )

    client = _client()
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")
