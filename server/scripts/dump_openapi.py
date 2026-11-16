"""Escreve o OpenAPI da API em JSON, sem subir o servidor (usado por `make types`)."""

import json
import sys
from pathlib import Path

from jarvis.api.app import create_app
from jarvis.core.config import Environment, Settings


def main() -> None:
    out = Path(sys.argv[1])
    app = create_app(Settings(env=Environment.development))
    out.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
