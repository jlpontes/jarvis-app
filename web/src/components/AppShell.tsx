import { CheckSquare, LogOut, Sun, Wallet, type LucideIcon } from 'lucide-react'
import { Navigate, NavLink, Outlet, useLocation } from 'react-router'
import { Button } from '@/components/ui/button'
import { Logo } from '@/components/Logo'
import { ErrorState } from '@/components/StatusViews'
import { useLogout, useSession } from '@/features/auth/session'
import { cn } from '@/lib/utils'

const NAV: { to: string; label: string; icon: LucideIcon }[] = [
  { to: '/hoje', label: 'Hoje', icon: Sun },
  { to: '/tarefas', label: 'Tarefas', icon: CheckSquare },
  { to: '/financas', label: 'Finanças', icon: Wallet },
]

/** Só deixa passar com sessão; sem ela, vai para /login e volta depois. */
export function RequireAuth() {
  const session = useSession()
  const location = useLocation()

  if (session.isPending) {
    return <output aria-label="Carregando" className="block min-h-dvh" />
  }
  if (session.isError) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-sm flex-col justify-center px-4">
        <ErrorState message={session.error.message} onRetry={() => void session.refetch()} />
      </main>
    )
  }
  if (!session.data) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <AppShell />
}

function AppShell() {
  const logout = useLogout()

  return (
    <div className="min-h-dvh md:grid md:grid-cols-[14rem_1fr]">
      {/* Desktop: sidebar */}
      <aside className="sticky top-0 hidden h-dvh flex-col gap-6 border-r bg-sidebar px-3 py-5 md:flex">
        <div className="flex items-center gap-2.5 px-2">
          <Logo className="size-7 text-sm" />
          <span className="font-semibold tracking-tight">Jarvis</span>
        </div>
        <nav aria-label="Principal" className="flex flex-col gap-1">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  'flex h-10 items-center gap-3 rounded-[var(--radius)] px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground',
                  isActive && 'bg-sidebar-accent text-sidebar-accent-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                )
              }
            >
              <Icon className="size-[18px]" aria-hidden />
              {label}
            </NavLink>
          ))}
        </nav>
        <Button
          variant="ghost"
          className="mt-auto h-10 justify-start gap-3 px-3 text-muted-foreground"
          onClick={() => logout.mutate()}
        >
          <LogOut className="size-[18px]" aria-hidden />
          Sair
        </Button>
      </aside>

      <div className="flex min-w-0 flex-col">
        {/* Celular: cabeçalho fino com a marca e o "Sair" */}
        <header className="flex items-center justify-between px-4 pt-[max(0.75rem,env(safe-area-inset-top))] pb-1 md:hidden">
          <div className="flex items-center gap-2">
            <Logo className="size-6 text-xs" />
            <span className="text-sm font-semibold tracking-tight">Jarvis</span>
          </div>
          <Button variant="ghost" size="icon" className="size-10" aria-label="Sair" onClick={() => logout.mutate()}>
            <LogOut className="size-[18px]" aria-hidden />
          </Button>
        </header>

        <main className="mx-auto w-full max-w-[40rem] flex-1 px-4 pt-3 pb-[calc(5.5rem+env(safe-area-inset-bottom))] md:px-8 md:pt-10 md:pb-16">
          <Outlet />
        </main>
      </div>

      {/* Celular: navegação inferior */}
      <nav
        aria-label="Principal"
        className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-3 border-t bg-background/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden"
      >
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex h-16 flex-col items-center justify-center gap-1 text-xs font-medium text-muted-foreground',
                isActive && 'text-primary',
              )
            }
          >
            <Icon className="size-[22px]" aria-hidden />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
