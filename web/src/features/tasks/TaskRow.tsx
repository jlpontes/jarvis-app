import { Checkbox } from '@/components/ui/checkbox'
import type { Priority, Task } from '@/api/client'
import { formatDue } from '@/lib/dates'
import { cn } from '@/lib/utils'
import { isTemp } from './useTasks'

const PRIORITY_LABEL: Record<Priority, string> = { high: 'Prioridade alta', medium: 'Prioridade média', low: 'Prioridade baixa' }

/** Alta = ponto cheio no acento; média = contorno; baixa = nada. */
function PriorityDot({ priority }: { priority: Priority }) {
  return (
    <span
      aria-hidden
      className={cn(
        'size-2 shrink-0 rounded-full',
        priority === 'high' && 'bg-primary',
        priority === 'medium' && 'border-[1.5px] border-muted-foreground/60',
        priority === 'low' && 'invisible',
      )}
    />
  )
}

type Props = {
  task: Task
  today: string
  onToggle: (task: Task) => void
  onOpen: (task: Task) => void
}

export function TaskRow({ task, today, onToggle, onOpen }: Props) {
  const pending = isTemp(task)
  const overdue = !task.done && task.due_date !== null && task.due_date < today

  return (
    <li className={cn('flex min-h-12 items-center', pending && 'opacity-60')}>
      {/* O ::after do checkbox estende a área de toque para 48 px */}
      <div className="grid size-12 shrink-0 place-items-center">
        <Checkbox
          checked={task.done}
          disabled={pending}
          onCheckedChange={() => onToggle(task)}
          className="size-5 rounded-full after:-inset-3.5"
          aria-label={task.done ? `Reabrir “${task.title}”` : `Concluir “${task.title}”`}
        />
      </div>
      <button
        type="button"
        disabled={pending}
        onClick={() => onOpen(task)}
        className="flex min-h-12 min-w-0 flex-1 items-center gap-3 rounded-md py-2 pr-2 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <span
          className={cn(
            'min-w-0 flex-1 text-sm break-words',
            task.done && 'text-muted-foreground line-through decoration-muted-foreground/50',
          )}
        >
          {task.title}
        </span>
        {task.due_date && (
          <span
            className={cn(
              'shrink-0 text-xs tabular-nums text-muted-foreground',
              overdue && 'font-medium text-destructive',
            )}
          >
            {formatDue(task.due_date, today)}
          </span>
        )}
        {!task.done && <PriorityDot priority={task.priority} />}
        <span className="sr-only">{PRIORITY_LABEL[task.priority]}</span>
      </button>
    </li>
  )
}
