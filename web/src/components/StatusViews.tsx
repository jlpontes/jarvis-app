import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'

/** Estados de lista padronizados: carregando, erro com "Tentar de novo" e vazio. */

export function LoadingRows({ rows = 4, label = 'Carregando…' }: { rows?: number; label?: string }) {
  return (
    <output aria-label={label} className="flex flex-col gap-2 py-2">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="h-12 animate-pulse rounded-[var(--radius)] bg-muted" />
      ))}
    </output>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-start gap-3 rounded-[var(--radius)] border border-destructive/30 p-4">
      <p className="text-sm text-destructive">{message}</p>
      <Button variant="outline" onClick={onRetry}>
        Tentar de novo
      </Button>
    </div>
  )
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col gap-1 rounded-[var(--radius)] border border-dashed p-6 text-center">
      <p className="font-medium">{title}</p>
      {children && <p className="text-sm text-muted-foreground">{children}</p>}
    </div>
  )
}
