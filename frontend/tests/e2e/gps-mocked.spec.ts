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

test('mocked unavailable nearby API keeps manual location and demo list usable', async ({ page }) => {
  await page.route('**/customer/service-points/nearby?**', route => route.abort('internetdisconnected'));
  await page.goto('/chat');
  await page.getByRole('button', { name: 'Tìm điểm gần đây', exact: true }).click();
  await page.getByRole('button', { name: 'Nhập khu vực', exact: true }).click();
  const failed = page.waitForEvent('requestfailed', request => request.url().includes('/service-points/nearby?'));
  await page.getByPlaceholder('Nhập km cao tốc, trạm sạc hoặc khu vực...').fill('TP. Hồ Chí Minh');
  await page.getByRole('button', { name: 'Xác nhận', exact: true }).click();
  await failed;
  await expect(page.getByText('Khu vực: TP. Hồ Chí Minh', { exact: true })).toBeVisible();
  const map = page.getByRole('region', { name: 'Bản đồ điểm dịch vụ' });
  await expect(map.getByRole('button', { name: /Demo/ }).first()).toBeVisible();
  await expect(map.getByRole('link', { name: 'Google Maps tìm địa chỉ' })).toHaveAttribute('href', /^https:\/\/www.google.com\/maps/);
});

test('mocked late nearby response cannot overwrite a newer category request', async ({ page }) => {
  let releaseOld!: () => void;
  const oldGate = new Promise<void>(resolve => { releaseOld = resolve; });
  let oldFinished!: () => void;
  const finished = new Promise<void>(resolve => { oldFinished = resolve; });
  let oldStarted!: () => void;
  const started = new Promise<void>(resolve => { oldStarted = resolve; });
  await page.route('**/customer/service-points/nearby?**', async route => {
    const old = new URL(route.request().url()).searchParams.get('category') === 'ALL';
    if (old) { oldStarted(); await oldGate; }
    await route.fulfill({ json: { data: { points: [{ id: old ? 'stale' : 'fresh', name: old ? 'Stale response point' : 'Fresh response point', category: 'CHARGING_STATION', address: 'Synthetic address', latitude: 10.7769, longitude: 106.7009, hotline: '', demo: true }] } } }).catch(() => {});
    if (old) oldFinished();
  });
  await page.goto('/chat');
  await page.getByRole('button', { name: 'Tìm điểm gần đây', exact: true }).click();
  await page.getByRole('button', { name: 'Nhập khu vực', exact: true }).click();
  await page.getByPlaceholder('Nhập km cao tốc, trạm sạc hoặc khu vực...').fill('TP. Hồ Chí Minh');
  await page.getByRole('button', { name: 'Xác nhận', exact: true }).click();
  await started;
  const map = page.getByRole('region', { name: 'Bản đồ điểm dịch vụ' });
  await map.getByRole('button', { name: 'Trụ sạc', exact: true }).click();
  await expect(map.getByRole('button', { name: /Fresh response point/ }).first()).toBeVisible();
  releaseOld();
  await finished;
  await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => resolve())));
  await expect(map.getByRole('button', { name: /Fresh response point/ }).first()).toBeVisible();
  await expect(map.getByText(/Stale response point/)).toHaveCount(0);
});
