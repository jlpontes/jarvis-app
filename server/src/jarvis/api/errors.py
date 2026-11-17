"""Todo erro em /api sai no formato Response: {ok: false, message, data: null}."""

from collections.abc import Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from jarvis.core.command import ErrorResponse
from jarvis.core.errors import friendly_validation_message

_STATUS_MESSAGES = {
    401: "Faça login para continuar.",
    404: "Rota não encontrada.",
    405: "Método não permitido nesta rota.",
}


class ApiError(Exception):
    """Erro com status HTTP e mensagem para a pessoa."""

    def __init__(self, status_code: int, message: str, headers: Mapping[str, str] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.headers: Mapping[str, str] | None = headers


def error_json(
    status_code: int, message: str, headers: Mapping[str, str] | None = None
) -> JSONResponse:
    body = ErrorResponse(message=message).model_dump(mode="json")
    return JSONResponse(body, status_code=status_code, headers=headers)


def install_error_handlers(app: FastAPI, args_models: dict[str, type[BaseModel]]) -> None:
    """`args_models` mapeia o caminho da rota ao modelo dos argumentos (para nomes amigáveis)."""

    @app.exception_handler(ApiError)
    async def api_error(_: Request, exc: ApiError) -> JSONResponse:  # pyright: ignore[reportUnusedFunction]
        return error_json(exc.status_code, exc.message, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:  # pyright: ignore[reportUnusedFunction]
        model = args_models.get(request.url.path)
        return error_json(400, friendly_validation_message(exc.errors(), model))

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:  # pyright: ignore[reportUnusedFunction]
        message = _STATUS_MESSAGES.get(exc.status_code, exc.detail or "Erro.")
        return error_json(exc.status_code, message, exc.headers)
