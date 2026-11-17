import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, call, getHealth, isLoggedIn, login, setUnauthorizedHandler } from './client'

function fakeFetch(response: Response | Error): typeof fetch {
  return () => (response instanceof Error ? Promise.reject(response) : Promise.resolve(response))
}

describe('getHealth', () => {
  it('retorna o status e a versão', async () => {
    const body = JSON.stringify({ status: 'ok', version: '0.1.0' })
    const health = await getHealth(fakeFetch(new Response(body, { status: 200 })))
    expect(health).toEqual({ status: 'ok', version: '0.1.0' })
  })

  it('explica quando a API está fora do ar', async () => {
    const promise = getHealth(fakeFetch(new TypeError('Failed to fetch')))
    await expect(promise).rejects.toThrow('Não foi possível falar com a API')
  })

  it('trata erro de proxy (502) como API fora do ar', async () => {
    const promise = getHealth(fakeFetch(new Response('', { status: 502 })))
    await expect(promise).rejects.toThrow('Não foi possível falar com a API')
    await expect(promise).rejects.toMatchObject({ status: 502 })
  })

  it('leva o status HTTP nos outros erros', async () => {
    const promise = getHealth(fakeFetch(new Response('', { status: 500 })))
    await expect(promise).rejects.toBeInstanceOf(ApiError)
    await expect(promise).rejects.toMatchObject({ status: 500 })
  })
})

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } })

describe('call', () => {
  afterEach(() => setUnauthorizedHandler(() => {}))

  it('manda os argumentos como JSON e devolve message e data', async () => {
    const task = { id: 3, title: 'Comprar pão' }
    const fetchImpl = vi.fn<typeof fetch>(() =>
      Promise.resolve(json(200, { ok: true, message: 'Tarefa #3 adicionada', data: task })),
    )
    const result = await call('/api/tarefas/add', { title: 'Comprar pão', priority: 'high' }, fetchImpl)
    expect(result).toEqual({ message: 'Tarefa #3 adicionada', data: task })
    const [url, init] = fetchImpl.mock.calls[0]
    expect(url).toBe('/api/tarefas/add')
    expect(init?.method).toBe('POST')
    expect(JSON.parse(String(init?.body))).toEqual({ title: 'Comprar pão', priority: 'high' })
  })

  it('usa a message do servidor nos erros (400)', async () => {
    const fetchImpl = fakeFetch(json(400, { ok: false, message: 'Tarefa #9 não encontrada', data: null }))
    const promise = call('/api/tarefas/feito', { id: 9 }, fetchImpl)
    await expect(promise).rejects.toThrow('Tarefa #9 não encontrada')
    await expect(promise).rejects.toMatchObject({ status: 400 })
  })

  it('avisa o app quando a sessão expira (401)', async () => {
    const handler = vi.fn<() => void>()
    setUnauthorizedHandler(handler)
    const fetchImpl = fakeFetch(json(401, { ok: false, message: 'Faça login para continuar.', data: null }))
    await expect(call('/api/tarefas/listar', { filter: 'all' }, fetchImpl)).rejects.toThrow('Faça login')
    expect(handler).toHaveBeenCalledOnce()
  })
})

describe('sessão', () => {
  afterEach(() => setUnauthorizedHandler(() => {}))

  it('senha errada não conta como sessão expirada', async () => {
    const handler = vi.fn<() => void>()
    setUnauthorizedHandler(handler)
    const fetchImpl = fakeFetch(json(401, { ok: false, message: 'Senha incorreta.', data: null }))
    await expect(login('x', fetchImpl)).rejects.toThrow('Senha incorreta.')
    expect(handler).not.toHaveBeenCalled()
  })

  it('isLoggedIn: true com sessão, false com 401', async () => {
    expect(await isLoggedIn(fakeFetch(json(200, { ok: true, message: '', data: { method: 'session' } })))).toBe(true)
    expect(await isLoggedIn(fakeFetch(json(401, { ok: false, message: 'x', data: null })))).toBe(false)
  })

  it('isLoggedIn: API fora do ar é erro, não "sem login"', async () => {
    await expect(isLoggedIn(fakeFetch(new TypeError('Failed to fetch')))).rejects.toBeInstanceOf(ApiError)
  })
})
