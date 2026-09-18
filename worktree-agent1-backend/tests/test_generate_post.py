"""Unit tests for app.generate_post. Mocks the Anthropic client so the suite
never makes a real (paid, network-dependent) API call — the real call was
verified manually end-to-end against the live server (see shared/AGENT1_STATUS.md)."""
from unittest.mock import MagicMock, patch

import pytest

from app.generate_post import _report_summary, generate_post
from app.models import BestShot, ReportOut, TopLocation


def _report(**overrides):
    defaults = dict(
        total_photos=10, selfie_count=3, food_count=2, landscape_count=5,
        blurry_count=1, eyes_closed_count=0,
    )
    defaults.update(overrides)
    return ReportOut(**defaults)


def test_report_summary_omits_absent_optional_fields():
    summary = _report_summary(_report())
    assert "총 사진 수: 10" in summary
    assert "장소" not in summary  # no top_location
    assert "베스트컷" not in summary  # no best_shot


def test_report_summary_includes_present_optional_fields():
    summary = _report_summary(
        _report(top_location=TopLocation(place="Prague", count=10), best_shot=BestShot(photo_id="p1", aesthetic_score=9.2))
    )
    assert "Prague" in summary
    assert "9.2" in summary


def test_generate_post_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        generate_post("blog", _report(), [])


def test_generate_post_uses_configured_model_and_returns_text(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-5")

    fake_block = MagicMock(type="text", text="생성된 후기 텍스트")
    fake_response = MagicMock(content=[fake_block])
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response

    with patch("app.generate_post.Anthropic", return_value=fake_client) as mock_anthropic:
        result = generate_post("instagram", _report(), ["p1", "p2"])

    assert result == "생성된 후기 텍스트"
    mock_anthropic.assert_called_once_with(api_key="fake-key-for-test")
    _, kwargs = fake_client.messages.create.call_args
    assert kwargs["model"] == "claude-sonnet-5"
