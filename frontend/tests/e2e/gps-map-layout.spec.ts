import { test, expect } from '@playwright/test';

test.skip(!process.env.GPS_E2E_REAL_CATALOG || !process.env.NEXT_PUBLIC_VIETMAP_API_KEY, 'Requires imported full catalog and a valid Vietmap API key');

test('compact map stays collapsed and top-five directions fit desktop and mobile', async ({ page }, testInfo) => {
  await page.goto('/chat');
  await page.getByRole('button', { name: 'Tìm điểm gần đây', exact: true }).click();
  await page.getByRole('button', { name: 'Nhập khu vực', exact: true }).click();
  await page.getByPlaceholder('Nhập km cao tốc, trạm sạc hoặc khu vực...').fill('TP. Hồ Chí Minh');
  await page.getByRole('button', { name: 'Xác nhận', exact: true }).click();
  const result = page.getByRole('region', { name: 'Kết quả gần đây', exact: true });
  await expect(result.getByRole('link', { name: 'Chỉ đường', exact: true })).toHaveCount(5);
  await expect(page.getByRole('region', { name: 'Bản đồ điểm dịch vụ', exact: true })).toHaveCount(0);
  for (const width of [1440, 768, 375]) {
    await page.setViewportSize({ width, height: 900 });
    await result.evaluate(element => { const feed = element.closest<HTMLElement>('[data-chat-feed]'); if (feed) feed.scrollTop += element.getBoundingClientRect().top - feed.getBoundingClientRect().top; });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
    const links = result.getByRole('link', { name: 'Chỉ đường', exact: true });
    expect((await links.first().boundingBox())!.width).toBeLessThan(width);
    await expect(links.first()).toBeInViewport();
    await expect(page.getByRole("button", { name: "Tin mới", exact: true })).toHaveCount(0);
    await page.screenshot({ path: testInfo.outputPath(`compact-results-${width}.png`) });
  }
  await result.getByRole('button', { name: 'Xem bản đồ', exact: true }).click();
  const map = page.getByRole('region', { name: 'Bản đồ điểm dịch vụ', exact: true });
  await expect(map.locator('canvas')).toBeVisible();
  await expect(map.locator('canvas')).toBeInViewport();
  await expect(map.locator('.maplibregl-marker')).toHaveCount(6);
  expect((await map.boundingBox())!.height).toBeGreaterThan(200);
  await page.screenshot({ path: testInfo.outputPath('compact-map-mobile.png') });
  await page.getByRole('button', { name: 'Đóng bản đồ', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Bản đồ điểm dịch vụ', exact: true })).toHaveCount(0);
  await expect(result.getByRole('link', { name: 'Chỉ đường', exact: true })).toHaveCount(5);
});
