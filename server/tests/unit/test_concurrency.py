"""Várias conexões escrevendo ao mesmo tempo, como várias requisições na API."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from zoneinfo import ZoneInfo

from jarvis.core.command import Command
from jarvis.core.database import Database
from jarvis.core.module import Context
from jarvis.modules import build_registry

THREADS = 8
ADDS_PER_THREAD = 25


def test_parallel_writers_do_not_lock(tmp_path: Path) -> None:
    path = tmp_path / "concorrencia.db"
    registry = build_registry()
    with Database.open(path) as db:
        registry.init_all(db)

    def worker(n: int) -> list[bool]:
        results: list[bool] = []
        for i in range(ADDS_PER_THREAD):
            with Database.open(path) as db:  # uma conexão por "requisição"
                ctx = Context.create(db, ZoneInfo("UTC"))
                cmd = Command(module="tarefas", action="add", args={"title": f"t{n}-{i}"})
                response = registry.dispatch(cmd, ctx)
                results.append(response.ok)
        return results

    with ThreadPoolExecutor(THREADS) as pool:
        outcomes = [ok for batch in pool.map(worker, range(THREADS)) for ok in batch]

    assert all(outcomes)
    with Database.open(path) as db:
        count = db.query_one("SELECT COUNT(*) FROM tasks")
        assert count is not None and count[0] == THREADS * ADDS_PER_THREAD
