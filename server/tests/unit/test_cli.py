import io
from pathlib import Path

import pytest

from jarvis.cli import main


def run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = main(list(argv), out=out, err=err)
    return code, out.getvalue().strip(), err.getvalue().strip()


@pytest.fixture(autouse=True)
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "cli-data"
    monkeypatch.setenv("JARVIS_DATA_DIR", str(path))
    return path


def test_help_comes_from_the_registry() -> None:
    code, out, _ = run("help")
    assert code == 0
    assert "tarefas" in out
    assert "add <título> - Adiciona uma tarefa" in out
    assert "--priority (low|medium|high)" in out


def test_no_arguments_shows_help_and_fails() -> None:
    code, out, _ = run()
    assert code == 1 and out.startswith("Uso: jarvis")


def test_add_list_done_flow(data_dir: Path) -> None:
    assert run("tarefas", "add", "Comprar", "pão") == (0, "Tarefa #1 adicionada: Comprar pão", "")
    assert run("tarefas", "add", "Pagar luz", "--priority", "alta")[0] == 0
    _, listing, _ = run("tarefas", "listar")
    assert listing == "#2 [ ] Pagar luz · alta\n#1 [ ] Comprar pão"
    assert run("tarefas", "feito", "#1")[1] == "Tarefa #1 concluída: Comprar pão"
    assert run("tarefas", "feito", "2")[1] == "Tarefa #2 concluída: Pagar luz"
    assert run("tarefas", "listar")[1] == "Nenhuma tarefa pendente."
    assert run("tarefas", "listar", "todas")[1].count("[x]") == 2
    assert (data_dir / "jarvis.db").is_file()


def test_clear_a_field_with_empty_string() -> None:
    run("tarefas", "add", "Com prazo", "--due-date", "2026-11-20")
    assert run("tarefas", "editar", "1", "--due-date", "")[0] == 0
    assert "·" not in run("tarefas", "listar")[1]


@pytest.mark.parametrize(
    ("argv", "error"),
    [
        (["tarefas", "feito", "abc"], "Erro: Id inválido: 'abc'. Use um número, ex.: 3 ou #3."),
        (["tarefas", "feito", "99"], "Erro: Tarefa #99 não encontrada."),
        (["tarefas", "add"], "Erro: Falta o campo Título."),
        (
            ["tarefas", "add", "x", "--cor", "azul"],
            "Erro: Opção desconhecida: --cor. Veja: jarvis help",
        ),
        (["tarefas", "add", "x", "--priority"], "Erro: Falta o valor de --priority."),
        (["tarefas", "voar"], "Erro: Ação desconhecida: tarefas voar. Veja: jarvis help"),
        (["financas", "resumo"], "Erro: Módulo desconhecido: financas. Veja: jarvis help"),
        (["tarefas"], "Erro: Falta a ação. Uso: jarvis <modulo> <acao> [texto...] [--campo valor]"),
    ],
)
def test_errors_go_to_stderr_with_exit_1(argv: list[str], error: str) -> None:
    code, out, err = run(*argv)
    assert (code, out, err) == (1, "", error)
