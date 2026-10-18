import { test, expect } from '@playwright/test';
import fs from 'node:fs';

test('Serv mechanism switches illustrative outcomes and preserves selection when translated', async ({ page }) => {
  await page.goto('/project-overview');
  const scenarios = page.getByRole('group', { name: 'Chọn tình huống minh họa' });
  await scenarios.getByRole('button', { name: 'Ảnh cảnh báo', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Dấu hiệu cần làm rõ', exact: true })).toBeVisible();
  const lookup = scenarios.getByRole('button', { name: 'Tra cứu dịch vụ', exact: true });
  await lookup.focus();
  await lookup.press('Enter');
  await expect(lookup).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('heading', { name: 'Câu trả lời kèm nguồn', exact: true })).toBeVisible();
  await page.locator('header').getByRole('button', { name: 'English', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'An answer with references', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Service information', exact: true })).toHaveAttribute('aria-pressed', 'true');
});

test('validation stays explicit about the recorded test scope', async ({ page }) => {
  await page.goto('/project-overview');
  await expect(page.locator('#flow-proof')).toContainText('Ba ca còn lại');
  await page.locator('#flow-proof summary').click();
  await expect(page.locator('#flow-proof details[open]')).toContainText('chưa kiểm thử trực tiếp giao diện web');
});

test('hero illustration toggles charging with pointer and keyboard', async ({ page }) => {
  await page.goto('/project-overview');
  const toggle = page.getByRole('button', { name: 'Đổi trạng thái cắm sạc của hình minh họa', exact: true });
  await expect(toggle).toHaveAttribute('aria-pressed', 'false');
  await expect(toggle.locator('img[aria-hidden="false"]')).toHaveAttribute('src', /serviceflow-hero-vf6-charger/);
  await toggle.click();
  await expect(toggle).toHaveAttribute('aria-pressed', 'true');
  await expect(toggle.locator('img[aria-hidden="false"]')).toHaveAttribute('src', /serviceflow-hero-vf6-charging/);
  await toggle.press('Space');
  await expect(toggle).toHaveAttribute('aria-pressed', 'false');
  await toggle.press('Enter');
  await expect(toggle).toHaveAttribute('aria-pressed', 'true');
});

test('separate VFServ page explains the product and supports the complete demo journey', async ({ page }) => {
  await page.goto('/project-overview');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('An tâm');
  await expect(page.getByText('Tình huống minh họa', { exact: true }).first()).toBeVisible();
  const tabs = page.getByRole('tablist', { name: 'Quy trình hỗ trợ minh họa' }).getByRole('tab');
  await expect(tabs).toHaveCount(4);
  await tabs.last().click();
  await expect(tabs.last()).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByRole('tabpanel')).toContainText('Chờ nhân viên rà soát');
  await tabs.last().press('Home');
  await expect(tabs.first()).toBeFocused();
  await expect(tabs.first()).toHaveAttribute('aria-selected', 'true');
  await tabs.first().press('ArrowRight');
  await expect(tabs.nth(1)).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByRole('tabpanel')).toContainText('VF 8');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('project presentation opens the existing product only through the explore CTA', async ({ page }) => {
  await page.goto('/project-overview');
  await expect(page.getByRole('textbox')).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Đăng nhập', exact: true })).toHaveCount(0);
  const links = page.getByRole('link', { name: 'Khám phá sản phẩm', exact: true });
  await expect(links).toHaveCount(4);
  for (const link of await links.all()) await expect(link).toHaveAttribute('href', '/');
  if ((page.viewportSize()?.width || 0) <= 800) {
    await page.locator('summary[aria-label="Mở menu giới thiệu"]').click();
    const menu = page.getByRole('navigation', { name: 'Menu giới thiệu trên điện thoại' });
    await expect(menu).toBeVisible();
    await menu.getByRole('link', { name: 'Bài toán', exact: true }).click();
    await expect(menu).not.toBeVisible();
  }
  await page.getByRole('heading', { name: /Dự án của team chúng tôi/ }).scrollIntoViewIfNeeded();
  await expect(page.getByText('Team VFO2O-18', { exact: true }).first()).toBeVisible();
  await links.first().click();
  await expect(page).toHaveURL(/:\d+\/$/);
  await expect(page.getByRole('link', { name: 'Đăng nhập', exact: true })).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Mô tả câu hỏi hoặc sự cố xe' })).toBeVisible();
});

test('existing language switch translates the page and FAQ opens with the keyboard', async ({ page }) => {
  await page.goto('/project-overview');
  await page.locator('header').getByRole('button', { name: 'English', exact: true }).click();
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Understand the issue.');
  await expect(page.getByRole('tablist', { name: 'Illustrative support journey' })).toBeVisible();
  const question = page.locator('#flow-faq summary').first();
  await question.focus();
  await question.press('Enter');
  await expect(page.getByText('The project focuses on collecting owner information', { exact: false })).toBeVisible();
});

for (const theme of ['light', 'dark']) {
  test(`page has accessible content and no horizontal overflow in ${theme} mode`, async ({ page }) => {
    await page.addInitScript(theme => localStorage.setItem('vf_theme', theme), theme);
    await page.goto('/project-overview');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await page.addScriptTag({ content: fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8') });
    const violations = await page.evaluate(async () => {
      const result = await (window as any).axe.run(document.querySelector('[data-project-overview]'), {
        runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa'] },
      });
      return result.violations.map((v: any) => ({ id: v.id, nodes: v.nodes.map((n: any) => n.target) }));
    });
    expect(violations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
}
