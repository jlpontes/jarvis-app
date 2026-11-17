"""Importação das tarefas do C++, com um banco falso que imita o do ../Jarvis."""

import hashlib
import sqlite3
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from jarvis.core.database import Database
from jarvis.core.errors import JarvisError
from jarvis.core.registry import ModuleRegistry
from jarvis.modules.tasks.cpp_import import import_cpp_tasks, read_cpp_tasks
from tests.conftest import Dispatch

SAO_PAULO = ZoneInfo("America/Sao_Paulo")

# Cópia da migration kV1 de ../Jarvis/modules/tasks/src/migrations.hpp
CPP_V1 = """
CREATE TABLE tasks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL CHECK (length(trim(title)) > 0),
    done       INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    done_at    TEXT
);
"""


def make_cpp_db(path: Path, rows: list[tuple[str, int, str, str | None]]) -> Path:
    conn = sqlite3.connect(path)
    conn.executescript(CPP_V1)
    conn.executemany(
        "INSERT INTO tasks (title, done, created_at, done_at) VALUES (?, ?, ?, ?)", rows
    )
    conn.commit()
    conn.close()
    return path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def cpp_db(tmp_path: Path) -> Path:
    return make_cpp_db(
        tmp_path / "cpp.db",
        [
            ("Estudar ponteiros", 0, "2026-10-29 17:26:00", None),
            ("Configurar vcpkg", 1, "2026-10-28 09:00:00", "2026-10-28 22:30:00"),
        ],
    )


def test_imports_tasks_and_converts_local_time_to_utc(
    cpp_db: Path, db: Database, registry: ModuleRegistry, dispatch: Dispatch
) -> None:
    result = import_cpp_tasks(cpp_db, db, SAO_PAULO)
    assert (result.found, result.imported, result.skipped) == (2, 2, 0)

    tasks = dispatch("tarefas", "listar", filter="all").model_dump(mode="json")["data"]
    by_title = {t["title"]: t for t in tasks}
    assert by_title["Estudar ponteiros"]["created_at"] == "2026-10-29T20:26:00Z"  # 17:26 em SP
    assert by_title["Estudar ponteiros"]["done"] is False
    assert by_title["Configurar vcpkg"]["done"] is True
    assert by_title["Configurar vcpkg"]["done_at"] == "2026-10-29T01:30:00Z"


def test_running_twice_does_not_duplicate(
    cpp_db: Path, db: Database, registry: ModuleRegistry
) -> None:
    import_cpp_tasks(cpp_db, db, SAO_PAULO)
    again = import_cpp_tasks(cpp_db, db, SAO_PAULO)
    assert (again.found, again.imported, again.skipped) == (2, 0, 2)
    count = db.query_one("SELECT COUNT(*) FROM tasks")
    assert count is not None and count[0] == 2


def test_deleted_tasks_are_not_resurrected(
    cpp_db: Path, db: Database, registry: ModuleRegistry, dispatch: Dispatch
) -> None:
    import_cpp_tasks(cpp_db, db, SAO_PAULO)
    assert dispatch("tarefas", "remover", id=1).ok
    assert import_cpp_tasks(cpp_db, db, SAO_PAULO).imported == 0


def test_source_database_is_never_modified(
    cpp_db: Path, db: Database, registry: ModuleRegistry
) -> None:
    before = digest(cpp_db)
    import_cpp_tasks(cpp_db, db, SAO_PAULO)
    assert digest(cpp_db) == before
    assert not (cpp_db.parent / "cpp.db-wal").exists()


def test_read_only_connection_cannot_write(cpp_db: Path) -> None:
    # Prova de que mode=ro é de fato só leitura (a mesma URI que o importador usa).
    conn = sqlite3.connect(f"{cpp_db.resolve().as_uri()}?mode=ro", uri=True)
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        conn.execute("DELETE FROM tasks")
    conn.close()


def test_database_without_tasks_table(tmp_path: Path) -> None:
    # É o caso do ~/.jarvis/jarvis.db de hoje: só schema_migrations.
    path = tmp_path / "vazio.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE schema_migrations (module TEXT, version INTEGER)")
    conn.close()
    assert read_cpp_tasks(path, SAO_PAULO) == []


def test_missing_file_is_a_friendly_error(tmp_path: Path) -> None:
    missing = tmp_path / "nao-existe.db"
    with pytest.raises(JarvisError, match="não encontrado"):
        read_cpp_tasks(missing, SAO_PAULO)
    assert not missing.exists()  # não criou o arquivo


def test_cli_import(cpp_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import io

    from jarvis.cli import main

    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path / "app"))
    out = io.StringIO()
    assert main(["import-cpp-tasks", "--from", str(cpp_db)], out=out) == 0
    assert out.getvalue().strip() == "2 tarefa(s) importada(s); 0 já importada(s) antes."
    out = io.StringIO()
    main(["import-cpp-tasks", "--from", str(cpp_db)], out=out)
    assert out.getvalue().strip() == "0 tarefa(s) importada(s); 2 já importada(s) antes."
