from __future__ import annotations

import json
from pathlib import Path

import pytest

typer = pytest.importorskip("typer")
pytest.importorskip("telethon")

from typer.testing import CliRunner

from telegrab.cli import app
from telegrab.config import RuntimeEnvironment
from telegrab.models import PreparedDownload

runner = CliRunner()


def test_describe_returns_json() -> None:
    result = runner.invoke(app, ["describe", "fetch"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "describe"
    assert payload["target"] == "fetch"
    assert payload["description"]["response"]["command"] == "fetch"


def test_doctor_returns_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    environment = RuntimeEnvironment(
        config_path=tmp_path / "config.json",
        data_dir=tmp_path / "data",
        session_stem=tmp_path / "data" / "user_session",
        credentials_present=True,
        credentials_source="env",
        env_api_id_valid=True,
    )
    monkeypatch.setattr("telegrab.cli.inspect_runtime_environment", lambda: environment)
    monkeypatch.setattr("telegrab.cli._session_present", lambda env: True)

    result = runner.invoke(app, ["doctor", "--output", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "doctor"
    assert payload["credentials_source"] == "env"
    assert payload["session_present"] is True


def test_fetch_dry_run_returns_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("telegrab.cli.load_runtime_config", lambda: object())

    async def fake_fetch(**kwargs):
        return PreparedDownload(
            source_url=kwargs["telegram_link"],
            message_id=42,
            would_write_to=str((tmp_path / "downloads" / "demo_42.mp4").resolve()),
            chat_id=123,
            dry_run=True,
        ).to_fetch_result()

    monkeypatch.setattr("telegrab.cli._fetch", fake_fetch)

    result = runner.invoke(
        app,
        ["fetch", "https://t.me/demo/42", "--dry-run", "--output", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "fetch"
    assert payload["dry_run"] is True
    assert payload["file_path"] is None
