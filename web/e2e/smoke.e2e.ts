import { expect, test } from '@playwright/test'

// Senha definida em e2e/serve.sh (banco temporário, só para este teste).
const PASSWORD = 'senha-do-teste-e2e'

test('login → adicionar → concluir → recarregar → continua lá', async ({ page }) => {
  const title = `Comprar pão ${Date.now()}`

  await page.goto('/')
  await expect(page).toHaveURL(/\/login$/)

  await page.getByLabel('Senha').fill(PASSWORD)
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page.getByRole('heading', { name: 'Tarefas' })).toBeVisible()

  // Adicionar
  await page.getByLabel('Nova tarefa').fill(title)
  await page.keyboard.press('Enter')
  const pending = page.getByRole('checkbox', { name: `Concluir “${title}”` })
  await expect(pending).toBeVisible()
  await expect(pending).toBeEnabled() // o servidor já respondeu (sem id temporário)

  // Concluir: sai da lista de pendentes e aparece o "Desfazer"
  await pending.click()
  await expect(page.getByRole('button', { name: 'Desfazer' })).toBeVisible()
  await expect(pending).toBeHidden()

  // Recarregar: a sessão continua e a tarefa está em "Concluídas"
  await page.waitForLoadState('networkidle')
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Tarefas' })).toBeVisible()
  await page.getByRole('button', { name: /Concluídas/ }).click()
  await expect(page.getByRole('checkbox', { name: `Reabrir “${title}”` })).toBeChecked()
})
