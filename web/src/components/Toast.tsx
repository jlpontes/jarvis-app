import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

/**
 * Um aviso por vez, embaixo da tela, com uma ação opcional ("Desfazer").
 * Pequeno de propósito: substitui o `sonner` sem trazer dependência nova.
 */
type ToastInput = {
  message: string
  tone?: 'default' | 'error'
  action?: { label: string; onClick: () => void }
  durationMs?: number
}
type ToastState = ToastInput & { id: number }

const ToastContext = createContext<(toast: ToastInput) => void>(() => {})

export function useToast(): (toast: ToastInput) => void {
  return useContext(ToastContext)
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<ToastState | null>(null)
  const nextId = useRef(0)

  const show = useCallback((input: ToastInput) => {
    nextId.current += 1
    setToast({ ...input, id: nextId.current })
  }, [])

  useEffect(() => {
    if (!toast) return
    const timer = window.setTimeout(() => setToast(null), toast.durationMs ?? 5000)
    return () => window.clearTimeout(timer)
  }, [toast])

  return (
    <ToastContext.Provider value={show}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 bottom-[calc(4.5rem+env(safe-area-inset-bottom))] z-50 flex justify-center px-4 md:bottom-6"
      >
        {toast && (
          <div
            key={toast.id}
            className={cn(
              'pointer-events-auto flex w-full max-w-sm items-center gap-3 rounded-[var(--radius)] px-4 py-3 text-sm shadow-lg animate-in fade-in-0 slide-in-from-bottom-2',
              toast.tone === 'error'
                ? 'bg-destructive text-white'
                : 'bg-foreground text-background',
            )}
          >
            <span className="min-w-0 flex-1">{toast.message}</span>
            {toast.action && (
              <button
                type="button"
                className="-my-2 -mr-2 shrink-0 rounded-md px-2 py-2 font-semibold underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-current"
                onClick={() => {
                  toast.action?.onClick()
                  setToast(null)
                }}
              >
                {toast.action.label}
              </button>
            )}
          </div>
        )}
      </div>
    </ToastContext.Provider>
  )
}
