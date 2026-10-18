import { test, expect } from '@playwright/test';

test('GPS consent returns nearby results and directions; stop sharing clears origin', async ({ page, context }, testInfo) => {
  await page.clock.install();
  await context.grantPermissions(['geolocation']);
  await context.setGeolocation({ latitude: 10.7769, longitude: 106.7009, accuracy: 20 });
  await page.goto('/chat');
  await page.getByRole('button', { name: 'Tìm điểm gần đây', exact: true }).click();
  const query = page.waitForResponse(r => r.url().includes('/service-points/nearby?'));
  await page.getByRole('button', { name: 'Dùng vị trí hiện tại' }).click();
  const response = await query;
  expect(response.status()).toBe(200);
  const result = (await response.json()).data;
  expect(result.points.length).toBeGreaterThan(0);
  const region = page.getByRole('region', { name: 'Kết quả gần đây', exact: true });
  const links = region.getByRole('link', { name: 'Chỉ đường', exact: true });
  await expect(links).toHaveCount(result.points.length);
  expect(new URL((await links.first().getAttribute('href'))!).searchParams.get('origin')).toBe('10.7769,106.7009');
  await page.clock.fastForward(8500);
  await expect(links).toHaveCount(result.points.length);
  await expect(region).toContainText('Từ vị trí bạn cho phép dùng');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.screenshot({ path: testInfo.outputPath('gps-results.png') });
  await page.getByRole('button', { name: 'Dừng chia sẻ', exact: true }).click();
  await expect(links).toHaveCount(0);
});

test('manual area uses a reference center without claiming customer GPS', async ({ page }, testInfo) => {
  await page.goto('/chat');
  await page.getByRole('button', { name: 'Tìm điểm gần đây', exact: true }).click();
  await page.getByRole('button', { name: 'Nhập khu vực', exact: true }).click();
  await page.getByPlaceholder('Nhập km cao tốc, trạm sạc hoặc khu vực...').fill('TP. Hồ Chí Minh');
  await page.getByRole('button', { name: 'Xác nhận', exact: true }).click();
  const region = page.getByRole('region', { name: 'Kết quả gần đây', exact: true });
  await expect(region).toContainText('không phải GPS');
  const link = region.getByRole('link', { name: 'Chỉ đường', exact: true }).first();
  await expect(link).toBeVisible();
  expect(new URL((await link.getAttribute('href'))!).searchParams.has('origin')).toBe(false);
  await page.screenshot({ path: testInfo.outputPath('manual-results.png') });
});
