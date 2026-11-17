# 0001: MVP em Python + TypeScript, ao lado do Jarvis em C++

- **Data:** 2026-11-16
- **Status:** aceita

## Contexto

O Jarvis em C++20 (`../Jarvis`) é a trilha de aprendizado do João e ainda vai demorar para virar
algo usado no dia a dia. O João quer um Jarvis para usar **hoje**, no celular e no Mac.

## Decisão

Criar uma segunda implementação da **mesma arquitetura**, com um stack mais rápido de entregar:
uma API em Python (FastAPI + SQLite) e um app web em TypeScript (React + Vite, instalável como PWA).
O projeto C++ não é modificado por este projeto.

| Jarvis em C++ | Este app |
|---|---|
| `Command {module, action, args}` → `Response {ok, message, data}` | Os mesmos formatos, como modelos Pydantic |
| `IModule`: `name()`, `actions()`, `init(db)`, `handle()` | O mesmo contrato, em Python |
| `ModuleRegistry::dispatch` | O mesmo |
| `schema_migrations(module, version)` + SQL no código | A mesma tabela e a mesma regra: nunca editar uma migração publicada |
| Regra `apps → modules → core` | Regra `api / cli / assistant → modules → core` |
| `POST /api/{modulo}/{acao}` planejado | Implementado aqui, com exatamente esse formato de rota |

## Consequências

- O **contrato HTTP** (`docs/contract.md`) é a costura entre as duas implementações. O web só conhece
  o contrato, então o servidor C++ pode substituir o Python depois sem mexer no front, e
  Telegram, um app Qt ou um app nativo entram como novos clientes da mesma API.
- **Dados separados:** este app usa `~/.jarvis-app/jarvis.db` e nunca escreve em `~/.jarvis/jarvis.db`.
  No M1 haverá uma importação única, só leitura, das tarefas existentes.
- Há duas bases de código para manter. Os testes de contrato (M1) aceitam a URL base como
  parâmetro para poder verificar as duas.
