"""SQLite com controle de versão do esquema (equivale a jarvis/database.hpp do C++).

Regras: uma conexão por requisição (nunca compartilhada entre threads ao mesmo tempo),
foreign keys ligadas, WAL e busy timeout. SQL só em repositories, sempre com `?`.
"""

import sqlite3
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

type Params = Sequence[Any]

BUSY_TIMEOUT_MS = 5000

_SCHEMA_MIGRATIONS = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    module     TEXT    NOT NULL,
    version    INTEGER NOT NULL,
    applied_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    PRIMARY KEY (module, version)
)
"""


class Database:
    """Uma conexão SQLite. Abra com `Database.open(caminho)` e feche com `close()`."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    @classmethod
    def open(cls, path: Path | str) -> Database:
        """Abre (ou cria) o banco. `":memory:"` cria um banco temporário."""
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        # autocommit=True: cada comando fora de `transaction()` é confirmado na hora.
        # check_same_thread=False: o FastAPI pode abrir a conexão numa thread e usá-la em outra
        # dentro da MESMA requisição; nunca há duas threads usando a conexão ao mesmo tempo.
        conn = sqlite3.connect(
            path,
            autocommit=True,
            check_same_thread=False,
            timeout=BUSY_TIMEOUT_MS / 1000,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute(_SCHEMA_MIGRATIONS)
        return cls(conn)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Database:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Generator[None]:
        """Tudo dentro do bloco é confirmado junto, ou desfeito se der erro.

        BEGIN IMMEDIATE pega o lock de escrita logo no início, e o busy timeout faz as
        outras conexões esperarem a vez em vez de falhar com "database is locked".
        """
        if self._conn.in_transaction:  # já dentro de uma transação: só participa dela
            yield
            return
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self._conn.execute("ROLLBACK")
            raise
        self._conn.execute("COMMIT")

    def execute(self, sql: str, params: Params = ()) -> sqlite3.Cursor:
        return self._conn.execute(sql, params)

    def query(self, sql: str, params: Params = ()) -> list[sqlite3.Row]:
        rows: list[sqlite3.Row] = self._conn.execute(sql, params).fetchall()
        return rows

    def query_one(self, sql: str, params: Params = ()) -> sqlite3.Row | None:
        row: sqlite3.Row | None = self._conn.execute(sql, params).fetchone()
        return row

    def schema_version(self, module: str) -> int:
        """Última migration aplicada para o módulo (0 = nenhuma)."""
        row = self.query_one(
            "SELECT COALESCE(MAX(version), 0) FROM schema_migrations WHERE module = ?",
            (module,),
        )
        return int(row[0]) if row is not None else 0

    def migrate(self, module: str, version: int, sql: str) -> bool:
        """Aplica a migration se ainda não foi aplicada. True se aplicou agora."""
        with self.transaction():
            # Confere de novo DENTRO da transação: outro processo pode ter aplicado antes.
            if version <= self.schema_version(module):
                return False
            for statement in _split_statements(sql):
                self._conn.execute(statement)
            self._conn.execute(
                "INSERT INTO schema_migrations (module, version) VALUES (?, ?)",
                (module, version),
            )
        return True


def _split_statements(sql: str) -> list[str]:
    """Divide um script em comandos, respeitando `;` dentro de strings e triggers."""
    statements: list[str] = []
    current = ""
    for line in sql.splitlines(keepends=True):
        current += line
        if sqlite3.complete_statement(current):
            if current.strip():
                statements.append(current.strip())
            current = ""
    if current.strip():
        statements.append(current.strip())
    return statements
