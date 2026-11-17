from pathlib import Path

import pytest

from jarvis.core.database import Database

SQL_V1 = "CREATE TABLE things (id INTEGER PRIMARY KEY, name TEXT NOT NULL);"


def test_migrate_applies_once(db: Database) -> None:
    assert db.schema_version("demo") == 0
    assert db.migrate("demo", 1, SQL_V1) is True
    assert db.migrate("demo", 1, SQL_V1) is False  # idempotente: não roda de novo
    assert db.schema_version("demo") == 1


def test_migrate_versions_are_per_module(db: Database) -> None:
    db.migrate("a", 1, "CREATE TABLE a1 (x INTEGER);")
    db.migrate("a", 2, "CREATE TABLE a2 (x INTEGER);")
    assert db.schema_version("a") == 2
    assert db.schema_version("b") == 0


def test_failed_migration_rolls_back_everything(db: Database) -> None:
    broken = "CREATE TABLE ok_table (x INTEGER);\nCREATE TABLE ok_table (x INTEGER);"
    with pytest.raises(Exception, match="already exists"):
        db.migrate("demo", 1, broken)
    assert db.schema_version("demo") == 0
    assert db.query_one("SELECT name FROM sqlite_master WHERE name = 'ok_table'") is None


def test_transaction_rolls_back_on_error(db: Database) -> None:
    db.migrate("demo", 1, SQL_V1)
    with pytest.raises(RuntimeError), db.transaction():
        db.execute("INSERT INTO things (name) VALUES (?)", ("a",))
        raise RuntimeError("falhou no meio")
    assert db.query("SELECT * FROM things") == []


def test_pragmas_are_on(tmp_path: Path) -> None:
    with Database.open(tmp_path / "pragmas.db") as db:
        assert db.query_one("PRAGMA foreign_keys")[0] == 1  # pyright: ignore[reportOptionalSubscript]
        assert db.query_one("PRAGMA journal_mode")[0] == "wal"  # pyright: ignore[reportOptionalSubscript]


def test_open_creates_parent_directories(tmp_path: Path) -> None:
    path = tmp_path / "a" / "b" / "jarvis.db"
    Database.open(path).close()
    assert path.is_file()
