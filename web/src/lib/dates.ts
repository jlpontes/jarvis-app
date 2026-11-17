/** Datas como `YYYY-MM-DD` (o formato do contrato). "Hoje" é o dia local do navegador. */

const WEEKDAYS = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb']

function pad(n: number): string {
  return String(n).padStart(2, '0')
}

export function toISODate(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function todayISO(now: Date = new Date()): string {
  return toISODate(now)
}

function parseISODate(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}

export function addDays(iso: string, days: number): string {
  const date = parseISODate(iso)
  date.setDate(date.getDate() + days)
  return toISODate(date)
}

/** `hoje`, `amanhã`, `ontem` ou `sex 20/11` (com o ano quando não é o ano corrente). */
export function formatDue(iso: string, today: string): string {
  if (iso === today) return 'hoje'
  if (iso === addDays(today, 1)) return 'amanhã'
  if (iso === addDays(today, -1)) return 'ontem'
  const date = parseISODate(iso)
  const base = `${WEEKDAYS[date.getDay()]} ${pad(date.getDate())}/${pad(date.getMonth() + 1)}`
  return iso.slice(0, 4) === today.slice(0, 4) ? base : `${base}/${date.getFullYear()}`
}

type Groupable = { due_date: string | null; done: boolean; done_at: string | null }

export type TaskGroups<T> = {
  overdue: T[]
  today: T[]
  upcoming: T[]
  noDate: T[]
  done: T[]
}

/**
 * Separa as tarefas nas seções da tela. Mantém a ordem do servidor (prioridade) dentro de cada
 * seção; "Próximas" fica por data e "Concluídas" pela conclusão mais recente.
 */
export function groupTasks<T extends Groupable>(tasks: readonly T[], today: string): TaskGroups<T> {
  const groups: TaskGroups<T> = { overdue: [], today: [], upcoming: [], noDate: [], done: [] }
  for (const task of tasks) {
    if (task.done) groups.done.push(task)
    else if (task.due_date === null) groups.noDate.push(task)
    else if (task.due_date < today) groups.overdue.push(task)
    else if (task.due_date === today) groups.today.push(task)
    else groups.upcoming.push(task)
  }
  // sort é estável: empates mantêm a ordem do servidor.
  groups.upcoming.sort((a, b) => (a.due_date ?? '').localeCompare(b.due_date ?? ''))
  groups.done.sort((a, b) => (b.done_at ?? '').localeCompare(a.done_at ?? ''))
  return groups
}
