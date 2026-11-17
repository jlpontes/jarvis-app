"""Command e Response: o pedido e a resposta (equivalem a jarvis/command.hpp do C++)."""

from typing import Any, Literal, cast

from pydantic import BaseModel, Field, JsonValue, PrivateAttr


class Command(BaseModel):
    """O pedido: "módulo X, faça a ação Y com estes argumentos"."""

    module: str
    action: str
    args: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])


class Response[T](BaseModel):
    """A resposta: deu certo? `message` para pessoas (pt-BR) e `data` para máquinas."""

    ok: bool = True
    message: str
    data: T | None = None

    # Não vai para o JSON: marca erros inesperados, para a API responder 500 em vez de 400.
    _internal_error: bool = PrivateAttr(default=False)

    @staticmethod
    def success[D](message: str, data: D) -> Response[D]:
        """Deu certo. O tipo de `data` define o tipo da resposta (ex.: Task → Response[Task])."""
        return cast(Response[D], Response[Any](ok=True, message=message, data=data))

    @staticmethod
    def error(message: str) -> Response[Any]:
        return Response[Any](ok=False, message=message, data=None)

    @staticmethod
    def internal_error(message: str) -> Response[Any]:
        response = Response.error(message)
        response._internal_error = True
        return response

    @property
    def is_internal_error(self) -> bool:
        return self._internal_error


class ErrorResponse(BaseModel):
    """Forma de toda resposta de erro em /api (usada na documentação do OpenAPI)."""

    ok: Literal[False] = False
    message: str
    data: None = None
