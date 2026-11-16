import { describe, expect, it } from 'vitest'
import { ApiError, getHealth } from './client'

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
