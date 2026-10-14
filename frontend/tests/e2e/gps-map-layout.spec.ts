import { test, expect } from '@playwright/test';

test('map uses about forty percent of desktop width and remains usable on narrow screens', async ({ page }, testInfo) => {
  // Layout must work when the nearby service is unavailable, using the labelled demo fallback.
  await page.route('**/customer/service-points/nearby?**', route => route.abort('internetdisconnected'));
  await page.goto('/chat');
  await expect(page.getByRole('region', { name: 'Bản đồ điểm dịch vụ', exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Tìm điểm gần đây', exact: true }).click();
  await page.getByRole('button', { name: 'Nhập khu vực', exact: true }).click();
  await page.getByPlaceholder('Nhập km cao tốc, trạm sạc hoặc khu vực...').fill('TP. Hồ Chí Minh');
  await page.getByRole('button', { name: 'Xác nhận', exact: true }).click();

  const panel = page.getByRole('region', { name: 'Bản đồ điểm dịch vụ', exact: true });
  const map = panel.getByRole('region', { name: 'Bản đồ tương tác', exact: true });
  const canvas = map.locator('canvas');
  await expect(canvas).toBeVisible();
  const measurements: Array<{ viewport: number; canvasWidth: number; canvasHeight: number; ratio: number }> = [];

  for (const width of [1280, 1440, 1920, 1024, 768, 375, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    // ResizeObserver updates the MapLibre canvas after the responsive layout changes.
    await expect.poll(async () => {
      const region = await map.boundingBox();
      const drawing = await canvas.boundingBox();
      return !!region && !!drawing && Math.abs(region.width - drawing.width) < 2;
    }).toBeTruthy();
    const drawing = (await canvas.boundingBox())!;
    expect(drawing.height).toBeGreaterThanOrEqual(279);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
    const ratio = drawing.width / width;
    if (width >= 1280) {
      expect(ratio).toBeGreaterThanOrEqual(0.375);
      expect(ratio).toBeLessThanOrEqual(0.415);
    }
    measurements.push({ viewport: width, canvasWidth: drawing.width, canvasHeight: drawing.height, ratio });
    await panel.getByRole('button', { name: /Demo/ }).first().click();
    await expect(panel.getByRole('link', { name: 'Google Maps tìm địa chỉ' })).toHaveAttribute('href', /^https:\/\/www.google.com\/maps/);
    if (width === 1440 || width === 375) {
      await panel.screenshot({ path: testInfo.outputPath(`map-panel-${width}.png`) });
      await page.screenshot({ path: testInfo.outputPath(`map-page-${width}.png`), fullPage: true });
    }
  }
  await testInfo.attach('map-layout-measurements', { body: JSON.stringify(measurements, null, 2), contentType: 'application/json' });
  await page.setViewportSize({ width: 375, height: 812 });
  await panel.getByRole('button', { name: 'Đóng bản đồ', exact: true }).click();
  await expect(panel).toHaveCount(0);
  await expect(page.getByText('Chưa chia sẻ vị trí', { exact: true })).toBeVisible();
  await page.clock.install();
  await page.getByRole('button', { name: 'Chia sẻ vị trí', exact: true }).click();
  await page.getByRole('button', { name: 'Nhập khu vực', exact: true }).click();
  await page.getByPlaceholder('Nhập km cao tốc, trạm sạc hoặc khu vực...').fill('TP. Hồ Chí Minh');
  await page.getByRole('button', { name: 'Xác nhận', exact: true }).click();
  // Exercise the feed's scheduled 120ms scroll as well as the map's animation-frame reveal.
  await page.clock.runFor(250);
  // Read geometry before any locator click can auto-scroll: opening reveals the map below the navbar.
  await expect.poll(async () => {
    const bounds = await panel.boundingBox();
    return !!bounds && bounds.y >= 64 && bounds.y < 160;
  }).toBeTruthy();
  await page.screenshot({ path: testInfo.outputPath('map-open-375.png') });
});
