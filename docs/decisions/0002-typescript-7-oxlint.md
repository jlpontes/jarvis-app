# 0002: TypeScript 7 + oxlint no web, com o gerador de tipos isolado

- **Data:** 2026-11-16
- **Status:** aceita (escolha do João no M0)

## Contexto

O plano previa ESLint. O template atual do Vite (`create vite`, react-ts) já vem com
**TypeScript 7** (o compilador reescrito em Go, bem mais rápido) e **oxlint** no lugar do ESLint.
Duas incompatibilidades apareceram:

- O `typescript-eslint` 8.73 só aceita TypeScript até a 6.0.
- O `openapi-typescript` 7.13 usa a API JavaScript do compilador (`ts.factory`), que **não existe**
  no TS 7. Testado: ele quebra com `Cannot read properties of undefined (reading 'createKeywordTypeNode')`.

## Decisão

- O web usa TypeScript 7 e oxlint (`web/.oxlintrc.json`, com `no-explicit-any` como erro).
- O `openapi-typescript` mora num pacote separado, `web/tools/openapi/`, com o próprio TypeScript 5
  e o próprio lockfile. `make types` chama o gerador de lá. Ele só *gera* o `schema.d.ts`; quem
  checa os tipos do projeto continua sendo o TS 7.

## Consequências

- Lint e checagem de tipos ficam muito rápidos.
- O oxlint ainda não roda regras que dependem de tipos (como `no-floating-promises`) sem um
  plugin extra. Se isso fizer falta, reavaliamos.
- Quando o `openapi-typescript` suportar o TS 7, dá para apagar `web/tools/openapi/` e instalá-lo direto no web.
