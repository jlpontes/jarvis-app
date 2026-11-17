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

Abra http://localhost:5173, entre com a senha do `.env` e você cai na tela **Tarefas**.
A documentação interativa da API fica em http://localhost:8000/docs.

O `make setup` também baixa o Chromium do Playwright (~150 MB), usado só pelo smoke test do
`make test`.

O `make setup` cria o `.env` a partir do `.env.example`. Em desenvolvimento a senha de login é
`troque-esta-senha`; troque tudo antes de usar de verdade (a API se recusa a subir em produção
com esses valores).

## Usando pelo terminal

```bash
cd server
uv run jarvis help
uv run jarvis tarefas add Comprar pão --due-date 2026-11-20 --priority alta
uv run jarvis tarefas listar            # pendentes; também: todas, hoje
uv run jarvis tarefas feito '#1'        # ou só 1 (no zsh, '#' precisa de aspas)
uv run jarvis tarefas editar 1 --due-date ""   # "" apaga o campo
uv run jarvis import-cpp-tasks          # copia, só lendo, as tarefas de ~/.jarvis/jarvis.db
```

O CLI usa o mesmo banco da API (`$JARVIS_DATA_DIR/jarvis.db`).

## Usando pelo `/docs`

1. Abra http://localhost:8000/docs.
2. Em **POST /api/login** → *Try it out* → `{"password": "troque-esta-senha"}` → *Execute*.
   O navegador guarda o cookie.
3. Use qualquer rota de **tarefas** do mesmo jeito.

## Comandos

| Comando | O que faz |
|---|---|
| `make dev` | API (:8000) + web (:5173) com reload. `Ctrl+C` para os dois |
| `make test` | pytest (unidade + contrato) + vitest + Playwright (smoke a 375 px, banco temporário) |
| `make contract` | só a suíte de contrato; contra outro servidor: `make contract URL=... PASSWORD=... TOKEN=...` |
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
| `JARVIS_TZ` | `America/Sao_Paulo` | fuso que define "hoje" e "atrasada" |
| `JARVIS_PASSWORD` | — | senha de login no navegador |
| `JARVIS_API_TOKEN` | — | `Authorization: Bearer ...` para outros clientes |
| `JARVIS_SECRET_KEY` | — | assina o cookie de sessão; trocar desloga todo mundo |
| `JARVIS_CPP_DB_PATH` | `~/.jarvis/jarvis.db` | origem do `import-cpp-tasks` |

O contrato HTTP completo está em `docs/contract.md`.
