"""Fixtures compartilhadas.

Os testes NUNCA usam ~/.jarvis-app nem ~/.jarvis: só pastas temporárias.
"""

from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from jarvis.core.command import Command, Response
from jarvis.core.config import Settings
from jarvis.core.database import Database
from jarvis.core.module import Context
from jarvis.core.registry import ModuleRegistry
from jarvis.modules import build_registry

TEST_PASSWORD = "senha-de-teste-123"
TEST_TOKEN = "token-de-teste-1234"
TEST_SECRET_KEY = "chave-de-teste-12345"

# 17/11/2026 às 12:00 em São Paulo (15:00 UTC). Uma terça-feira.
FIXED_NOW = datetime(2026, 11, 17, 15, 0, tzinfo=UTC)

type Dispatch = Callable[..., Response[Any]]


def make_settings(data_dir: Path, **overrides: Any) -> Settings:
    """Settings só com o que o teste passar: ignora o .env do repositório."""
    values: dict[str, Any] = {
        "data_dir": data_dir,
        "password": TEST_PASSWORD,
        "api_token": TEST_TOKEN,
        "secret_key": TEST_SECRET_KEY,
        "cpp_db_path": data_dir / "nao-existe" / "jarvis.db",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)  # pyright: ignore[reportCallIssue]


@pytest.fixture(autouse=True)
def _no_real_data_dirs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Mesmo que um teste esqueça, a pasta padrão de dados aponta para uma pasta temporária."""
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path / "data-padrao"))
    monkeypatch.setenv("JARVIS_CPP_DB_PATH", str(tmp_path / "cpp-padrao" / "jarvis.db"))


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return make_settings(tmp_path / "data")


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    with Database.open(tmp_path / "test.db") as database:
        yield database


@pytest.fixture
def registry(db: Database) -> ModuleRegistry:
    registry = build_registry()
    registry.init_all(db)
    return registry


@pytest.fixture
def dispatch(registry: ModuleRegistry, db: Database, settings: Settings) -> Dispatch:
    """dispatch("tarefas", "add", title="x", now=...) → Response, pelo registry, como o C++."""

    def run(module: str, action: str, *, now: datetime = FIXED_NOW, **args: Any) -> Response[Any]:
        ctx = Context.create(db, settings.zone, now)
        return registry.dispatch(Command(module=module, action=action, args=args), ctx)

    return run
