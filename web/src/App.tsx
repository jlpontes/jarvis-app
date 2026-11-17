import { useCallback, useEffect, useState } from 'react'
import { getHealth, type Health } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

type State =
  | { kind: 'loading' }
  | { kind: 'ok'; health: Health }
  | { kind: 'error'; message: string }

export default function App() {
  const [state, setState] = useState<State>({ kind: 'loading' })

  // Só chama setState quando a resposta chega (assíncrono), nunca direto no efeito.
  const load = useCallback(() => {
    getHealth()
      .then((health) => setState({ kind: 'ok', health }))
      .catch((error: unknown) =>
        setState({
          kind: 'error',
          message: error instanceof Error ? error.message : 'Erro inesperado.',
        }),
      )
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const retry = () => {
    setState({ kind: 'loading' })
    load()
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center gap-6 p-4">
      <h1 className="text-2xl font-semibold tracking-tight">Jarvis</h1>
      <Card>
        <CardHeader>
          <CardTitle>Estado da API</CardTitle>
          <CardDescription>GET /api/health</CardDescription>
        </CardHeader>
        <CardContent aria-live="polite" className="flex items-center justify-between gap-4">
          {state.kind === 'loading' && <p className="text-muted-foreground">Verificando…</p>}
          {state.kind === 'ok' && (
            <p>
              <span className="mr-2 inline-block size-2.5 rounded-full bg-emerald-500" aria-hidden />
              API: {state.health.status} · v{state.health.version}
            </p>
          )}
          {state.kind === 'error' && (
            <>
              <p className="text-destructive">{state.message}</p>
              <Button variant="outline" onClick={retry}>
                Tentar de novo
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </main>
  )
}
