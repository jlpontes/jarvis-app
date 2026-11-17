import logging

import pytest
from pydantic import BaseModel, ConfigDict

from jarvis.core.command import Command, Response
from jarvis.core.database import Database
from jarvis.core.errors import JarvisError
from jarvis.core.module import Context, Module, action
from jarvis.core.registry import ModuleRegistry
from tests.conftest import FIXED_NOW


class EchoArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str


class EchoModule(Module):
    """Módulo de teste, no estilo do PingModule do C++."""

    name = "eco"

    @action("repetir", "Repete o texto", args=EchoArgs, result=str, text_arg="text")
    def repetir(self, ctx: Context, args: EchoArgs) -> Response[str]:
        return Response.success(args.text, args.text)

    @action("recusar", "Sempre recusa", args=EchoArgs, result=str)
    def recusar(self, ctx: Context, args: EchoArgs) -> Response[str]:
        raise JarvisError(f"Não vou repetir {args.text}.")

    @action("quebrar", "Erro inesperado", args=EchoArgs, result=str)
    def quebrar(self, ctx: Context, args: EchoArgs) -> Response[str]:
        raise RuntimeError("bug")


@pytest.fixture
def echo(db: Database) -> tuple[ModuleRegistry, Context]:
    registry = ModuleRegistry()
    registry.add(EchoModule())
    from zoneinfo import ZoneInfo

    return registry, Context.create(db, ZoneInfo("America/Sao_Paulo"), FIXED_NOW)


def run(echo: tuple[ModuleRegistry, Context], action: str, **args: object) -> Response[object]:
    registry, ctx = echo
    return registry.dispatch(Command(module="eco", action=action, args=dict(args)), ctx)  # pyright: ignore[reportArgumentType]


def test_add_rejects_duplicate_names() -> None:
    registry = ModuleRegistry()
    assert registry.add(EchoModule()) is True
    assert registry.add(EchoModule()) is False
    assert registry.has("eco")
    assert not registry.has("outro")


def test_actions_are_collected_in_declaration_order() -> None:
    assert [a.name for a in EchoModule().actions()] == ["repetir", "recusar", "quebrar"]


def test_dispatch_success(echo: tuple[ModuleRegistry, Context]) -> None:
    response = run(echo, "repetir", text="oi")
    assert response.ok and response.message == "oi" and response.data == "oi"


def test_unknown_module_and_action(echo: tuple[ModuleRegistry, Context]) -> None:
    registry, ctx = echo
    unknown = registry.dispatch(Command(module="nada", action="x"), ctx)
    assert not unknown.ok and unknown.message == "Módulo desconhecido: nada"
    assert run(echo, "voar").message == "Ação desconhecida: voar"


def test_domain_error_becomes_ok_false(echo: tuple[ModuleRegistry, Context]) -> None:
    response = run(echo, "recusar", text="isso")
    assert not response.ok and response.message == "Não vou repetir isso."
    assert not response.is_internal_error


def test_validation_error_is_friendly(echo: tuple[ModuleRegistry, Context]) -> None:
    assert run(echo, "repetir").message == "Falta o campo text."
    assert run(echo, "repetir", text="a", extra=1).message == "Campo desconhecido: extra."


def test_unexpected_error_is_logged_and_marked_internal(
    echo: tuple[ModuleRegistry, Context], caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR):
        response = run(echo, "quebrar", text="x")
    assert not response.ok
    assert response.is_internal_error
    assert "Erro interno no módulo 'eco'" in response.message
    assert "bug" not in response.message  # detalhes só no log
    assert "Falha no módulo eco" in caplog.text


def test_text_arg_must_be_a_field() -> None:
    with pytest.raises(ValueError, match="text_arg"):
        action("x", "x", args=EchoArgs, result=str, text_arg="nao_existe")
