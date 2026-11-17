import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { call, type ActionArgs, type Task } from '@/api/client'
import { useToast } from '@/components/Toast'

export const tasksKey = ['tarefas', 'all'] as const

/** Todas as tarefas (pendentes e concluídas); a tela agrupa no cliente. */
export function useTasks() {
  return useQuery({
    queryKey: tasksKey,
    queryFn: async () => (await call('/api/tarefas/listar', { filter: 'all' })).data,
  })
}

/**
 * Mutation otimista: muda o cache na hora, desfaz se o servidor recusar e, no fim, busca a
 * lista de novo. `scope` faz as mutations de tarefas rodarem em fila (concluir → desfazer
 * nunca chega fora de ordem no servidor).
 */
function useOptimisticTaskMutation<V, R>(
  mutationFn: (vars: V) => Promise<R>,
  apply: (tasks: Task[], vars: V) => Task[],
) {
  const queryClient = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn,
    scope: { id: 'tarefas' },
    onMutate: async (vars: V) => {
      await queryClient.cancelQueries({ queryKey: tasksKey })
      const previous = queryClient.getQueryData<Task[]>(tasksKey)
      if (previous) queryClient.setQueryData<Task[]>(tasksKey, apply(previous, vars))
      return { previous }
    },
    onError: (error, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(tasksKey, context.previous)
      toast({ message: error.message, tone: 'error' })
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: tasksKey }),
  })
}

const nowISO = () => new Date().toISOString()

/** Id temporário (negativo) para a tarefa recém-criada até o servidor responder. */
let tempId = 0
export const isTemp = (task: Task) => task.id < 0

export function useAddTask() {
  return useOptimisticTaskMutation(
    (args: ActionArgs<'/api/tarefas/add'>) => call('/api/tarefas/add', args),
    (tasks, args) => [
      {
        id: --tempId,
        title: args.title.trim(),
        due_date: args.due_date ?? null,
        priority: args.priority,
        done: false,
        created_at: nowISO(),
        done_at: null,
      },
      ...tasks,
    ],
  )
}

export function useCompleteTask() {
  return useOptimisticTaskMutation(
    (task: Task) => call('/api/tarefas/feito', { id: task.id }),
    (tasks, task) => tasks.map((t) => (t.id === task.id ? { ...t, done: true, done_at: nowISO() } : t)),
  )
}

export function useReopenTask() {
  return useOptimisticTaskMutation(
    (task: Task) => call('/api/tarefas/reabrir', { id: task.id }),
    (tasks, task) => tasks.map((t) => (t.id === task.id ? { ...t, done: false, done_at: null } : t)),
  )
}

export function useEditTask() {
  return useOptimisticTaskMutation(
    (args: ActionArgs<'/api/tarefas/editar'>) => call('/api/tarefas/editar', args),
    (tasks, args) =>
      tasks.map((t) =>
        t.id === args.id
          ? {
              ...t,
              ...(args.title != null && { title: args.title.trim() }),
              ...(args.due_date !== undefined && { due_date: args.due_date }),
              ...(args.priority != null && { priority: args.priority }),
            }
          : t,
      ),
  )
}

export function useRemoveTask() {
  return useOptimisticTaskMutation(
    (task: Task) => call('/api/tarefas/remover', { id: task.id }),
    (tasks, task) => tasks.filter((t) => t.id !== task.id),
  )
}
