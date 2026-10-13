import { test, expect } from '@playwright/test';

// Browser geolocation is intentionally mocked here; real API persistence lives in gps-real.
test('mocked late geolocation callback cannot restore revoked consent', async ({ page }) => {
  await page.addInitScript(() => {
    const state = { starts: 0, stops: 0, emit: () => {} };
    Object.assign(window, { gpsTest: state });
    Object.defineProperty(navigator, 'geolocation', { value: {
      watchPosition(success: PositionCallback) {
        state.starts++;
        state.emit = () => success({ coords: { latitude: 10.7769, longitude: 106.7009, accuracy: 20 }, timestamp: Date.now() } as GeolocationPosition);
        return 1;
      },
      clearWatch() { state.stops++; },
    } });
  });
  await page.goto('/chat');
  await page.getByRole('button', { name: 'Tìm điểm gần đây', exact: true }).click();
  expect(await page.evaluate(() => (window as any).gpsTest.starts)).toBe(0);
  await page.getByRole('button', { name: 'Dùng vị trí hiện tại' }).click();
  await page.evaluate(() => (window as any).gpsTest.emit());
  await expect(page.getByText('Đã ghi nhận vị trí (GPS)', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Dừng chia sẻ' }).click();
  await page.evaluate(() => (window as any).gpsTest.emit());
  await expect(page.getByText('Chưa chia sẻ vị trí', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => (window as any).gpsTest.stops)).toBe(1);
});

test('mocked GPS timeout preserves manual fallback', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'geolocation', { value: {
      watchPosition(_success: PositionCallback, failure: PositionErrorCallback) {
        setTimeout(() => failure({ code: 3, message: 'Synthetic timeout' } as GeolocationPositionError), 20);
        return 1;
      }, clearWatch() {},
    } });
  });
  await page.goto('/chat');
  await page.getByRole('button', { name: 'Tìm điểm gần đây', exact: true }).click();
  await page.getByRole('button', { name: 'Dùng vị trí hiện tại' }).click();
  await expect(page.getByText('Quá thời gian chờ tín hiệu GPS (> 8s).')).toBeVisible();
  await page.getByPlaceholder('Nhập km cao tốc, trạm sạc hoặc khu vực...').fill('Khu vực giả lập');
  await page.getByRole('button', { name: 'Xác nhận', exact: true }).click();
  await expect(page.getByText('Khu vực: Khu vực giả lập', { exact: true })).toBeVisible();
});
