"""Módulo de tarefas testado de fora, só pelo dispatch (como os testes do C++)."""

from datetime import UTC, datetime
from typing import Any

import pytest

from jarvis.core.database import Database
from jarvis.core.registry import ModuleRegistry
from tests.conftest import Dispatch


def add(dispatch: Dispatch, title: str, **args: Any) -> dict[str, Any]:
    response = dispatch("tarefas", "add", title=title, **args)
    assert response.ok, response.message
    return response.model_dump(mode="json")["data"]


def titles(dispatch: Dispatch, filter: str = "pending") -> list[str]:
    response = dispatch("tarefas", "listar", filter=filter)
    assert response.ok, response.message
    return [t["title"] for t in response.model_dump(mode="json")["data"]]


def test_add_returns_the_task(dispatch: Dispatch) -> None:
    response = dispatch("tarefas", "add", title="  Comprar pão  ")
    assert response.ok
    assert response.message == "Tarefa #1 adicionada: Comprar pão"
    assert response.model_dump(mode="json")["data"] == {
        "id": 1,
        "title": "Comprar pão",
        "due_date": None,
        "priority": "medium",
        "done": False,
        "created_at": "2026-11-17T15:00:00Z",
        "done_at": None,
    }


def test_add_with_due_date_and_portuguese_priority(dispatch: Dispatch) -> None:
    task = add(dispatch, "Pagar luz", due_date="2026-11-20", priority="alta")
    assert task["due_date"] == "2026-11-20"
    assert task["priority"] == "high"


@pytest.mark.parametrize(
    ("args", "message"),
    [
        ({}, "Falta o campo Título."),
        ({"title": ""}, "Título não pode ficar vazio."),
        ({"title": "   "}, "Título não pode ficar vazio."),
        (
            {"title": "x", "due_date": "amanhã"},
            "Prazo: data inválida. Use AAAA-MM-DD, ex.: 2026-11-20.",
        ),
        (
            {"title": "x", "due_date": "2026-02-30"},
            "Prazo: data inválida. Use AAAA-MM-DD, ex.: 2026-11-20.",
        ),
        (
            {"title": "x", "priority": "urgente"},
            "Prioridade: valor inválido. Use um destes: 'low', 'medium' or 'high'.",
        ),
        ({"title": "x", "cor": "azul"}, "Campo desconhecido: cor."),
    ],
)
def test_add_rejects_invalid_input(dispatch: Dispatch, args: dict[str, Any], message: str) -> None:
    response = dispatch("tarefas", "add", **args)
    assert not response.ok
    assert response.message == message
    assert response.data is None


@pytest.mark.parametrize("bad", ["abc", "3abc", "-1", "0", "", "#", "#-2", "1.5", "³", True])
@pytest.mark.parametrize("action", ["feito", "reabrir", "remover", "editar"])
def test_invalid_ids_are_rejected(dispatch: Dispatch, action: str, bad: object) -> None:
    add(dispatch, "Uma tarefa")
    response = dispatch("tarefas", action, id=bad)
    assert not response.ok
    assert response.message == f"Id inválido: '{bad}'. Use um número, ex.: 3 ou #3."


@pytest.mark.parametrize("action", ["feito", "reabrir", "remover", "editar"])
def test_missing_task(dispatch: Dispatch, action: str) -> None:
    extra = {"title": "x"} if action == "editar" else {}
    response = dispatch("tarefas", action, id=99, **extra)
    assert not response.ok
    assert response.message == "Tarefa #99 não encontrada."


@pytest.mark.parametrize("task_id", [1, "1", "#1", " #1 "])
def test_ids_accept_number_and_hash(dispatch: Dispatch, task_id: object) -> None:
    add(dispatch, "Uma tarefa")
    assert dispatch("tarefas", "feito", id=task_id).ok


@pytest.mark.parametrize(
    "title",
    ["'); DROP TABLE tasks;--", 'Robert"); DELETE FROM tasks; --', "1 OR 1=1", "%_\\"],
)
def test_injection_looking_titles_are_just_text(
    dispatch: Dispatch, db: Database, title: str
) -> None:
    add(dispatch, "Antes")
    task = add(dispatch, title)
    assert task["title"] == title
    assert titles(dispatch) == ["Antes", title]
    tables = {row["name"] for row in db.query("SELECT name FROM sqlite_master")}
    assert "tasks" in tables


def test_list_order_overdue_priority_due_date(dispatch: Dispatch) -> None:
    add(dispatch, "sem prazo, baixa", priority="low")
    add(dispatch, "sem prazo, média")
    add(dispatch, "sexta, média", due_date="2026-11-20")
    add(dispatch, "amanhã, média", due_date="2026-11-18")
    add(dispatch, "amanhã, alta", due_date="2026-11-18", priority="high")
    add(dispatch, "atrasada, baixa", due_date="2026-11-01", priority="low")
    add(dispatch, "atrasada, alta", due_date="2026-11-16", priority="high")
    add(dispatch, "hoje, média", due_date="2026-11-17")
    assert titles(dispatch) == [
        "atrasada, alta",
        "atrasada, baixa",
        "amanhã, alta",
        "hoje, média",
        "amanhã, média",
        "sexta, média",
        "sem prazo, média",
        "sem prazo, baixa",
    ]


def test_list_filters(dispatch: Dispatch) -> None:
    add(dispatch, "atrasada", due_date="2026-11-10")
    add(dispatch, "hoje", due_date="2026-11-17")
    add(dispatch, "amanhã", due_date="2026-11-18")
    add(dispatch, "sem prazo")
    done = add(dispatch, "feita hoje", due_date="2026-11-17")
    assert dispatch("tarefas", "feito", id=done["id"]).ok

    assert titles(dispatch, "today") == ["atrasada", "hoje"]
    assert titles(dispatch, "hoje") == ["atrasada", "hoje"]  # apelido em português
    assert titles(dispatch, "pendentes") == ["atrasada", "hoje", "amanhã", "sem prazo"]
    assert titles(dispatch, "todas")[-1] == "feita hoje"  # concluídas vão para o fim
    assert len(titles(dispatch, "all")) == 5


def test_list_default_is_pending(dispatch: Dispatch) -> None:
    add(dispatch, "a")
    response = dispatch("tarefas", "listar")
    assert response.ok and response.message == "#1 [ ] a"


def test_list_messages(dispatch: Dispatch) -> None:
    assert dispatch("tarefas", "listar").message == "Nenhuma tarefa pendente."
    assert dispatch("tarefas", "listar", filter="all").message == "Nenhuma tarefa."
    assert dispatch("tarefas", "listar", filter="today").message == "Nada atrasado nem para hoje."
    add(dispatch, "Pagar luz", due_date="2026-11-16", priority="high")
    add(dispatch, "Comprar pão", due_date="2026-11-20")
    add(dispatch, "Mercado", due_date="2026-11-18")
    assert dispatch("tarefas", "listar").message == (
        "#1 [ ] Pagar luz · atrasada (16/11) · alta\n"
        "#3 [ ] Mercado · amanhã\n"
        "#2 [ ] Comprar pão · sex 20/11"
    )


def test_today_uses_configured_timezone(dispatch: Dispatch) -> None:
    add(dispatch, "vence dia 17", due_date="2026-11-17")
    # 01:00 UTC do dia 18 ainda é 22:00 do dia 17 em São Paulo: a tarefa é "de hoje".
    late_evening = datetime(2026, 11, 18, 1, 0, tzinfo=UTC)
    response = dispatch("tarefas", "listar", filter="today", now=late_evening)
    assert response.message == "#1 [ ] vence dia 17 · hoje"


def test_done_and_reopen(dispatch: Dispatch) -> None:
    add(dispatch, "Ler")
    done = dispatch("tarefas", "feito", id=1)
    assert done.ok and done.message == "Tarefa #1 concluída: Ler"
    assert done.model_dump(mode="json")["data"]["done_at"] == "2026-11-17T15:00:00Z"

    again = dispatch("tarefas", "feito", id=1)
    assert not again.ok and again.message == "Tarefa #1 já estava concluída."

    reopened = dispatch("tarefas", "reabrir", id="#1")
    assert reopened.ok and reopened.message == "Tarefa #1 reaberta: Ler"
    data = reopened.model_dump(mode="json")["data"]
    assert data["done"] is False and data["done_at"] is None

    twice = dispatch("tarefas", "reabrir", id=1)
    assert not twice.ok and twice.message == "Tarefa #1 já está pendente."


def test_edit_changes_only_what_was_sent(dispatch: Dispatch) -> None:
    add(dispatch, "Original", due_date="2026-11-20", priority="high")
    response = dispatch("tarefas", "editar", id=1, title="Novo título")
    assert response.ok and response.message == "Tarefa #1 editada: Novo título"
    data = response.model_dump(mode="json")["data"]
    assert data["due_date"] == "2026-11-20" and data["priority"] == "high"

    response = dispatch("tarefas", "editar", id=1, priority="baixa", due_date="2026-12-01")
    data = response.model_dump(mode="json")["data"]
    assert data["title"] == "Novo título"
    assert data["priority"] == "low" and data["due_date"] == "2026-12-01"


def test_edit_null_due_date_clears_it(dispatch: Dispatch) -> None:
    add(dispatch, "Com prazo", due_date="2026-11-20")
    response = dispatch("tarefas", "editar", id=1, due_date=None)
    assert response.ok
    assert response.model_dump(mode="json")["data"]["due_date"] is None


@pytest.mark.parametrize(
    ("args", "message"),
    [
        ({}, "Nada para editar. Mande título, prazo ou prioridade."),
        ({"title": None}, "Título não pode ficar vazio."),
        ({"title": "  "}, "Título não pode ficar vazio."),
        ({"priority": None}, "Prioridade não pode ficar vazia. Use low, medium ou high."),
    ],
)
def test_edit_rejects(dispatch: Dispatch, args: dict[str, Any], message: str) -> None:
    add(dispatch, "Tarefa")
    response = dispatch("tarefas", "editar", id=1, **args)
    assert not response.ok and response.message == message


def test_remove(dispatch: Dispatch) -> None:
    add(dispatch, "Apagar")
    removed = dispatch("tarefas", "remover", id="#1")
    assert removed.ok and removed.message == "Tarefa #1 removida: Apagar"
    assert removed.model_dump(mode="json")["data"]["title"] == "Apagar"
    assert dispatch("tarefas", "remover", id=1).message == "Tarefa #1 não encontrada."


def test_init_is_idempotent(registry: ModuleRegistry, db: Database) -> None:
    registry.init_all(db)
    registry.init_all(db)
    assert db.schema_version("tarefas") == 1
