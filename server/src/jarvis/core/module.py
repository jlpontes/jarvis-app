"""Módulo, ações e contexto (equivalem a IModule e ActionInfo do C++)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, ClassVar
from zoneinfo import ZoneInfo

from pydantic import BaseModel, TypeAdapter, ValidationError

from jarvis.core.command import Command, Response
from jarvis.core.database import Database
from jarvis.core.errors import JarvisError, friendly_validation_message


@dataclass(frozen=True)
class Context:
    """O que cada chamada recebe: a conexão desta requisição e o "agora"."""

    db: Database
    now: datetime  # sempre em UTC
    tz: ZoneInfo

    @classmethod
    def create(cls, db: Database, tz: ZoneInfo, now: datetime | None = None) -> Context:
        return cls(db=db, now=now or datetime.now(UTC), tz=tz)

    @property
    def today(self) -> date:
        """A data de hoje no fuso da pessoa (JARVIS_TZ), não em UTC."""
        return self.now.astimezone(self.tz).date()


type ActionHandler = Callable[[Any, Context, Any], Response[Any]]


@dataclass(frozen=True)
class ActionInfo:
    """Descrição de uma ação. Daqui saem a rota HTTP, os tipos do web, o help e (M5) a IA."""

    name: str
    description: str
    args: type[BaseModel]
    result: TypeAdapter[Any]
    result_type: Any  # o tipo em si (ex.: Task, list[Task]), para montar Response[...]
    text_arg: str | None
    handler: ActionHandler


_ACTION_ATTR = "__jarvis_action__"


def action(
    name: str,
    description: str,
    *,
    args: type[BaseModel],
    result: Any,
    text_arg: str | None = None,
) -> Callable[[ActionHandler], ActionHandler]:
    """Marca um método do módulo como ação. O método recebe (ctx, args) já validados."""
    if text_arg is not None and text_arg not in args.model_fields:
        raise ValueError(f"text_arg '{text_arg}' não é um campo de {args.__name__}")

    def decorate(fn: ActionHandler) -> ActionHandler:
        info = ActionInfo(
            name=name,
            description=description,
            args=args,
            result=TypeAdapter(result),
            result_type=result,
            text_arg=text_arg,
            handler=fn,
        )
        setattr(fn, _ACTION_ATTR, info)
        return fn

    return decorate


class Module:
    """Contrato de todo módulo. Subclasses definem `name` e métodos com `@action`."""

    name: ClassVar[str]

    def init(self, db: Database) -> None:
        """Chamado uma vez na inicialização (migrations). Padrão: nada."""

    def actions(self) -> list[ActionInfo]:
        """As ações declaradas com @action, na ordem em que aparecem na classe."""
        found: list[ActionInfo] = []
        for klass in reversed(type(self).__mro__):
            for attr in vars(klass).values():
                info = getattr(attr, _ACTION_ATTR, None)
                if isinstance(info, ActionInfo):
                    found.append(info)
        return found

    def find_action(self, name: str) -> ActionInfo | None:
        return next((info for info in self.actions() if info.name == name), None)

    def handle(self, ctx: Context, cmd: Command) -> Response[Any]:
        """Acha a ação pelo nome, valida os argumentos e chama o método."""
        info = self.find_action(cmd.action)
        if info is None:
            return Response.error(f"Ação desconhecida: {cmd.action}")
        try:
            args = info.args.model_validate(cmd.args)
        except ValidationError as exc:
            raise JarvisError(friendly_validation_message(exc.errors(), info.args)) from exc
        return info.handler(self, ctx, args)
