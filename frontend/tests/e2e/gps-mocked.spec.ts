import { test, expect, Page } from '@playwright/test';

type GpsWindow = Window & { gpsTest: { starts: number; emit: () => void } };
async function manual(page: Page) {
  await page.getByRole('button', { name: 'Tìm điểm gần đây', exact: true }).click();
  await page.getByRole('button', { name: 'Nhập khu vực', exact: true }).click();
  await page.getByPlaceholder('Nhập km cao tốc, trạm sạc hoặc khu vực...').fill('TP. Hồ Chí Minh');
  await page.getByRole('button', { name: 'Xác nhận', exact: true }).click();
}

test('late one-shot GPS callback cannot restore skipped consent', async ({ page }) => {
  await page.addInitScript(() => {
    const state = { starts: 0, emit: () => {} };
    (window as unknown as GpsWindow).gpsTest = state;
    Object.defineProperty(navigator, 'geolocation', { value: {
      getCurrentPosition(success: PositionCallback) {
        state.starts++;
        state.emit = () => success({ coords: { latitude: 10.7769, longitude: 106.7009, accuracy: 20 } } as GeolocationPosition);
      },
    } });
  });
  await page.goto('/chat');
  await page.getByRole('button', { name: 'Tìm điểm gần đây', exact: true }).click();
  expect(await page.evaluate(() => (window as unknown as GpsWindow).gpsTest.starts)).toBe(0);
  await page.getByRole('button', { name: 'Dùng vị trí hiện tại' }).click();
  await page.getByRole('button', { name: 'Bỏ qua', exact: true }).click();
  await page.evaluate(() => (window as unknown as GpsWindow).gpsTest.emit());
  await expect(page.getByText('Chưa chia sẻ vị trí. Bạn có thể tiếp tục chat.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Chỉ đường Google Maps' })).toHaveCount(0);
});

for (const code of [1, 3]) test(`GPS error ${code} retains manual fallback`, async ({ page }) => {
  await page.addInitScript((errorCode) => {
    Object.defineProperty(navigator, 'geolocation', { value: {
      getCurrentPosition(_success: PositionCallback, failure: PositionErrorCallback) {
        setTimeout(() => failure({ code: errorCode, message: 'Synthetic error' } as GeolocationPositionError), 20);
      },
    } });
  }, code);
  await page.goto('/chat');
  await page.getByRole('button', { name: 'Tìm điểm gần đây', exact: true }).click();
  await page.getByRole('button', { name: 'Dùng vị trí hiện tại' }).click();
  await expect(page.getByText(code === 1 ? 'Trình duyệt đã chặn quyền vị trí.' : 'Quá thời gian chờ tín hiệu GPS (> 8s).')).toBeVisible();
  await page.getByPlaceholder('Nhập km cao tốc, trạm sạc hoặc khu vực...').fill('Khu vực giả lập');
  await page.getByRole('button', { name: 'Xác nhận', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Kết quả gần đây' })).toContainText('Chưa xác định được tâm tham chiếu');
  await expect(page.getByRole('link', { name: 'Chỉ đường Google Maps' })).toHaveCount(0);
});

test('nearby network failure is explicit and can retry without mixing demo points', async ({ page }) => {
  await page.route('**/customer/service-points/nearby?**', route => route.abort('internetdisconnected'));
  await page.goto('/chat');
  await manual(page);
  await expect(page.getByRole('region', { name: 'Kết quả gần đây', exact: true }).getByRole('alert')).toContainText('Không tải được danh mục');
  await expect(page.getByRole('link', { name: 'Chỉ đường Google Maps' })).toHaveCount(0);
  await page.unroute('**/customer/service-points/nearby?**');
  await page.getByRole('button', { name: 'Thử lại tìm kiếm' }).click();
  await expect(page.getByRole('link', { name: 'Chỉ đường Google Maps' })).toHaveCount(5);
});

test('late nearby response cannot overwrite a newer category turn', async ({ page }) => {
  let releaseOld!: () => void;
  const gate = new Promise<void>(resolve => { releaseOld = resolve; });
  let markStarted!: () => void;
  const started = new Promise<void>(resolve => { markStarted = resolve; });
  await page.route('**/customer/service-points/nearby?**', async route => {
    const showroom = new URL(route.request().url()).searchParams.get('category') === 'SHOWROOM';
    if (!showroom) { markStarted(); await gate; }
    await route.fulfill({ json: { data: { points: [{ id: showroom ? 'fresh' : 'stale', name: showroom ? 'Fresh showroom' : 'Stale station', category: showroom ? 'SHOWROOM' : 'CHARGING_STATION', address: 'Synthetic address', latitude: 10.7769, longitude: 106.7009, distance_km: 1, demo: false }] } } }).catch(() => {});
  });
  await page.goto('/chat'); await manual(page); await started;
  await page.getByPlaceholder('Quý khách cần em hỗ trợ gì ạ?').fill('Tìm showroom gần tôi');
  await page.getByRole('button', { name: 'Gửi', exact: true }).click();
  await expect(page.getByText('1. Fresh showroom', { exact: true })).toBeVisible();
  releaseOld();
  await expect(page.getByText('1. Stale station', { exact: true })).toHaveCount(0);
});
