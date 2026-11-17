import type { components, paths } from './schema'

type Schemas = components['schemas']
export type Health = Schemas['Health']
export type Task = Schemas['Task']
export type Priority = Schemas['Priority']

/** Erro de chamada à API, com uma mensagem pronta para mostrar à pessoa. */
export class ApiError extends Error {
  readonly status: number | null

  constructor(message: string, status: number | null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

const UNREACHABLE = 'Não foi possível falar com a API. Ela está rodando?'
// 502/503/504 vêm de um proxy (o do Vite em dev, ou outro na frente da API) quando a API está fora.
const GATEWAY_ERRORS = new Set([502, 503, 504])

type Fetch = typeof fetch

/** Chamado em toda resposta 401 (sessão expirou): o app volta para o login. */
let onUnauthorized: () => void = () => {}
export function setUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler
}

async function request(
  path: string,
  init: RequestInit,
  fetchImpl: Fetch,
): Promise<{ status: number; body: unknown }> {
  let response: Response
  try {
    response = await fetchImpl(path, {
      ...init,
      credentials: 'same-origin',
      headers: { accept: 'application/json', ...(init.body ? { 'content-type': 'application/json' } : {}) },
    })
  } catch {
    throw new ApiError(UNREACHABLE, null)
  }
  if (GATEWAY_ERRORS.has(response.status)) {
    throw new ApiError(UNREACHABLE, response.status)
  }
  let body: unknown = null
  try {
    body = await response.json()
  } catch {
    // corpo vazio ou não-JSON: tratado abaixo pelo status
  }
  if (!response.ok) {
    // Senha errada no login também é 401, mas não é "sessão expirou".
    if (response.status === 401 && path !== '/api/login' && path !== '/api/me') onUnauthorized()
    throw new ApiError(messageOf(body) ?? `A API respondeu com erro ${response.status}.`, response.status)
  }
  return { status: response.status, body }
}

function messageOf(body: unknown): string | null {
  if (typeof body === 'object' && body !== null && 'message' in body) {
    const { message } = body as { message: unknown }
    if (typeof message === 'string' && message) return message
  }
  return null
}

export async function getHealth(fetchImpl: Fetch = fetch): Promise<Health> {
  const { body } = await request('/api/health', { method: 'GET' }, fetchImpl)
  return body as Health
}

// --- Ações dos módulos: POST /api/{modulo}/{acao}, tipado a partir do schema gerado. ---

/** Caminhos de ação, como "/api/tarefas/add" (os de sessão não têm a segunda barra). */
type ActionPath = Extract<keyof paths, `/api/${string}/${string}`>
type Op<P extends ActionPath> = paths[P]['post']
export type ActionArgs<P extends ActionPath> = Op<P> extends {
  requestBody: { content: { 'application/json': infer B } }
}
  ? B
  : never
type ActionResponse<P extends ActionPath> = Op<P>['responses'][200]['content']['application/json']
export type ActionData<P extends ActionPath> = NonNullable<ActionResponse<P>['data']>

export type ActionResult<P extends ActionPath> = { message: string; data: ActionData<P> }

/** Chama uma ação. Devolve `message` (para pessoas) e `data` (para o app). */
export async function call<P extends ActionPath>(
  path: P,
  args: ActionArgs<P>,
  fetchImpl: Fetch = fetch,
): Promise<ActionResult<P>> {
  const { body } = await request(path, { method: 'POST', body: JSON.stringify(args) }, fetchImpl)
  const response = body as ActionResponse<P>
  return { message: response.message, data: response.data as ActionData<P> }
}

// --- Sessão ---

export async function login(password: string, fetchImpl: Fetch = fetch): Promise<void> {
  const args: Schemas['LoginArgs'] = { password }
  await request('/api/login', { method: 'POST', body: JSON.stringify(args) }, fetchImpl)
}

export async function logout(fetchImpl: Fetch = fetch): Promise<void> {
  await request('/api/logout', { method: 'POST' }, fetchImpl)
}

/** `true` se há sessão válida, `false` se a API respondeu 401. Outros erros sobem. */
export async function isLoggedIn(fetchImpl: Fetch = fetch): Promise<boolean> {
  try {
    await request('/api/me', { method: 'GET' }, fetchImpl)
    return true
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return false
    throw error
  }
}
