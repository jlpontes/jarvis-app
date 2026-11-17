import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Logo } from '@/components/Logo'
import { useLogin, useSession } from './session'

export function LoginPage() {
  const session = useSession()
  const loginMutation = useLogin()
  const navigate = useNavigate()
  const location = useLocation()
  const [password, setPassword] = useState('')

  const from = (location.state as { from?: string } | null)?.from ?? '/tarefas'
  if (session.data === true) return <Navigate to={from} replace />

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (!password) return
    loginMutation.mutate(password, { onSuccess: () => navigate(from, { replace: true }) })
  }

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-sm flex-col justify-center gap-8 px-4 py-10">
      <div className="flex items-center gap-3">
        <Logo className="size-9" />
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Jarvis</h1>
          <p className="text-sm text-muted-foreground">Entre para ver suas tarefas.</p>
        </div>
      </div>
      <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
        <div className="flex flex-col gap-2">
          <Label htmlFor="password">Senha</Label>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            className="h-11"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            aria-invalid={loginMutation.isError || undefined}
            aria-describedby={loginMutation.isError ? 'login-error' : undefined}
          />
          {loginMutation.isError && (
            <p id="login-error" role="alert" className="text-sm text-destructive">
              {loginMutation.error.message}
            </p>
          )}
        </div>
        <Button type="submit" size="lg" className="h-11" disabled={!password || loginMutation.isPending}>
          {loginMutation.isPending ? 'Entrando…' : 'Entrar'}
        </Button>
      </form>
    </main>
  )
}
