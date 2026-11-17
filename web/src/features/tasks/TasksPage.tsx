import { ChevronRight } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { Task } from '@/api/client'
import { EmptyState, ErrorState, LoadingRows } from '@/components/StatusViews'
import { useToast } from '@/components/Toast'
import { groupTasks, todayISO } from '@/lib/dates'
import { cn } from '@/lib/utils'
import { QuickAdd } from './QuickAdd'
import { TaskRow } from './TaskRow'
import { TaskSheet, type TaskChanges } from './TaskSheet'
import {
  useCompleteTask,
  useEditTask,
  useRemoveTask,
  useReopenTask,
  useTasks,
} from './useTasks'

export function TasksPage() {
  const tasks = useTasks()
  const complete = useCompleteTask()
  const reopen = useReopenTask()
  const edit = useEditTask()
  const remove = useRemoveTask()
  const toast = useToast()
  const [editingId, setEditingId] = useState<number | null>(null)
  const [showDone, setShowDone] = useState(false)

  const today = todayISO()
  const groups = useMemo(() => groupTasks(tasks.data ?? [], today), [tasks.data, today])
  const editing = tasks.data?.find((t) => t.id === editingId) ?? null

  const toggle = (task: Task) => {
    if (task.done) {
      reopen.mutate(task)
      return
    }
    complete.mutate(task)
    toast({
      message: `Concluída: ${task.title}`,
      action: { label: 'Desfazer', onClick: () => reopen.mutate(task) },
    })
  }

  const save = (task: Task, changes: TaskChanges) => {
    setEditingId(null)
    if (Object.keys(changes).length > 0) edit.mutate({ id: task.id, ...changes })
  }

  const removeTask = (task: Task) => {
    setEditingId(null)
    remove.mutate(task, { onSuccess: () => toast({ message: 'Tarefa removida.' }) })
  }

  const pendingCount = groups.overdue.length + groups.today.length + groups.upcoming.length + groups.noDate.length
  const rowProps = { today, onToggle: toggle, onOpen: (t: Task) => setEditingId(t.id) }

  return (
    <section className="flex flex-col gap-6">
      <header className="flex items-baseline justify-between gap-4">
        <h1 className="text-xl font-semibold tracking-tight">Tarefas</h1>
        {tasks.data && (
          <p className="text-sm text-muted-foreground tabular-nums">
            {pendingCount === 1 ? '1 pendente' : `${pendingCount} pendentes`}
          </p>
        )}
      </header>

      <QuickAdd />

      {tasks.isPending && <LoadingRows />}
      {tasks.isError && <ErrorState message={tasks.error.message} onRetry={() => void tasks.refetch()} />}

      {tasks.data && (
        <div className="flex flex-col gap-6">
          {pendingCount === 0 && (
            <EmptyState title="Nada pendente.">
              Digite algo como “Comprar pão” na caixa acima e aperte Enter.
            </EmptyState>
          )}
          <Group title="Atrasadas" tone="danger" tasks={groups.overdue} {...rowProps} />
          <Group title="Hoje" tasks={groups.today} {...rowProps} />
          <Group title="Próximas" tasks={groups.upcoming} {...rowProps} />
          <Group title="Sem prazo" tasks={groups.noDate} {...rowProps} />

          {groups.done.length > 0 && (
            <div>
              <button
                type="button"
                aria-expanded={showDone}
                aria-controls="done-list"
                onClick={() => setShowDone((v) => !v)}
                className="flex h-10 items-center gap-1 rounded-md text-xs font-semibold tracking-wider text-muted-foreground uppercase hover:text-foreground"
              >
                <ChevronRight className={cn('size-4 transition-transform', showDone && 'rotate-90')} aria-hidden />
                Concluídas · {groups.done.length}
              </button>
              {showDone && (
                <ul id="done-list" className="divide-y rounded-[var(--radius)] border bg-card">
                  {groups.done.map((task) => (
                    <TaskRow key={task.id} task={task} {...rowProps} />
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}

      <TaskSheet task={editing} onClose={() => setEditingId(null)} onSave={save} onRemove={removeTask} />
    </section>
  )
}

type GroupProps = {
  title: string
  tone?: 'danger'
  tasks: Task[]
  today: string
  onToggle: (task: Task) => void
  onOpen: (task: Task) => void
}

function Group({ title, tone, tasks, ...rowProps }: GroupProps) {
  if (tasks.length === 0) return null
  const id = `group-${title}`
  return (
    <div>
      <h2
        id={id}
        className={cn(
          'mb-2 text-xs font-semibold tracking-wider uppercase',
          tone === 'danger' ? 'text-destructive' : 'text-muted-foreground',
        )}
      >
        {title} · {tasks.length}
      </h2>
      <ul aria-labelledby={id} className="divide-y rounded-[var(--radius)] border bg-card">
        {tasks.map((task) => (
          <TaskRow key={task.id} task={task} {...rowProps} />
        ))}
      </ul>
    </div>
  )
}
