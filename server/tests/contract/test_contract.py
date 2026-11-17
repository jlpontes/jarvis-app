"""O contrato de docs/contract.md, verificado por HTTP. Não supõe banco vazio."""

import uuid
from typing import Any

import httpx2 as httpx
import pytest

ACTIONS = ["add", "listar", "feito", "reabrir", "editar", "remover"]


def assert_response_shape(body: dict[str, Any], ok: bool) -> None:
    assert set(body) == {"ok", "message", "data"}
    assert body["ok"] is ok
    assert isinstance(body["message"], str) and body["message"]


def unique(title: str) -> str:
    return f"{title} {uuid.uuid4().hex[:8]}"


def test_health_needs_no_auth(anon: httpx.Client) -> None:
    response = anon.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok" and isinstance(body["version"], str)


@pytest.mark.parametrize("action", ACTIONS)
def test_actions_need_auth(anon: httpx.Client, action: str) -> None:
    response = anon.post(f"/api/tarefas/{action}", json={})
    assert response.status_code == 401
    assert_response_shape(response.json(), ok=False)


def test_wrong_password_is_401(anon: httpx.Client) -> None:
    response = anon.post("/api/login", json={"password": "certamente-errada"})
    assert response.status_code == 401
    assert_response_shape(response.json(), ok=False)


def test_bearer_token(anon: httpx.Client, token: str) -> None:
    headers = {"authorization": f"Bearer {token}"}
    response = anon.post("/api/tarefas/listar", json={}, headers=headers)
    assert response.status_code == 200


def test_unknown_module_and_action_are_404(client: httpx.Client) -> None:
    for path in ["/api/naoexiste/add", "/api/tarefas/naoexiste"]:
        response = client.post(path, json={})
        assert response.status_code == 404
        assert_response_shape(response.json(), ok=False)


def test_modules_lists_actions_with_schemas(client: httpx.Client) -> None:
    response = client.get("/api/modules")
    assert response.status_code == 200
    modules = {m["name"]: m for m in response.json()["data"]}
    names = [a["name"] for a in modules["tarefas"]["actions"]]
    assert names == ACTIONS
    for action in modules["tarefas"]["actions"]:
        assert action["args_schema"]["type"] == "object"


def test_task_lifecycle(client: httpx.Client) -> None:
    title = unique("Contrato")
    created = client.post(
        "/api/tarefas/add", json={"title": title, "due_date": "2030-01-15", "priority": "high"}
    )
    assert created.status_code == 200
    assert_response_shape(created.json(), ok=True)
    task = created.json()["data"]
    assert task["title"] == title
    assert task["due_date"] == "2030-01-15"
    assert task["priority"] == "high"
    assert task["done"] is False and task["done_at"] is None
    assert task["created_at"].endswith("Z")
    task_id = task["id"]

    listed = client.post("/api/tarefas/listar", json={"filter": "pending"}).json()["data"]
    assert task_id in [t["id"] for t in listed]

    done = client.post("/api/tarefas/feito", json={"id": task_id}).json()
    assert done["ok"] and done["data"]["done"] is True and done["data"]["done_at"].endswith("Z")

    again = client.post("/api/tarefas/feito", json={"id": task_id})
    assert again.status_code == 400
    assert_response_shape(again.json(), ok=False)

    reopened = client.post("/api/tarefas/reabrir", json={"id": f"#{task_id}"}).json()
    assert reopened["data"]["done"] is False

    edited = client.post("/api/tarefas/editar", json={"id": task_id, "due_date": None}).json()
    assert edited["data"]["due_date"] is None and edited["data"]["title"] == title

    removed = client.post("/api/tarefas/remover", json={"id": task_id})
    assert removed.status_code == 200 and removed.json()["data"]["id"] == task_id
    gone = client.post("/api/tarefas/remover", json={"id": task_id})
    assert gone.status_code == 400


@pytest.mark.parametrize("bad_id", ["abc", "3abc", -1, 0])
def test_invalid_ids_are_400(client: httpx.Client, bad_id: object) -> None:
    response = client.post("/api/tarefas/feito", json={"id": bad_id})
    assert response.status_code == 400
    assert_response_shape(response.json(), ok=False)


def test_validation_errors_are_400_not_422(client: httpx.Client) -> None:
    for body in [{}, {"title": ""}, {"title": "x", "due_date": "ontem"}, {"title": "x", "z": 1}]:
        response = client.post("/api/tarefas/add", json=body)
        assert response.status_code == 400, body
        assert_response_shape(response.json(), ok=False)


def test_logout(client: httpx.Client) -> None:
    assert client.post("/api/logout").status_code == 200
    assert client.get("/api/me").status_code == 401
