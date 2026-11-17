import { useState, type FormEvent } from 'react'
import { Trash2 } from 'lucide-react'
import type { Priority, Task } from '@/api/client'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { addDays, todayISO } from '@/lib/dates'
import { cn } from '@/lib/utils'
import { useMediaQuery } from '@/lib/useMediaQuery'

const PRIORITIES: { value: Priority; label: string }[] = [
  { value: 'low', label: 'Baixa' },
  { value: 'medium', label: 'Média' },
  { value: 'high', label: 'Alta' },
]

export type TaskChanges = { title?: string; due_date?: string | null; priority?: Priority }

type Props = {
  task: Task | null
  onClose: () => void
  onSave: (task: Task, changes: TaskChanges) => void
  onRemove: (task: Task) => void
}

/** Editar uma tarefa: de baixo no celular, da direita no desktop. */
export function TaskSheet({ task, onClose, onSave, onRemove }: Props) {
  const desktop = useMediaQuery('(min-width: 768px)')
  return (
    <Sheet open={task !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent
        side={desktop ? 'right' : 'bottom'}
        // No celular, focar o título abriria o teclado por cima do sheet.
        onOpenAutoFocus={desktop ? undefined : (event) => event.preventDefault()}
        className={cn(desktop ? 'w-full sm:max-w-md' : 'max-h-[90dvh] rounded-t-2xl pb-[env(safe-area-inset-bottom)]')}
      >
        <SheetHeader className="px-5 pt-5">
          <SheetTitle className="text-base font-semibold">Editar tarefa</SheetTitle>
          <SheetDescription className="sr-only">Título, prazo e prioridade.</SheetDescription>
        </SheetHeader>
        {task && <TaskForm key={task.id} task={task} onSave={onSave} onRemove={onRemove} />}
      </SheetContent>
    </Sheet>
  )
}

function TaskForm({ task, onSave, onRemove }: Omit<Props, 'onClose'> & { task: Task }) {
  const [title, setTitle] = useState(task.title)
  const [due, setDue] = useState(task.due_date ?? '')
  const [priority, setPriority] = useState<Priority>(task.priority)
  const today = todayISO()

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const changes: TaskChanges = {}
    if (title.trim() !== task.title) changes.title = title.trim()
    if ((due || null) !== task.due_date) changes.due_date = due || null
    if (priority !== task.priority) changes.priority = priority
    onSave(task, changes)
  }

  const shortcuts = [
    { label: 'Hoje', value: today },
    { label: 'Amanhã', value: addDays(today, 1) },
    { label: 'Sem prazo', value: '' },
  ]

  return (
    <form onSubmit={submit} className="flex flex-col gap-6 overflow-y-auto px-5 pb-5">
      <div className="flex flex-col gap-2">
        <Label htmlFor="task-title">Título</Label>
        <Input
          id="task-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={500}
          className="h-11"
          required
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="task-due">Prazo</Label>
        <Input
          id="task-due"
          type="date"
          value={due}
          onChange={(e) => setDue(e.target.value)}
          className="h-11 tabular-nums"
        />
        <div className="flex flex-wrap gap-2">
          {shortcuts.map((s) => (
            <Button
              key={s.label}
              type="button"
              variant="outline"
              size="sm"
              aria-pressed={due === s.value}
              className="h-8 aria-pressed:border-primary aria-pressed:bg-accent aria-pressed:text-accent-foreground"
              onClick={() => setDue(s.value)}
            >
              {s.label}
            </Button>
          ))}
        </div>
      </div>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-medium">Prioridade</legend>
        <ToggleGroup
          type="single"
          variant="outline"
          spacing={0}
          value={priority}
          onValueChange={(value) => value && setPriority(value as Priority)}
          className="w-full"
        >
          {PRIORITIES.map((p) => (
            <ToggleGroupItem
              key={p.value}
              value={p.value}
              className="h-10 flex-1 data-[state=on]:bg-accent data-[state=on]:text-accent-foreground"
            >
              {p.label}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      </fieldset>

      <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-between">
        {/* O Trigger devolve o foco para "Remover" quando a confirmação fecha */}
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button type="button" variant="destructive" className="h-11 gap-2 sm:h-10">
              <Trash2 aria-hidden />
              Remover
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Remover esta tarefa?</AlertDialogTitle>
              <AlertDialogDescription>“{task.title}” será apagada. Não dá para desfazer.</AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction variant="destructive" onClick={() => onRemove(task)}>
                Remover
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
        <Button type="submit" className="h-11 sm:h-10 sm:px-6" disabled={!title.trim()}>
          Salvar
        </Button>
      </div>
    </form>
  )
}
