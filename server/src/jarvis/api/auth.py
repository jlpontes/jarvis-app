"""Login de um usuário só: cookie de sessão assinado (navegador) ou Bearer token (outros clientes).

O cookie guarda só o instante do login, assinado com HMAC-SHA256 e JARVIS_SECRET_KEY. Ninguém
consegue forjar sem a chave. Trocar a chave desloga todo mundo.
"""

import base64
import hashlib
import hmac
import threading
import time
from collections import deque
from collections.abc import Callable
from typing import Literal

from fastapi import Request
from fastapi import Response as HttpResponse

from jarvis.api.errors import ApiError
from jarvis.core.config import Environment, Settings

COOKIE_NAME = "jarvis_session"
SESSION_SECONDS = 30 * 24 * 3600  # 30 dias
RENEW_AFTER_SECONDS = 24 * 3600  # renova o cookie no máximo uma vez por dia
MAX_FAILURES = 5
FAILURE_WINDOW_SECONDS = 15 * 60

type AuthMethod = Literal["session", "token"]


def _equal(a: str, b: str) -> bool:
    """Comparação em tempo constante (não vaza, pelo tempo, quantos caracteres batem)."""
    return hmac.compare_digest(a.encode(), b.encode())


class SessionSigner:
    def __init__(self, secret_key: str) -> None:
        self._key = secret_key.encode()

    def _signature(self, issued_at: int) -> str:
        digest = hmac.new(self._key, f"jarvis-session:{issued_at}".encode(), hashlib.sha256)
        return base64.urlsafe_b64encode(digest.digest()).decode().rstrip("=")

    def sign(self, issued_at: int) -> str:
        return f"{issued_at}.{self._signature(issued_at)}"

    def issued_at(self, cookie: str, now: int) -> int | None:
        """Instante do login se o cookie é válido e não expirou; senão None."""
        issued_text, _, signature = cookie.partition(".")
        if not issued_text.isascii() or not issued_text.isdigit():
            return None
        issued_at = int(issued_text)
        if not _equal(signature, self._signature(issued_at)):
            return None
        if not (0 <= now - issued_at < SESSION_SECONDS):
            return None
        return issued_at


class LoginLimiter:
    """No máximo MAX_FAILURES tentativas erradas por IP a cada FAILURE_WINDOW_SECONDS."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._failures: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._clock = clock

    def _recent(self, ip: str) -> deque[float]:
        now = self._clock()
        failures = self._failures.setdefault(ip, deque())
        while failures and now - failures[0] >= FAILURE_WINDOW_SECONDS:
            failures.popleft()
        return failures

    def retry_after(self, ip: str) -> int | None:
        """Segundos até poder tentar de novo, ou None se pode tentar agora."""
        with self._lock:
            failures = self._recent(ip)
            if len(failures) < MAX_FAILURES:
                return None
            return int(FAILURE_WINDOW_SECONDS - (self._clock() - failures[0])) + 1

    def fail(self, ip: str) -> None:
        with self._lock:
            self._recent(ip).append(self._clock())

    def reset(self, ip: str) -> None:
        with self._lock:
            self._failures.pop(ip, None)


class Auth:
    def __init__(self, settings: Settings, clock: Callable[[], float] = time.time) -> None:
        self._password = settings.password.get_secret_value() if settings.password else ""
        self._token = settings.api_token.get_secret_value() if settings.api_token else ""
        secret_key = settings.secret_key.get_secret_value() if settings.secret_key else ""
        # Sem chave (só em dev mal configurado): nenhuma sessão é válida.
        self._signer = SessionSigner(secret_key) if secret_key else None
        self._secure = settings.env is Environment.production
        self._clock = clock
        self.limiter = LoginLimiter()

    def _now(self) -> int:
        return int(self._clock())

    def check_password(self, password: str) -> bool:
        return bool(self._password) and _equal(password, self._password)

    def start_session(self, response: HttpResponse) -> None:
        if self._signer is None:
            raise ApiError(500, "JARVIS_SECRET_KEY não está configurada no servidor.")
        response.set_cookie(
            COOKIE_NAME,
            self._signer.sign(self._now()),
            max_age=SESSION_SECONDS,
            httponly=True,
            samesite="lax",
            secure=self._secure,
            path="/",
        )

    def end_session(self, response: HttpResponse) -> None:
        response.delete_cookie(
            COOKIE_NAME, httponly=True, samesite="lax", secure=self._secure, path="/"
        )

    def authenticate(self, request: Request, response: HttpResponse) -> AuthMethod:
        """Dependência das rotas protegidas: devolve como a pessoa entrou, ou 401."""
        header = request.headers.get("authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() == "bearer" and token:
            if self._token and _equal(token.strip(), self._token):
                return "token"
            raise ApiError(401, "Token inválido.", {"WWW-Authenticate": "Bearer"})

        cookie = request.cookies.get(COOKIE_NAME)
        if cookie and self._signer is not None:
            issued_at = self._signer.issued_at(cookie, self._now())
            if issued_at is not None:
                if self._now() - issued_at >= RENEW_AFTER_SECONDS:
                    self.start_session(response)  # renova: mais 30 dias a partir de agora
                return "session"
        raise ApiError(401, "Faça login para continuar.")
