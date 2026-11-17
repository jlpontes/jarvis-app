import type { components } from './schema'

export type Health = components['schemas']['Health']

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

export async function getHealth(fetchImpl: typeof fetch = fetch): Promise<Health> {
  let response: Response
  try {
    response = await fetchImpl('/api/health', { headers: { accept: 'application/json' } })
  } catch {
    throw new ApiError(UNREACHABLE, null)
  }
  if (GATEWAY_ERRORS.has(response.status)) {
    throw new ApiError(UNREACHABLE, response.status)
  }
  if (!response.ok) {
    throw new ApiError(`A API respondeu com erro ${response.status}.`, response.status)
  }
  return (await response.json()) as Health
}
