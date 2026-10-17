import { test, expect } from '@playwright/test';
import fs from 'node:fs';

test('login keyboard, axe and responsive layout', async ({page}, testInfo) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/login');
  await expect(page.getByLabel('Mật khẩu', {exact:true})).toBeVisible();
  await page.getByLabel('Số điện thoại / Tên đăng nhập').focus();
  await page.keyboard.press('Tab');
  await expect(page.getByLabel('Mật khẩu', {exact:true})).toBeFocused();
  await page.addScriptTag({content:fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8')});
  const violations = await page.evaluate(async () => {
    const axe = (window as unknown as {axe: {run: () => Promise<{violations: {impact: string}[]}>}}).axe;
    return (await axe.run()).violations.filter(v => ['serious', 'critical'].includes(v.impact));
  });
  expect(violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(errors).toEqual([]);
  testInfo.annotations.push({type:'visual-baseline', description:'INCONCLUSIVE until human-approved baseline exists'});
});

test('production Core Web Vitals acceptance', async () => {
  test.skip(true, 'NOT_MEASURED: run web-vitals production instrumentation for 3 runs per breakpoint; no INP proxy accepted');
});
