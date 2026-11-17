"""Todo o SQL do módulo de tarefas mora aqui (equivale a TaskRepository do C++)."""

import sqlite3
from datetime import UTC, date, datetime

from jarvis.core.database import Database
from jarvis.modules.tasks.models import Priority, Task, TaskFilter

_COLUMNS = "id, title, due_date, priority, done, created_at, done_at"

# Ordem da lista: pendentes antes de concluídas; atrasadas primeiro; prioridade alta → baixa;
# prazo mais próximo primeiro (sem prazo por último); depois a ordem de criação.
_ORDER = """
ORDER BY done,
         CASE WHEN done = 0 AND due_date < ? THEN 0 ELSE 1 END,
         CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
         due_date IS NULL,
         due_date,
         id
"""


def to_db_timestamp(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _from_db_timestamp(text: str | None) -> datetime | None:
    return datetime.fromisoformat(text) if text else None


def _from_row(row: sqlite3.Row) -> Task:
    created_at = _from_db_timestamp(row["created_at"])
    assert created_at is not None
    return Task(
        id=row["id"],
        title=row["title"],
        due_date=date.fromisoformat(row["due_date"]) if row["due_date"] else None,
        priority=Priority(row["priority"]),
        done=bool(row["done"]),
        created_at=created_at,
        done_at=_from_db_timestamp(row["done_at"]),
    )


class TaskRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, title: str, due_date: date | None, priority: Priority, now: datetime) -> Task:
        with self._db.transaction():
            cursor = self._db.execute(
                "INSERT INTO tasks (title, due_date, priority, created_at) VALUES (?, ?, ?, ?)",
                (title, due_date.isoformat() if due_date else None, priority, to_db_timestamp(now)),
            )
        task = self.find(int(cursor.lastrowid or 0))
        assert task is not None
        return task

    def find(self, task_id: int) -> Task | None:
        row = self._db.query_one(f"SELECT {_COLUMNS} FROM tasks WHERE id = ?", (task_id,))
        return _from_row(row) if row is not None else None

    def list(self, filter: TaskFilter, today: date) -> list[Task]:
        today_text = today.isoformat()
        if filter is TaskFilter.all:
            rows = self._db.query(f"SELECT {_COLUMNS} FROM tasks {_ORDER}", (today_text,))
        elif filter is TaskFilter.today:
            rows = self._db.query(
                f"SELECT {_COLUMNS} FROM tasks WHERE done = 0 AND due_date <= ? {_ORDER}",
                (today_text, today_text),
            )
        else:
            rows = self._db.query(
                f"SELECT {_COLUMNS} FROM tasks WHERE done = 0 {_ORDER}", (today_text,)
            )
        return [_from_row(row) for row in rows]

    def set_done(self, task_id: int, done_at: datetime | None) -> None:
        """done_at preenchido = concluir; None = reabrir."""
        with self._db.transaction():
            self._db.execute(
                "UPDATE tasks SET done = ?, done_at = ? WHERE id = ?",
                (
                    1 if done_at else 0,
                    to_db_timestamp(done_at) if done_at else None,
                    task_id,
                ),
            )

    def update(
        self,
        task_id: int,
        *,
        title: str | None = None,
        due_date: date | None = None,
        priority: Priority | None = None,
        set_due_date: bool = False,
    ) -> None:
        """Atualiza só o que foi passado. `set_due_date=True` grava due_date mesmo se for None."""
        with self._db.transaction():
            if title is not None:
                self._db.execute("UPDATE tasks SET title = ? WHERE id = ?", (title, task_id))
            if priority is not None:
                self._db.execute("UPDATE tasks SET priority = ? WHERE id = ?", (priority, task_id))
            if set_due_date:
                self._db.execute(
                    "UPDATE tasks SET due_date = ? WHERE id = ?",
                    (due_date.isoformat() if due_date else None, task_id),
                )

    def remove(self, task_id: int) -> bool:
        with self._db.transaction():
            cursor = self._db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return cursor.rowcount > 0

    def import_task(
        self,
        source: str,
        source_id: int,
        title: str,
        done: bool,
        created_at: datetime,
        done_at: datetime | None,
    ) -> bool:
        """Insere uma tarefa vinda de outra fonte. False se essa (fonte, id) já foi importada."""
        with self._db.transaction():
            already = self._db.query_one(
                "SELECT 1 FROM task_imports WHERE source = ? AND source_id = ?",
                (source, source_id),
            )
            if already is not None:
                return False
            cursor = self._db.execute(
                "INSERT INTO tasks (title, priority, done, created_at, done_at)"
                " VALUES (?, 'medium', ?, ?, ?)",
                (
                    title,
                    1 if done else 0,
                    to_db_timestamp(created_at),
                    to_db_timestamp(done_at) if done_at else None,
                ),
            )
            self._db.execute(
                "INSERT INTO task_imports (source, source_id, task_id) VALUES (?, ?, ?)",
                (source, source_id, cursor.lastrowid),
            )
        return True
