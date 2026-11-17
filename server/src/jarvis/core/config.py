"""Configuração lida das variáveis de ambiente (prefixo JARVIS_) e do arquivo .env."""

from enum import StrEnum
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]

# Valores de exemplo do .env.example: servem só em desenvolvimento.
EXAMPLE_SECRETS = frozenset({"troque-esta-senha", "troque-este-token", "troque-esta-chave"})
MIN_SECRET_LENGTH = 16


class Environment(StrEnum):
    development = "development"
    production = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="JARVIS_",
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Environment = Environment.development
    data_dir: Path = Path.home() / ".jarvis-app"
    tz: str = "America/Sao_Paulo"
    web_dir: Path = REPO_ROOT / "web" / "dist"

    password: SecretStr | None = None
    api_token: SecretStr | None = None
    secret_key: SecretStr | None = None

    # Banco do Jarvis em C++, lido (só leitura) por `jarvis import-cpp-tasks`.
    cpp_db_path: Path = Path.home() / ".jarvis" / "jarvis.db"

    @field_validator("data_dir", "web_dir", "cpp_db_path")
    @classmethod
    def expand_home(cls, value: Path) -> Path:
        """Aceita `~/...` no .env, como no shell."""
        return value.expanduser()

    @field_validator("tz")
    @classmethod
    def known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"fuso horário desconhecido: {value}") from exc
        return value

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.tz)

    @property
    def db_path(self) -> Path:
        return self.data_dir / "jarvis.db"

    def secret_problems(self) -> list[str]:
        """O que impede subir em produção: segredo ausente, de exemplo ou curto demais."""
        problems: list[str] = []
        for name in ("password", "api_token", "secret_key"):
            secret: SecretStr | None = getattr(self, name)
            env_name = f"JARVIS_{name.upper()}"
            if secret is None or not secret.get_secret_value():
                problems.append(f"{env_name} não foi definido")
            elif secret.get_secret_value() in EXAMPLE_SECRETS:
                problems.append(f"{env_name} ainda tem o valor de exemplo do .env.example")
            elif len(secret.get_secret_value()) < MIN_SECRET_LENGTH:
                problems.append(f"{env_name} precisa de pelo menos {MIN_SECRET_LENGTH} caracteres")
        return problems


def get_settings() -> Settings:
    return Settings()
