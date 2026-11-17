import { cn } from '@/lib/utils'

/** Marca do Jarvis: um "J" sobre o acento. */
export function Logo({ className }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={cn(
        'inline-grid shrink-0 place-items-center rounded-[var(--radius)] bg-primary font-semibold text-primary-foreground',
        className,
      )}
    >
      J
    </span>
  )
}
