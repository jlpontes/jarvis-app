"""Importação única, SÓ LEITURA, das tarefas do Jarvis em C++ (~/.jarvis/jarvis.db)."""

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jarvis.core.database import Database
from jarvis.core.errors import JarvisError
from jarvis.modules.tasks.repository import TaskRepository

SOURCE = "cpp"


@dataclass(frozen=True)
class CppTask:
    id: int
    title: str
    done: bool
    created_at: datetime  # UTC
    done_at: datetime | None  # UTC


@dataclass(frozen=True)
class ImportResult:
    found: int
    imported: int

    @property
    def skipped(self) -> int:
        return self.found - self.imported


def _local_to_utc(text: str | None, tz: ZoneInfo) -> datetime | None:
    """O C++ grava "AAAA-MM-DD HH:MM:SS" na hora local; aqui guardamos UTC."""
    if not text:
        return None
    return datetime.fromisoformat(text).replace(tzinfo=tz).astimezone(UTC)


def read_cpp_tasks(path: Path, tz: ZoneInfo) -> list[CppTask]:
    """Lê as tarefas do banco do C++ sem nunca escrever nele (mode=ro)."""
    if not path.is_file():
        raise JarvisError(f"Banco do Jarvis C++ não encontrado em {path}.")
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        conn.row_factory = sqlite3.Row
        has_table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'tasks'"
        ).fetchone()
        if has_table is None:
            return []
        rows: list[sqlite3.Row] = conn.execute(
            "SELECT id, title, done, created_at, done_at FROM tasks ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
    tasks: list[CppTask] = []
    for row in rows:
        created_at = _local_to_utc(row["created_at"], tz)
        assert created_at is not None
        tasks.append(
            CppTask(
                id=int(row["id"]),
                title=str(row["title"]),
                done=bool(row["done"]),
                created_at=created_at,
                done_at=_local_to_utc(row["done_at"], tz),
            )
        )
    return tasks


def import_cpp_tasks(source: Path, db: Database, tz: ZoneInfo) -> ImportResult:
    """Copia as tarefas para este app. Rodar duas vezes não duplica nada."""
    tasks = read_cpp_tasks(source, tz)
    repo = TaskRepository(db)
    imported = sum(
        repo.import_task(SOURCE, t.id, t.title, t.done, t.created_at, t.done_at) for t in tasks
    )
    return ImportResult(found=len(tasks), imported=imported)
