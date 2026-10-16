import { test, expect, Page } from '@playwright/test';

async function login(page: Page) {
  const username = `gps_e2e_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  const password = 'SyntheticE2e!Only2026';
  const registration = await page.request.post('/api/v1/auth/register', { data: { username, password, full_name: 'Synthetic E2E' } });
  expect(registration.ok()).toBeTruthy();
  await page.goto('/login');
  await page.locator('input[autocomplete="username"]').fill(username);
  await page.getByPlaceholder('Nhập mật khẩu').fill(password);
  await page.locator('button[type="submit"]').click();
  await expect.poll(() => page.evaluate(() => localStorage.getItem('vf_access_token'))).toBeTruthy();
  await page.goto('/chat');
}
async function chat(page: Page, message: string) {
  const response = page.waitForResponse(r => r.url().endsWith('/customer/chat') && r.request().method() === 'POST');
  await page.getByPlaceholder('Quý khách cần em hỗ trợ gì ạ?').fill(message);
  await page.getByRole('button', { name: 'Gửi', exact: true }).click();
  return (await (await response).json()).data;
}

test('real login, FAQ and reload never request location', async ({ page }) => {
  await login(page);
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.getByRole('region', { name: 'Kết quả gần đây' })).toHaveCount(0);
  await chat(page, 'Hướng dẫn cách sạc pin tại trạm sạc');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole('dialog')).toHaveCount(0);
});

test('real contextual search returns snapshot top five without a case; reuse consent for showroom', async ({ page, context }, testInfo) => {
  await context.grantPermissions(['geolocation']);
  await context.setGeolocation({ latitude: 10.7769, longitude: 106.7009, accuracy: 20 });
  await login(page);
  let savedLocationCalls = 0;
  page.on('request', request => { if (request.url().endsWith('/customer/location')) savedLocationCalls++; });
  const first = await chat(page, 'Tìm trạm sạc gần đây');
  expect(first.case_id).toBeNull();
  expect(first.nearby_action.category).toBe('CHARGING_STATION');
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('Tìm trạm sạc ô tô');
  const query = page.waitForResponse(r => r.url().includes('/service-points/nearby?'));
  await dialog.getByRole('button', { name: 'Dùng vị trí hiện tại' }).click();
  const response = await query;
  const result = (await response.json()).data;
  expect(result.points).toHaveLength(5);
  expect(result.demo).toBe(false);
  expect(result.distance_method).toBe('AIRLINE');
  expect(result.points.every((p: { vehicle_type: string }) => p.vehicle_type === 'CAR')).toBeTruthy();
  const region = page.getByRole('region', { name: 'Kết quả gần đây', exact: true });
  const links = region.getByRole('link', { name: 'Chỉ đường Google Maps' });
  await expect(links).toHaveCount(5);
  const directions = new URL((await links.first().getAttribute('href'))!);
  expect(directions.searchParams.get('origin')).toBe('10.7769,106.7009');
  expect(directions.searchParams.get('destination')).toBe(`${result.points[0].latitude},${result.points[0].longitude}`);
  await expect(page.getByRole('region', { name: 'Bản đồ điểm dịch vụ', exact: true })).toHaveCount(0);
  await expect(links.first()).toBeInViewport();
  await page.screenshot({ path: testInfo.outputPath('contextual-top-five.png') });
  expect(savedLocationCalls).toBe(0);
  const next = page.waitForResponse(r => r.url().includes('/service-points/nearby?') && r.url().includes('category=SHOWROOM'));
  const follow = await chat(page, 'còn showroom thì sao');
  expect(follow.nearby_action.category).toBe('SHOWROOM');
  await next;
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(links).toHaveCount(5);
  expect(savedLocationCalls).toBe(0);
  await region.getByRole('button', { name: 'Dừng chia sẻ' }).click();
  await expect(page.getByText('Chưa chia sẻ vị trí. Bạn có thể tiếp tục chat.')).toBeVisible();
});

test('explicit area in chat finds Hue showrooms without requesting browser GPS', async ({ page }) => {
  await login(page);
  const response = page.waitForResponse(r => r.url().includes('/service-points/nearby?'));
  const data = await chat(page, 'showroom ở Huế');
  expect(data.nearby_action.requires_location).toBe(false);
  expect(data.nearby_action.area_text).toBe('Huế');
  const points = (await (await response).json()).data.points;
  expect(points.length).toBeGreaterThan(0);
  await expect(page.getByRole('dialog')).toHaveCount(0);
  const region = page.getByRole('region', { name: 'Kết quả gần đây', exact: true });
  await expect(region).toContainText('không phải GPS');
  const link = new URL((await region.getByRole('link', { name: 'Chỉ đường Google Maps' }).first().getAttribute('href'))!);
  expect(link.searchParams.has('origin')).toBe(false);
});


test('logout clears GPS consent and requires a new deliberate location choice', async ({ page, context }) => {
  await context.grantPermissions(['geolocation']);
  await context.setGeolocation({ latitude: 10.7769, longitude: 106.7009, accuracy: 20 });
  await login(page);
  await page.getByRole('button', { name: 'Tìm điểm gần đây', exact: true }).click();
  const nearby = page.waitForResponse(r => r.url().includes('/service-points/nearby?'));
  await page.getByRole('button', { name: 'Dùng vị trí hiện tại' }).click();
  await nearby;
  await expect(page.getByRole('link', { name: 'Chỉ đường Google Maps' })).toHaveCount(5);
  await page.getByTitle('Đăng xuất', { exact: true }).click();
  await expect(page.getByRole('link', { name: 'Chỉ đường Google Maps' })).toHaveCount(0);
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByRole('button', { name: 'Tìm điểm gần đây', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Chỉ đường Google Maps' })).toHaveCount(0);
});
