"""Regra de dependência: api / cli / assistant → modules → core. Nunca o contrário."""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src" / "jarvis"

FORBIDDEN = {
    "core": ("jarvis.modules", "jarvis.api", "jarvis.cli", "jarvis.assistant"),
    "modules": ("jarvis.api", "jarvis.cli", "jarvis.assistant"),
}


def _imports(path: Path) -> list[str]:
    names: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


@pytest.mark.parametrize("layer", sorted(FORBIDDEN))
def test_layer_does_not_import_upwards(layer: str) -> None:
    files = sorted((SRC / layer).rglob("*.py"))
    assert files, f"nenhum arquivo em {layer}"
    violations = [
        f"{path.relative_to(SRC)} importa {name}"
        for path in files
        for name in _imports(path)
        if name.startswith(FORBIDDEN[layer])
    ]
    assert violations == []
