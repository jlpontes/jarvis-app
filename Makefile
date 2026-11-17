# Jarvis App: atalhos do dia a dia. Rode `make help` para ver a lista.
.DEFAULT_GOAL := help
SHELL := /bin/bash
HOST ?= 127.0.0.1
PORT ?= 8000

.PHONY: help setup dev test lint format types types-check build start clean

help: ## Mostra esta ajuda
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-12s %s\n", $$1, $$2}'

setup: ## Instala as dependências (Python e Node)
	cd server && uv sync
	cd web && npm ci
	cd web/tools/openapi && npm ci

dev: ## API em :8000 e web em :5173, com reload (Ctrl+C para os dois)
	@trap 'kill 0' INT TERM EXIT; \
	(cd server && uv run uvicorn jarvis.api.main:app --reload --host 127.0.0.1 --port 8000) & \
	(cd web && npm run dev) & \
	wait

test: ## pytest + vitest
	cd server && uv run pytest
	cd web && npm test

lint: ## ruff, pyright, oxlint, tsc
	cd server && uv run ruff check . && uv run ruff format --check . && uv run pyright
	cd web && npm run lint && npm run typecheck

format: ## Formata o código Python
	cd server && uv run ruff format . && uv run ruff check --fix .

types: ## Regenera web/src/api/schema.d.ts a partir do OpenAPI da API
	cd server && uv run python scripts/dump_openapi.py ../web/tools/openapi/openapi.json
	cd web/tools/openapi && ./node_modules/.bin/openapi-typescript openapi.json -o ../../src/api/schema.d.ts

types-check: types ## Falha se os tipos gerados estiverem desatualizados (usado no CI)
	@git diff --exit-code -- web/src/api/schema.d.ts || \
	  (echo "schema.d.ts desatualizado: rode 'make types' e faça commit." && exit 1)

build: ## Compila o web em web/dist (a pasta que a API serve)
	cd web && npm run build

start: build ## Modo produção: API + web numa porta só (http://$(HOST):$(PORT))
	cd server && JARVIS_ENV=production uv run uvicorn jarvis.api.main:app --host $(HOST) --port $(PORT)

clean: ## Remove builds e caches
	rm -rf web/dist web/node_modules/.tmp server/.pytest_cache server/.ruff_cache
