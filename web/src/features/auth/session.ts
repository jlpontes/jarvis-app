import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { isLoggedIn, login, logout, setUnauthorizedHandler } from '@/api/client'

export const sessionKey = ['session'] as const

/** `data` é `true` com sessão válida e `false` sem login (vem de `GET /api/me`). */
export function useSession() {
  return useQuery({ queryKey: sessionKey, queryFn: () => isLoggedIn(), staleTime: Infinity })
}

/** Qualquer 401 fora do login: apaga os dados em cache e marca "sem sessão". */
export function installUnauthorizedHandler(queryClient: QueryClient): void {
  setUnauthorizedHandler(() => {
    queryClient.removeQueries({ predicate: (q) => q.queryKey[0] !== sessionKey[0] })
    queryClient.setQueryData(sessionKey, false)
  })
}

export function useLogin() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (password: string) => login(password),
    onSuccess: () => queryClient.setQueryData(sessionKey, true),
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => logout(),
    onSettled: () => {
      queryClient.removeQueries({ predicate: (q) => q.queryKey[0] !== sessionKey[0] })
      queryClient.setQueryData(sessionKey, false)
    },
  })
}
