import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { RequireAuth } from '@/components/AppShell'
import { ComingSoon } from '@/components/ComingSoon'
import { ToastProvider } from '@/components/Toast'
import { ApiError } from '@/api/client'
import { installUnauthorizedHandler } from '@/features/auth/session'
import { LoginPage } from '@/features/auth/LoginPage'
import { TasksPage } from '@/features/tasks/TasksPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Erro de regra ou de login não melhora tentando de novo; só falha de rede.
      retry: (count, error) => count < 2 && error instanceof ApiError && error.status === null,
      refetchOnWindowFocus: true,
    },
  },
})
installUnauthorizedHandler(queryClient)

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<RequireAuth />}>
              <Route path="/" element={<Navigate to="/tarefas" replace />} />
              <Route
                path="/hoje"
                element={
                  <ComingSoon title="Hoje">
                    Aqui vão aparecer as tarefas atrasadas e de hoje, e o saldo do mês.
                  </ComingSoon>
                }
              />
              <Route path="/tarefas" element={<TasksPage />} />
              <Route
                path="/financas"
                element={
                  <ComingSoon title="Finanças">Gastos, receitas e o resumo do mês chegam no M4.</ComingSoon>
                }
              />
              <Route path="*" element={<Navigate to="/tarefas" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  )
}
