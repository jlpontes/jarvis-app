"""CLI do Jarvis: um cliente fino do mesmo registry que a API usa.

jarvis help
jarvis tarefas add Comprar pão --due-date 2026-11-20 --priority alta
jarvis tarefas listar todas
jarvis tarefas feito #3
jarvis import-cpp-tasks [--from CAMINHO]
"""

import argparse
import sys
from collections.abc import Sequence
from enum import Enum
from pathlib import Path
from typing import Any, TextIO, get_args

from pydantic.fields import FieldInfo

from jarvis.core.command import Command
from jarvis.core.config import Settings, get_settings
from jarvis.core.database import Database
from jarvis.core.errors import JarvisError
from jarvis.core.module import ActionInfo, Context
from jarvis.core.registry import ModuleRegistry
from jarvis.modules import build_registry
from jarvis.modules.tasks.cpp_import import import_cpp_tasks

USAGE = "Uso: jarvis <modulo> <acao> [texto...] [--campo valor]"


def _flag(field: str) -> str:
    return "--" + field.replace("_", "-")


def _enum_in(annotation: Any) -> type[Enum] | None:
    """Acha um Enum dentro de tipos como `Priority | None` ou `Annotated[Priority, ...]`."""
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation
    for inner in get_args(annotation):
        found = _enum_in(inner)
        if found is not None:
            return found
    return None


def _field_hint(name: str, field: FieldInfo) -> str:
    enum = _enum_in(field.annotation)
    choices = " (" + "|".join(str(m.value) for m in enum) + ")" if enum else ""
    return f"{_flag(name)}{choices}"


def _text_label(info: ActionInfo) -> str:
    if info.text_arg is None:
        return ""
    title = info.args.model_fields[info.text_arg].title or info.text_arg
    return f" <{title.lower()}>"


def format_help(registry: ModuleRegistry) -> str:
    """O help sai do registry, como o print_help do C++, agora com os campos de cada ação."""
    lines = [USAGE, "", "Módulos disponíveis:"]
    for module in registry.list():
        lines += ["", f"  {module.name}"]
        for info in module.actions():
            lines.append(f"    {info.name}{_text_label(info)} - {info.description}")
            flags = [
                _field_hint(name, field)
                for name, field in info.args.model_fields.items()
                if name != info.text_arg
            ]
            if flags:
                lines.append(f"        opções: {', '.join(flags)}")
    lines += [
        "",
        "Outros comandos:",
        "  import-cpp-tasks [--from CAMINHO] - copia as tarefas do Jarvis em C++ (só leitura)",
        "",
        'Use "" para apagar um campo, ex.: jarvis tarefas editar 3 --due-date ""',
    ]
    return "\n".join(lines)


def parse_action_args(info: ActionInfo, words: Sequence[str]) -> dict[str, Any]:
    """Transforma `Comprar pão --due-date 2026-11-20` em {"title": ..., "due_date": ...}.

    Os valores seguem como texto: quem valida e converte é o modelo Pydantic da ação.
    """
    fields = info.args.model_fields
    flags = {_flag(name): name for name in fields}
    args: dict[str, Any] = {}
    text: list[str] = []
    i = 0
    while i < len(words):
        word = words[i]
        if word.startswith("--") and word != "--":
            name = flags.get(word)
            if name is None:
                raise JarvisError(f"Opção desconhecida: {word}. Veja: jarvis help")
            if i + 1 >= len(words):
                raise JarvisError(f"Falta o valor de {word}.")
            value = words[i + 1]
            args[name] = None if value == "" else value
            i += 2
            continue
        text.append(word)
        i += 1
    if text:
        if info.text_arg is None:
            raise JarvisError(f"A ação {info.name} não recebe texto livre. Veja: jarvis help")
        args[info.text_arg] = " ".join(text)
    return args


def _run_import(settings: Settings, argv: Sequence[str], out: TextIO) -> int:
    parser = argparse.ArgumentParser(prog="jarvis import-cpp-tasks")
    parser.add_argument("--from", dest="source", type=Path, default=settings.cpp_db_path)
    options = parser.parse_args(argv)
    with Database.open(settings.db_path) as db:
        build_registry().init_all(db)
        result = import_cpp_tasks(options.source, db, settings.zone)
    if result.found == 0:
        print("Nenhuma tarefa para importar no banco do Jarvis C++.", file=out)
    else:
        imported, skipped = result.imported, result.skipped
        print(f"{imported} tarefa(s) importada(s); {skipped} já importada(s) antes.", file=out)
    return 0


def main(
    argv: Sequence[str] | None = None, out: TextIO = sys.stdout, err: TextIO = sys.stderr
) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    settings = get_settings()
    registry = build_registry()

    if not argv or argv[0] in {"help", "-h", "--help"}:
        print(format_help(registry), file=out)
        return 0 if argv else 1

    try:
        if argv[0] == "import-cpp-tasks":
            return _run_import(settings, argv[1:], out)

        if len(argv) < 2:
            raise JarvisError(f"Falta a ação. {USAGE}")
        module, action, *words = argv
        if not registry.has(module):
            raise JarvisError(f"Módulo desconhecido: {module}. Veja: jarvis help")
        info = registry.find_action(module, action)
        if info is None:
            raise JarvisError(f"Ação desconhecida: {module} {action}. Veja: jarvis help")
        cmd = Command(module=module, action=action, args=parse_action_args(info, words))

        with Database.open(settings.db_path) as db:
            registry.init_all(db)
            response = registry.dispatch(cmd, Context.create(db, settings.zone))
    except JarvisError as exc:
        print(f"Erro: {exc.message}", file=err)
        return 1

    if response.ok:
        print(response.message, file=out)
        return 0
    print(f"Erro: {response.message}", file=err)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
