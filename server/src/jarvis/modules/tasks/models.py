"""Formas de dados do módulo de tarefas: a Task e os argumentos de cada ação."""

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints


class Priority(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class TaskFilter(StrEnum):
    pending = "pending"  # pendentes
    all = "all"  # todas, inclusive concluídas
    today = "today"  # pendentes com prazo até hoje (atrasadas + hoje)


# Apelidos em português aceitos na entrada (CLI e caixa de captura). A saída é sempre em inglês.
_PRIORITY_ALIASES = {"baixa": "low", "media": "medium", "média": "medium", "alta": "high"}
_FILTER_ALIASES = {"pendentes": "pending", "todas": "all", "hoje": "today"}


def _alias(aliases: dict[str, str]) -> Any:
    def convert(value: object) -> object:
        if isinstance(value, str):
            key = value.strip().lower()
            return aliases.get(key, key)
        return value

    return BeforeValidator(convert)


def _parse_task_id(value: object) -> object:
    """Aceita 3 e "#3". Recusa "abc", "3abc", "-1", "0" (mesma regra do parse_id do C++)."""
    if isinstance(value, bool):
        raise ValueError(f"Id inválido: '{value}'. Use um número, ex.: 3 ou #3.")
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str):
        text = value.strip().removeprefix("#")
        if text.isascii() and text.isdigit() and int(text) > 0:
            return int(text)
    raise ValueError(f"Id inválido: '{value}'. Use um número, ex.: 3 ou #3.")


TaskId = Annotated[int, BeforeValidator(_parse_task_id), Field(title="Id", gt=0)]
Title = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
    Field(title="Título"),
]
PriorityIn = Annotated[Priority, _alias(_PRIORITY_ALIASES), Field(title="Prioridade")]
DueDate = Annotated[date | None, Field(title="Prazo")]


class Task(BaseModel):
    id: int
    title: str
    due_date: date | None
    priority: Priority
    done: bool
    created_at: datetime  # UTC
    done_at: datetime | None  # UTC


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AddTaskArgs(_Args):
    title: Title
    due_date: DueDate = None
    priority: PriorityIn = Priority.medium


class ListTasksArgs(_Args):
    filter: Annotated[TaskFilter, _alias(_FILTER_ALIASES), Field(title="Filtro")] = (
        TaskFilter.pending
    )


class TaskIdArgs(_Args):
    id: TaskId


class EditTaskArgs(_Args):
    """Só os campos enviados mudam. `due_date: null` apaga o prazo."""

    id: TaskId
    # O rótulo (title=...) vai no campo: dentro de `X | None`, o do tipo se perde.
    title: Annotated[Title | None, Field(title="Título")] = None
    due_date: DueDate = None
    priority: Annotated[PriorityIn | None, Field(title="Prioridade")] = None
