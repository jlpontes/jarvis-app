# Contrato HTTP do Jarvis

Este arquivo é a fonte da verdade da API. O app web só conhece este contrato. Assim, o servidor
em Python pode ser trocado pelo servidor C++ (ou rodar ao lado dele) sem mexer no front.
Depois do M2, qualquer mudança aqui precisa do ok do João.

**Versão:** M1. A suíte `server/tests/contract/` verifica este contrato por HTTP contra qualquer
servidor: `make contract URL=http://... PASSWORD=... TOKEN=...`.

## Rotas

| Rota | Auth | Estado | Para quê |
|---|---|---|---|
| `GET /api/health` | não | ✅ M0 | `{status, version}` (único corpo fora do formato `Response`) |
| `POST /api/login` | não | ✅ M1 | `{password}` → cookie de sessão |
| `POST /api/logout` | não | ✅ M1 | apaga o cookie |
| `GET /api/me` | sim | ✅ M1 | `data: {method: "session" \| "token"}` |
| `GET /api/modules` | sim | ✅ M1 | módulos, ações e o JSON Schema de argumentos e resultado |
| `POST /api/{modulo}/{acao}` | sim | ✅ M1 | corpo = argumentos; resposta = `Response` |
| `POST /api/command` | sim | M4 | `{text, dry_run}` → `Command` interpretado + `Response` |
| `POST /api/assistant` | sim | M5 | assistente |

## Formato `Response`

Toda resposta em `/api` (menos `health`), de sucesso **ou de erro**:

```json
{ "ok": true, "message": "Tarefa #3 adicionada: Comprar pão", "data": { "id": 3, "...": "..." } }
```

- `message` é para pessoas (em português). `data` é para máquinas; `null` em todo erro.

| Status | Quando | `ok` |
|---|---|---|
| 200 | deu certo | `true` |
| 400 | entrada inválida (JSON, campo faltando, tipo errado) ou erro de regra ("Tarefa #9 não encontrada") | `false` |
| 401 | sem login, cookie inválido ou expirado, token errado, senha errada no login | `false` |
| 404 | módulo, ação ou rota desconhecidos | `false` |
| 429 | login: 5 senhas erradas em 15 min pelo mesmo IP. Cabeçalho `Retry-After` em segundos | `false` |
| 500 | erro inesperado no servidor (detalhes só no log) | `false` |

A API **nunca** responde 422: erros de validação também vêm como 400 + `Response`.

## Autenticação

- **Navegador:** `POST /api/login {"password": "..."}` grava o cookie `jarvis_session`
  (`HttpOnly`, `SameSite=Lax`, `Secure` em produção, `Path=/`). Ele vale 30 dias e é renovado com
  o uso (no máximo uma vez por dia, a resposta traz um `Set-Cookie` novo).
- **Outros clientes:** cabeçalho `Authorization: Bearer <JARVIS_API_TOKEN>`.
- Sem autenticação: `health`, `login`, `logout`. Todo o resto exige login. A checagem de login
  vem antes da validação do corpo: sem login, a resposta é sempre 401.

## Nomes

- Módulos e ações em português, como no C++: `tarefas`, `add`, `listar`, `feito`, `reabrir`,
  `editar`, `remover`.
- Chaves JSON e valores de enum em inglês: `due_date`, `priority: "high"`.
- Datas como `YYYY-MM-DD`; timestamps em UTC, ISO 8601 com `Z` (`2026-11-17T15:00:00Z`).

## Módulo `tarefas`

`Task`:

```json
{
  "id": 3,
  "title": "Comprar pão",
  "due_date": "2026-11-20",
  "priority": "high",
  "done": false,
  "created_at": "2026-11-17T15:00:00Z",
  "done_at": null
}
```

`priority` ∈ `low | medium | high`; `due_date` e `done_at` podem ser `null`.

| Ação | Corpo | `data` |
|---|---|---|
| `add` | `{title, due_date?, priority? = "medium"}` | `Task` |
| `listar` | `{filter? = "pending"}`, `filter` ∈ `pending \| all \| today` | `Task[]` |
| `feito` | `{id}` | `Task` (concluída) |
| `reabrir` | `{id}` | `Task` (pendente) |
| `editar` | `{id, title?, due_date?, priority?}` | `Task` (atualizada) |
| `remover` | `{id}` | `Task` (como estava antes de apagar) |

Regras:

- `id` aceita número (`3`) ou texto (`"3"`, `"#3"`). Qualquer outra coisa (`"abc"`, `"3abc"`,
  `-1`, `0`) é 400.
- `title` não pode ficar vazio (os espaços das pontas são removidos), no máximo 500 caracteres.
- Entrada também aceita apelidos em português: `priority` `baixa | média | alta` e `filter`
  `pendentes | todas | hoje`. A saída é sempre em inglês.
- Campos desconhecidos no corpo são 400.
- `listar`, ordem: pendentes antes de concluídas; atrasadas primeiro; prioridade alta → baixa;
  prazo mais próximo (sem prazo por último); id. `today` = pendentes com prazo até hoje
  (atrasadas e de hoje). "Hoje" é calculado no fuso `JARVIS_TZ`.
- `editar` muda só os campos enviados. `"due_date": null` apaga o prazo; corpo só com `id` é 400.
- `feito` numa tarefa concluída e `reabrir` numa pendente são 400.

## Rotas fora de `/api`

Em produção (`JARVIS_ENV=production`), a mesma porta serve o app web compilado. Uma navegação
do navegador (`Accept: text/html`) para um caminho desconhecido recebe o `index.html` (SPA).
Um caminho desconhecido dentro de `/api` sempre responde **404 em JSON**.
