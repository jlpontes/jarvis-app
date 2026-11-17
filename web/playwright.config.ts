import { defineConfig, devices } from '@playwright/test'

const port = Number(process.env.E2E_PORT ?? 8765)
const baseURL = `http://localhost:${port}`

// Smoke test no tamanho de um celular (375 px), contra o app em modo produção numa porta só.
export default defineConfig({
  testDir: './e2e',
  testMatch: '*.e2e.ts', // não usa *.spec/*.test para o Vitest não pegar estes arquivos
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL,
    locale: 'pt-BR',
    timezoneId: 'America/Sao_Paulo',
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'celular',
      use: { ...devices['Desktop Chrome'], viewport: { width: 375, height: 812 }, isMobile: false },
    },
  ],
  webServer: {
    command: './e2e/serve.sh',
    url: `${baseURL}/api/health`,
    env: { E2E_PORT: String(port) },
    reuseExistingServer: false,
    timeout: 120_000,
  },
})
