import { Plus } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { Button } from '@/components/ui/button'
import { useAddTask } from './useTasks'

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)
}

/** Caixa de captura. `/` ou ⌘K foca, Enter envia, Esc limpa. */
export function QuickAdd() {
  const [title, setTitle] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const add = useAddTask()

  useEffect(() => {
    const onKey = (event: globalThis.KeyboardEvent) => {
      const cmdK = event.key.toLowerCase() === 'k' && (event.metaKey || event.ctrlKey)
      const slash = event.key === '/' && !isTypingTarget(event.target)
      if (cmdK || slash) {
        event.preventDefault()
        inputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const clean = title.trim()
    if (!clean) return
    add.mutate({ title: clean, priority: 'medium' })
    setTitle('')
  }

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape') {
      setTitle('')
      if (!title) inputRef.current?.blur()
    }
  }

  return (
    <form onSubmit={submit} className="flex gap-2">
      <label htmlFor="quick-add" className="sr-only">
        Nova tarefa
      </label>
      <input
        ref={inputRef}
        id="quick-add"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Nova tarefa…"
        autoComplete="off"
        enterKeyHint="done"
        maxLength={500}
        className="h-12 min-w-0 flex-1 rounded-[var(--radius)] border border-input bg-card px-4 text-base shadow-xs outline-none transition-colors placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/30"
      />
      <Button type="submit" className="h-12 gap-1.5 px-4" disabled={!title.trim()}>
        <Plus className="size-5" aria-hidden />
        <span className="sr-only sm:not-sr-only">Adicionar</span>
      </Button>
    </form>
  )
}
