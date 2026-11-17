from pathlib import Path

from fastapi.testclient import TestClient

from jarvis import __version__
from jarvis.api.app import create_app
from jarvis.core.config import Environment, Settings


def test_health_returns_status_and_version(tmp_path: Path) -> None:
    client = TestClient(create_app(Settings(data_dir=tmp_path)))
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_unknown_api_route_is_json_404(tmp_path: Path) -> None:
    client = TestClient(create_app(Settings(data_dir=tmp_path)))
    response = client.post("/api/nada/aqui")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")


def test_production_serves_frontend_with_spa_fallback(tmp_path: Path) -> None:
    web = tmp_path / "dist"
    web.mkdir()
    (web / "index.html").write_text("<html>jarvis</html>", encoding="utf-8")
    settings = Settings(env=Environment.production, data_dir=tmp_path, web_dir=web)
    client = TestClient(create_app(settings))

    html = {"accept": "text/html"}
    assert "jarvis" in client.get("/", headers=html).text
    assert "jarvis" in client.get("/tarefas", headers=html).text
    assert client.get("/api/nada", headers=html).status_code == 404
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/nada").status_code == 404
