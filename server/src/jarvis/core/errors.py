"""Erros do domínio e tradução de erros de validação para mensagens em pt-BR."""

from collections.abc import Iterable, Sequence
from typing import Any

from pydantic import BaseModel
from pydantic_core import ErrorDetails


class JarvisError(Exception):
    """Erro esperado (regra de negócio): vira `ok=false` com esta mensagem para a pessoa."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _label(model: type[BaseModel] | None, field: str) -> str:
    if model is not None and field in model.model_fields:
        title = model.model_fields[field].title
        if title:
            return title
    return field


def _one(error: ErrorDetails, model: type[BaseModel] | None) -> str:
    loc: Sequence[int | str] = [part for part in error["loc"] if part != "body"]
    field = str(loc[0]) if loc else ""
    label = _label(model, field) if field else "Entrada"
    kind = error["type"]
    ctx: dict[str, Any] = dict(error.get("ctx") or {})

    if kind == "value_error":
        # Mensagem escrita por nós num validador (ex.: "Id inválido: 'abc'...").
        return str(ctx.get("error", error["msg"]))
    if kind == "missing":
        return f"Falta o campo {label}."
    if kind == "extra_forbidden":
        return f"Campo desconhecido: {field}."
    if kind == "string_too_short":
        return f"{label} não pode ficar vazio."
    if kind == "string_too_long":
        return f"{label} é longo demais (máximo {ctx.get('max_length')} caracteres)."
    if kind.startswith("date"):
        return f"{label}: data inválida. Use AAAA-MM-DD, ex.: 2026-11-20."
    if kind == "enum":
        return f"{label}: valor inválido. Use um destes: {ctx.get('expected', '')}."
    if kind in {"int_parsing", "int_type", "int_from_float"}:
        return f"{label}: precisa ser um número inteiro."
    if kind in {"string_type", "bool_type", "bool_parsing"}:
        return f"{label}: tipo de valor inválido."
    if kind in {"model_type", "dict_type"}:
        return "O corpo da requisição precisa ser um objeto JSON."
    if kind == "json_invalid":
        return "JSON inválido no corpo da requisição."
    return f"{label}: {error['msg']}."


def friendly_validation_message(
    errors: Iterable[ErrorDetails], model: type[BaseModel] | None = None
) -> str:
    """Junta os erros de validação do Pydantic numa mensagem curta em pt-BR."""
    messages = list(dict.fromkeys(_one(error, model) for error in errors))
    return " ".join(messages) if messages else "Entrada inválida."
