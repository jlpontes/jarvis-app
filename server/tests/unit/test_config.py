from pathlib import Path

import pytest

from jarvis.core.config import Environment, Settings


def test_reads_prefixed_environment_variables(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("JARVIS_ENV", "production")
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_TZ", "UTC")
    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert settings.env is Environment.production
    assert settings.data_dir == tmp_path
    assert settings.tz == "UTC"


def test_rejects_unknown_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JARVIS_ENV", "staging")
    with pytest.raises(ValueError):
        Settings(_env_file=None)  # pyright: ignore[reportCallIssue]


def test_expands_home_in_data_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JARVIS_DATA_DIR", "~/.jarvis-app-teste")
    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert settings.data_dir == Path.home() / ".jarvis-app-teste"
