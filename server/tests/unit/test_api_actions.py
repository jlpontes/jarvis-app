"""As rotas geradas a partir das ações: corpo tipado, status e formato Response."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from jarvis.api.app import create_app
from tests.conftest import TEST_PASSWORD, make_settings


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(make_settings(tmp_path))) as client:
        client.post("/api/login", json={"password": TEST_PASSWORD})
        yield client


def test_every_action_has_a_typed_route(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    for action in ["add", "listar", "feito", "reabrir", "editar", "remover"]:
        operation = schema["paths"][f"/api/tarefas/{action}"]["post"]
        assert operation["operationId"] == f"tarefas_{action}"
        assert "requestBody" in operation
        assert set(operation["responses"]) == {"200", "400", "401"}  # sem o 422 padrão
    assert "HTTPValidationError" not in schema["components"]["schemas"]


def test_add_and_list(client: TestClient) -> None:
    created = client.post("/api/tarefas/add", json={"title": "Pão", "priority": "high"})
    assert created.status_code == 200
    assert created.json()["data"]["priority"] == "high"
    listed = client.post("/api/tarefas/listar", json={})
    assert listed.json()["data"][0]["title"] == "Pão"


def test_domain_and_validation_errors_are_400(client: TestClient) -> None:
    missing = client.post("/api/tarefas/feito", json={"id": 99})
    assert missing.status_code == 400
    assert missing.json() == {"ok": False, "message": "Tarefa #99 não encontrada.", "data": None}

    invalid = client.post("/api/tarefas/feito", json={"id": "3abc"})
    assert invalid.status_code == 400
    assert invalid.json()["message"] == "Id inválido: '3abc'. Use um número, ex.: 3 ou #3."

    empty = client.post("/api/tarefas/add", json={})
    assert empty.status_code == 400 and empty.json()["message"] == "Falta o campo Título."

    not_json = client.post(
        "/api/tarefas/add", content="oi", headers={"content-type": "application/json"}
    )
    assert not_json.status_code == 400


def test_edit_over_http_distinguishes_null_from_missing(client: TestClient) -> None:
    client.post("/api/tarefas/add", json={"title": "x", "due_date": "2026-11-20"})
    kept = client.post("/api/tarefas/editar", json={"id": 1, "title": "y"}).json()["data"]
    assert kept["due_date"] == "2026-11-20"
    cleared = client.post("/api/tarefas/editar", json={"id": 1, "due_date": None}).json()["data"]
    assert cleared["due_date"] is None


def test_modules_describe_actions(client: TestClient) -> None:
    modules = client.get("/api/modules").json()["data"]
    tasks = next(m for m in modules if m["name"] == "tarefas")
    add = next(a for a in tasks["actions"] if a["name"] == "add")
    assert add["description"] == "Adiciona uma tarefa"
    assert add["text_arg"] == "title"
    assert add["args_schema"]["required"] == ["title"]
    assert "title" in add["result_schema"]["properties"]
