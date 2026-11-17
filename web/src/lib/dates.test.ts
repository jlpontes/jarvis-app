import { describe, expect, it } from 'vitest'
import { addDays, formatDue, groupTasks, todayISO } from './dates'

describe('formatDue', () => {
  const today = '2026-11-17' // terça

  it.each([
    ['2026-11-17', 'hoje'],
    ['2026-11-18', 'amanhã'],
    ['2026-11-16', 'ontem'],
    ['2026-11-20', 'sex 20/11'],
    ['2026-11-01', 'dom 01/11'],
    ['2027-01-04', 'seg 04/01/2027'],
  ])('%s → %s', (iso, expected) => {
    expect(formatDue(iso, today)).toBe(expected)
  })
})

describe('addDays / todayISO', () => {
  it('atravessa mês e ano', () => {
    expect(addDays('2026-12-31', 1)).toBe('2027-01-01')
    expect(addDays('2026-03-01', -1)).toBe('2026-02-28')
  })

  it('usa o dia local', () => {
    expect(todayISO(new Date(2026, 10, 17, 23, 59))).toBe('2026-11-17')
  })
})

const t = (id: number, due_date: string | null, done = false, done_at: string | null = null) => ({
  id,
  due_date,
  done,
  done_at,
})

describe('groupTasks', () => {
  it('separa nas cinco seções', () => {
    const groups = groupTasks(
      [
        t(1, '2026-11-10'),
        t(2, '2026-11-17'),
        t(3, '2026-11-25'),
        t(4, '2026-11-18'),
        t(5, null),
        t(6, '2026-11-01', true, '2026-11-02T10:00:00Z'),
        t(7, null, true, '2026-11-05T10:00:00Z'),
      ],
      '2026-11-17',
    )
    expect(groups.overdue.map((x) => x.id)).toEqual([1])
    expect(groups.today.map((x) => x.id)).toEqual([2])
    expect(groups.upcoming.map((x) => x.id)).toEqual([4, 3])
    expect(groups.noDate.map((x) => x.id)).toEqual([5])
    expect(groups.done.map((x) => x.id)).toEqual([7, 6])
  })
})
