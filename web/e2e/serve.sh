#!/usr/bin/env bash
# Sobe a API em modo produção (servindo o web compilado) com um banco temporário.
# Usado só pelo Playwright: nunca toca ~/.jarvis-app.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
data_dir="$(mktemp -d "${TMPDIR:-/tmp}/jarvis-e2e.XXXXXX")"
trap 'rm -rf "$data_dir"' EXIT

cd "$here/.."
npm run build >/dev/null

cd "$here/../../server"
export JARVIS_ENV=production
export JARVIS_DATA_DIR="$data_dir"
export JARVIS_PASSWORD="senha-do-teste-e2e"
export JARVIS_API_TOKEN="token-do-teste-e2e-123"
export JARVIS_SECRET_KEY="chave-do-teste-e2e-123"
uv run uvicorn jarvis.api.main:app --host 127.0.0.1 --port "${E2E_PORT:-8765}"
