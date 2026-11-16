"""Aplicação FastAPI: rotas em /api e, em produção, o front já compilado."""

from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from jarvis import __version__
from jarvis.core.config import Environment, Settings, get_settings


class Health(BaseModel):
    status: Literal["ok"]
    version: str


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="Jarvis", version=__version__)

    @app.get("/api/health", operation_id="health")
    def health() -> Health:
        return Health(status="ok", version=__version__)

    # Rota desconhecida em /api responde 404 em JSON, e não com o index.html do front.
    @app.api_route(
        "/api/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        include_in_schema=False,
    )
    def api_not_found(path: str) -> None:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    if settings.env is Environment.production:
        # Navegação do navegador (Accept: text/html) em rota desconhecida recebe o index.html (SPA).
        app.frontend("/", directory=settings.web_dir, fallback="index.html", check_dir=True)

    return app
