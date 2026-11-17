"""Guarda os módulos e entrega cada Command ao módulo certo (equivale a ModuleRegistry)."""

import logging
from typing import Any

from jarvis.core.command import Command, Response
from jarvis.core.database import Database
from jarvis.core.errors import JarvisError
from jarvis.core.module import ActionInfo, Context, Module

log = logging.getLogger(__name__)


class ModuleRegistry:
    def __init__(self) -> None:
        self._modules: dict[str, Module] = {}

    def add(self, module: Module) -> bool:
        """Registra um módulo. False se já existe um com o mesmo nome."""
        if module.name in self._modules:
            return False
        self._modules[module.name] = module
        return True

    def has(self, name: str) -> bool:
        return name in self._modules

    def get(self, name: str) -> Module | None:
        return self._modules.get(name)

    def find_action(self, module: str, action: str) -> ActionInfo | None:
        found = self._modules.get(module)
        return found.find_action(action) if found is not None else None

    def init_all(self, db: Database) -> None:
        for module in self._modules.values():
            module.init(db)

    def list(self) -> list[Module]:
        return list(self._modules.values())

    def dispatch(self, cmd: Command, ctx: Context) -> Response[Any]:
        """Entrega o comando ao módulo dono dele. Nunca lança exceção: sempre devolve Response."""
        module = self._modules.get(cmd.module)
        if module is None:
            return Response.error(f"Módulo desconhecido: {cmd.module}")
        try:
            return module.handle(ctx, cmd)
        except JarvisError as exc:
            return Response.error(exc.message)
        except Exception:  # erro inesperado: registra tudo no log, mostra pouco para a pessoa
            log.exception("Falha no módulo %s, ação %s", cmd.module, cmd.action)
            return Response.internal_error(
                f"Erro interno no módulo '{cmd.module}'. Veja o log da API."
            )
