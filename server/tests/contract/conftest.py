"""Suíte de contrato: fala com a API só por HTTP, como qualquer cliente.

Por padrão sobe a API Python numa porta livre, com banco temporário. Para checar outro
servidor (por exemplo, o Jarvis em C++ no futuro):

    JARVIS_CONTRACT_URL=http://127.0.0.1:8080 JARVIS_CONTRACT_PASSWORD=... make contract
"""

import os
import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import httpx2 as httpx
import pytest
import uvicorn

from jarvis.api.app import create_app
from tests.conftest import TEST_PASSWORD, TEST_TOKEN, make_settings


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def base_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    external = os.environ.get("JARVIS_CONTRACT_URL")
    if external:
        yield external.rstrip("/")
        return

    data_dir: Path = tmp_path_factory.mktemp("contract-data")
    app = create_app(make_settings(data_dir))
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("A API de teste não subiu em 10 s.")
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture(scope="session")
def password() -> str:
    return os.environ.get("JARVIS_CONTRACT_PASSWORD") or TEST_PASSWORD


@pytest.fixture(scope="session")
def token() -> str:
    return os.environ.get("JARVIS_CONTRACT_TOKEN") or TEST_TOKEN


@pytest.fixture
def anon(base_url: str) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=base_url, timeout=10) as client:
        yield client


@pytest.fixture
def client(base_url: str, password: str) -> Iterator[httpx.Client]:
    """Cliente já logado por cookie, como o navegador."""
    with httpx.Client(base_url=base_url, timeout=10) as client:
        response = client.post("/api/login", json={"password": password})
        assert response.status_code == 200, response.text
        yield client
