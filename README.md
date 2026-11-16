# Jarvis App

Versão "para usar hoje" do Jarvis: uma API em Python (FastAPI + SQLite) e um app web em
TypeScript (React + Vite), para um usuário só. A arquitetura espelha o projeto C++ do Jarvis
(core → módulos → clientes, `Command` → `Response`). Veja `docs/decisions/0001-python-ts-mvp.md`.

## Do zero no macOS

Pré-requisitos (uma vez só):

```bash
xcode-select --install          # git e make, se ainda não tiver
brew install uv node            # uv instala o Python certo sozinho (versão em server/.python-version)
```

Depois, dentro da pasta do projeto, são dois comandos:

```bash
make setup    # instala as dependências do Python e do Node
make dev      # API em http://localhost:8000 e web em http://localhost:5173
```

Abra http://localhost:5173. Você deve ver o cartão **Estado da API** com `API: ok · v0.1.0`.
A documentação interativa da API fica em http://localhost:8000/docs.

Opcional: `cp .env.example .env` para mudar a configuração (pasta de dados, fuso).

## Comandos

| Comando | O que faz |
|---|---|
| `make dev` | API (:8000) + web (:5173) com reload. `Ctrl+C` para os dois |
| `make test` | pytest + vitest |
| `make lint` | ruff, pyright, oxlint, `tsc` |
| `make format` | formata o Python com ruff |
| `make types` | regenera `web/src/api/schema.d.ts` a partir do OpenAPI da API |
| `make build` | compila o web em `web/dist` |
| `make start` | modo produção: API + web numa porta só (http://127.0.0.1:8000) |

Depois de mudar qualquer modelo ou rota da API, rode `make types` e faça commit do
`schema.d.ts`. O CI falha se o arquivo estiver desatualizado.

## Estrutura

```
server/   API em Python (uv, FastAPI, Pydantic). Código em server/src/jarvis/
web/      app web (Vite, React, TypeScript, Tailwind, shadcn/ui)
docs/     contrato HTTP, decisões (ADRs) e notas de cada milestone
```

## Configuração

Variáveis de ambiente (ou arquivo `.env` na raiz, que não vai para o Git):

| Variável | Padrão | Para quê |
|---|---|---|
| `JARVIS_ENV` | `development` | `production` faz a API servir também o web compilado |
| `JARVIS_DATA_DIR` | `~/.jarvis-app` | banco SQLite e backups |
| `JARVIS_TZ` | `America/Sao_Paulo` | fuso para exibir datas |

Senha, token e chave de sessão chegam no M1. Veja `.env.example`.
