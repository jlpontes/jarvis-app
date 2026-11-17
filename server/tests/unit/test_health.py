from pathlib import Path

from fastapi.testclient import TestClient

from jarvis import __version__
from jarvis.api.app import create_app
from jarvis.core.config import Environment
from tests.conftest import make_settings

STRONG = {
    "password": "uma-senha-bem-comprida",
    "api_token": "um-token-bem-comprido-123",
    "secret_key": "uma-chave-bem-comprida-456",
}


def test_health_returns_status_and_version(tmp_path: Path) -> None:
    with TestClient(create_app(make_settings(tmp_path))) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_unknown_routes_are_json_404(tmp_path: Path) -> None:
    with TestClient(create_app(make_settings(tmp_path))) as client:
        assert client.post("/api/nada/aqui").json() == {
            "ok": False,
            "message": "Módulo desconhecido: nada",
            "data": None,
        }
        assert client.post("/api/tarefas/voar").json()["message"] == (
            "Ação desconhecida: tarefas voar"
        )
        response = client.get("/api/a/b/c")
        assert response.status_code == 404
        assert response.headers["content-type"].startswith("application/json")


def test_production_serves_frontend_with_spa_fallback(tmp_path: Path) -> None:
    web = tmp_path / "dist"
    web.mkdir()
    (web / "index.html").write_text("<html>jarvis</html>", encoding="utf-8")
    settings = make_settings(tmp_path, env=Environment.production, web_dir=web, **STRONG)
    with TestClient(create_app(settings)) as client:
        html = {"accept": "text/html"}
        assert "jarvis" in client.get("/", headers=html).text
        assert "jarvis" in client.get("/tarefas", headers=html).text
        assert client.get("/api/nada", headers=html).status_code == 404
        assert client.get("/api/health").json()["status"] == "ok"
