import { test, expect } from '@playwright/test';

test('should load landing page and show NexusOpsCRM brand', async ({ page }) => {
  await page.goto('/');
  // Verify target header brand title
  await expect(page.locator('h1')).toContainText(/NexusOpsCRM/i);
});
