"""Failure-delivery contracts for agent and script-only cron jobs."""

import pytest

from cron.scheduler import _summarize_cron_failure_for_delivery


@pytest.fixture
def script_job():
    return {"id": "script-123", "name": "agenda-sync", "no_agent": True}


@pytest.fixture
def agent_job():
    return {"id": "agent-123", "name": "briefing", "no_agent": False}


@pytest.mark.parametrize(
    "error",
    [
        "Script timed out after 300s: /opt/agenda-sync.py",
        "Google Calendar request timeout while fetching events",
        "HTTP 429 from Etsy inventory endpoint",
        "Google API returned 401 during calendar sync",
        "Backup upload failed with HTTP 403",
    ],
)
def test_no_agent_failures_keep_real_script_ownership(script_job, error):
    message = _summarize_cron_failure_for_delivery(script_job, error)

    assert "failed in script:" in message
    assert error.lower() in message.lower()
    assert "provider" not in message.lower()
    assert "fallback" not in message.lower()


def test_agent_timeout_still_uses_provider_classification(agent_job, monkeypatch):
    monkeypatch.setattr("cron.scheduler.load_config", lambda: {"fallback_providers": []})
    monkeypatch.setattr("cron.scheduler.get_fallback_chain", lambda _cfg: [])

    message = _summarize_cron_failure_for_delivery(
        agent_job, "Request timed out while awaiting model response"
    )

    assert "provider timeout" in message
    assert "No fallback chain configured" in message
    assert "failed in script" not in message


def test_existing_output_path_is_cited_with_mode_accurate_label(script_job, tmp_path):
    output_file = tmp_path / "run.md"
    output_file.write_text("captured script output", encoding="utf-8")

    message = _summarize_cron_failure_for_delivery(
        script_job,
        "Google Calendar request timeout",
        output_file=output_file,
    )

    assert f"Captured script output: `{output_file}`." in message


def test_missing_output_path_is_not_cited(script_job, tmp_path):
    missing = tmp_path / "missing.md"

    message = _summarize_cron_failure_for_delivery(
        script_job,
        "Google Calendar request timeout",
        output_file=missing,
    )

    assert str(missing) not in message
    assert "Captured script output" not in message
    assert "saved" not in message.lower()
