from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from jarvis.api.app import create_app
from jarvis.api.auth import (
    COOKIE_NAME,
    FAILURE_WINDOW_SECONDS,
    MAX_FAILURES,
    SESSION_SECONDS,
    LoginLimiter,
    SessionSigner,
)
from jarvis.core.config import Environment
from tests.conftest import TEST_PASSWORD, TEST_TOKEN, make_settings
from tests.unit.test_health import STRONG

PROTECTED = [
    ("GET", "/api/me"),
    ("GET", "/api/modules"),
    ("POST", "/api/tarefas/add"),
    ("POST", "/api/tarefas/listar"),
    ("POST", "/api/tarefas/feito"),
    ("POST", "/api/tarefas/reabrir"),
    ("POST", "/api/tarefas/editar"),
    ("POST", "/api/tarefas/remover"),
]


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(make_settings(tmp_path))) as client:
        yield client


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_protected_routes_need_auth(client: TestClient, method: str, path: str) -> None:
    response = client.request(method, path, json={"title": "x"})
    assert response.status_code == 401
    assert response.json() == {"ok": False, "message": "Faça login para continuar.", "data": None}


def test_auth_happens_before_validation(client: TestClient) -> None:
    # Sem login, um corpo inválido ainda responde 401 (não revela nada sobre a rota).
    assert client.post("/api/tarefas/add", json={}).status_code == 401


def test_login_sets_a_30_day_http_only_cookie(client: TestClient) -> None:
    response = client.post("/api/login", json={"password": TEST_PASSWORD})
    assert response.status_code == 200
    assert response.json() == {"ok": True, "message": "Login feito.", "data": None}
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE_NAME}=")
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert f"Max-Age={SESSION_SECONDS}" in cookie
    assert "Secure" not in cookie  # em desenvolvimento (http://localhost)
    assert client.get("/api/me").json()["data"] == {"method": "session"}


def test_cookie_is_secure_in_production(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, env=Environment.production, **STRONG)
    settings.web_dir.mkdir(parents=True, exist_ok=True)
    (settings.web_dir / "index.html").write_text("ok", encoding="utf-8")
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/login", json={"password": STRONG["password"]})
    assert "Secure" in response.headers["set-cookie"]


def test_wrong_password(client: TestClient) -> None:
    response = client.post("/api/login", json={"password": "errada"})
    assert response.status_code == 401
    assert response.json()["message"] == "Senha incorreta."
    assert "set-cookie" not in response.headers


def test_login_is_rate_limited(client: TestClient) -> None:
    for _ in range(MAX_FAILURES):
        assert client.post("/api/login", json={"password": "errada"}).status_code == 401
    blocked = client.post("/api/login", json={"password": TEST_PASSWORD})
    assert blocked.status_code == 429
    assert blocked.json()["message"].startswith("Muitas tentativas erradas.")
    assert int(blocked.headers["retry-after"]) > 0


def test_limiter_window_and_reset() -> None:
    now = [1000.0]
    limiter = LoginLimiter(clock=lambda: now[0])
    for _ in range(MAX_FAILURES):
        limiter.fail("1.2.3.4")
    assert limiter.retry_after("1.2.3.4") is not None
    assert limiter.retry_after("5.6.7.8") is None  # outro IP não é afetado
    now[0] += FAILURE_WINDOW_SECONDS
    assert limiter.retry_after("1.2.3.4") is None
    limiter.fail("1.2.3.4")
    limiter.reset("1.2.3.4")
    assert limiter.retry_after("1.2.3.4") is None


def test_logout_clears_the_cookie(client: TestClient) -> None:
    client.post("/api/login", json={"password": TEST_PASSWORD})
    response = client.post("/api/logout")
    assert response.status_code == 200
    assert f'{COOKIE_NAME}=""' in response.headers["set-cookie"]
    assert client.get("/api/me").status_code == 401


def test_bearer_token(client: TestClient) -> None:
    ok = client.get("/api/me", headers={"authorization": f"Bearer {TEST_TOKEN}"})
    assert ok.json()["data"] == {"method": "token"}
    bad = client.get("/api/me", headers={"authorization": "Bearer outro-token"})
    assert bad.status_code == 401
    assert bad.json()["message"] == "Token inválido."


def test_tampered_or_garbage_cookie_is_rejected(client: TestClient) -> None:
    client.post("/api/login", json={"password": TEST_PASSWORD})
    value = client.cookies[COOKIE_NAME]
    issued, _, signature = value.partition(".")
    for forged in [f"{int(issued) + 1}.{signature}", "abc", "", "1.2.3", f"{issued}."]:
        client.cookies.clear()  # senão o cliente manda o cookie verdadeiro junto
        client.cookies.set(COOKIE_NAME, forged)
        assert client.get("/api/me").status_code == 401, forged


def test_session_signer_expiry() -> None:
    signer = SessionSigner("chave")
    cookie = signer.sign(1_000_000)
    assert signer.issued_at(cookie, 1_000_000 + SESSION_SECONDS - 1) == 1_000_000
    assert signer.issued_at(cookie, 1_000_000 + SESSION_SECONDS) is None  # expirou
    assert signer.issued_at(cookie, 999_999) is None  # emitido "no futuro"
    assert SessionSigner("outra-chave").issued_at(cookie, 1_000_001) is None


def test_session_is_renewed_after_a_day(tmp_path: Path) -> None:
    from jarvis.api import auth as auth_module

    app = create_app(make_settings(tmp_path))
    with TestClient(app) as client:
        two_days_ago = int(auth_module.time.time()) - 2 * 24 * 3600
        signer = SessionSigner(make_settings(tmp_path).secret_key.get_secret_value())  # pyright: ignore[reportOptionalMemberAccess]
        client.cookies.set(COOKIE_NAME, signer.sign(two_days_ago))
        response = client.get("/api/me")
        assert response.status_code == 200
        assert response.headers["set-cookie"].startswith(f"{COOKIE_NAME}=")  # cookie novo

        fresh = client.get("/api/me")
        assert "set-cookie" not in fresh.headers  # renovado há pouco: não renova de novo


@pytest.mark.parametrize(
    ("overrides", "problem"),
    [
        ({"password": None}, "JARVIS_PASSWORD não foi definido"),
        ({"api_token": "troque-este-token"}, "JARVIS_API_TOKEN ainda tem o valor de exemplo"),
        ({"secret_key": "curta"}, "JARVIS_SECRET_KEY precisa de pelo menos 16 caracteres"),
    ],
)
def test_production_refuses_weak_secrets(
    tmp_path: Path, overrides: dict[str, str | None], problem: str
) -> None:
    settings = make_settings(tmp_path, env=Environment.production, **{**STRONG, **overrides})
    with pytest.raises(RuntimeError, match=problem):
        create_app(settings)


def test_development_accepts_example_secrets(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, password="troque-esta-senha")
    with TestClient(create_app(settings)) as client:
        assert client.post("/api/login", json={"password": "troque-esta-senha"}).status_code == 200
