# Contrato HTTP do Jarvis

Este arquivo é a fonte da verdade da API. O app web só conhece este contrato. Assim, o servidor
em Python pode ser trocado pelo servidor C++ (ou rodar ao lado dele) sem mexer no front.
Depois do M2, qualquer mudança aqui precisa do ok do João.

**Versão:** M0. Só `GET /api/health` está implementado. As outras rotas abaixo são o plano.

## Rotas

| Rota | Auth | Estado | Para quê |
|---|---|---|---|
| `GET /api/health` | não | ✅ M0 | `{status, version}` |
| `POST /api/login` · `POST /api/logout` · `GET /api/me` | login: não | M1 | sessão |
| `GET /api/modules` | sim | M1 | módulos, ações e o JSON Schema dos argumentos |
| `POST /api/{modulo}/{acao}` | sim | M1 | corpo = argumentos; resposta = `Response` |
| `POST /api/command` | sim | M4 | `{text, dry_run}` → `Command` interpretado + `Response` |
| `POST /api/assistant` | sim | M5 | assistente |

### `GET /api/health`

Sem autenticação. Sempre 200 quando a API está de pé.

```json
{ "status": "ok", "version": "0.1.0" }
```

## Formato de resposta das ações (a partir do M1)

```json
{ "ok": true, "message": "Tarefa #3 adicionada.", "data": { "...": "..." } }
```

- `message` é para pessoas (em português). `data` é para máquinas.
- **200** quando `ok=true`; **400** quando `ok=false` (erro de validação ou de domínio, com o corpo
  ainda no formato `Response`); **401** sem autenticação; **404** para módulo ou ação desconhecidos.

## Nomes

- Módulos e ações em português, como no C++: `tarefas`, `financas`, `add`, `listar`, `feito`,
  `reabrir`, `editar`, `remover`, `resumo`.
- Chaves JSON e valores de enum em inglês: `due_date`, `priority: "high"`.
- Datas como `YYYY-MM-DD`; timestamps em UTC (ISO 8601); dinheiro em centavos inteiros.

## Rotas fora de `/api`

Em produção (`JARVIS_ENV=production`), a mesma porta serve o app web compilado. Uma navegação
do navegador (`Accept: text/html`) para um caminho desconhecido recebe o `index.html` (SPA).
Um caminho desconhecido dentro de `/api` sempre responde **404 em JSON**.
