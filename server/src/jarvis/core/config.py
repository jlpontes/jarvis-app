"""Configuração lida das variáveis de ambiente (prefixo JARVIS_) e do arquivo .env."""

from enum import StrEnum
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


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

    @field_validator("data_dir", "web_dir")
    @classmethod
    def expand_home(cls, value: Path) -> Path:
        """Aceita `~/...` no .env, como no shell."""
        return value.expanduser()


def get_settings() -> Settings:
    return Settings()
