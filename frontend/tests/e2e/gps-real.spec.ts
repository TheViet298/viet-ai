import { test, expect, Page } from '@playwright/test';
import { writeFile } from 'node:fs/promises';

const password = 'SyntheticE2e!Only2026';
async function login(page: Page) {
  const username = `gps_e2e_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  const registration = await page.request.post('/api/v1/auth/register', { data: { username, password, full_name: 'Synthetic E2E' } });
  expect(registration.ok()).toBeTruthy();
  await page.goto('/login');
  await page.locator('input[autocomplete="username"]').fill(username);
  await page.getByPlaceholder('Nhập mật khẩu').fill(password);
  await page.locator('button[type="submit"]').click();
  await expect.poll(() => page.evaluate(() => localStorage.getItem('vf_access_token'))).toBeTruthy();
  await page.goto('/chat');
  return page.evaluate(() => localStorage.getItem('vf_access_token'));
}
async function createCase(page: Page) {
  const response = page.waitForResponse(r => r.url().endsWith('/customer/chat') && r.request().method() === 'POST');
  await page.getByPlaceholder('Quý khách cần em hỗ trợ gì ạ?').fill('Xe VF 8 có khói và mùi khét từ pin, xe đang cháy');
  await page.getByRole('button', { name: 'Gửi', exact: true }).click();
  const json = await (await response).json();
  expect(json.success).toBeTruthy();
  expect(json.data.case_id).toBeTruthy();
  return json.data.case_id as string;
}
for (const timing of ['before', 'after'] as const) {
  test(`real backend: GPS ${timing} case, manual, revoke, ownership`, async ({ page, context }, testInfo) => {
    await context.grantPermissions(['geolocation']);
    await context.setGeolocation({ latitude: 10.7769, longitude: 106.7009, accuracy: 20 });
    const workerResponses: number[] = [];
    const tileNetwork: Array<{ outcome: string; status?: number; error?: string }> = [];
    page.on('response', response => { if (response.url().includes('tile.openstreetmap.org')) tileNetwork.push({ outcome: 'response', status: response.status() }); });
    page.on('requestfailed', request => { if (request.url().includes('tile.openstreetmap.org')) tileNetwork.push({ outcome: 'failed', error: request.failure()?.errorText }); });
    page.on('response', response => { if (response.url().endsWith('/maplibre-gl-worker.mjs')) workerResponses.push(response.status()); });
    const token = await login(page);
    const headers = { Authorization: `Bearer ${token}` };
    let caseId: string;
    if (timing === 'after') caseId = await createCase(page);
    else await page.getByRole('button', { name: 'Tìm điểm gần đây', exact: true }).click();
    await page.getByRole('button', { name: 'Dùng vị trí hiện tại', exact: true }).click();
    await expect(page.getByText('Đã ghi nhận vị trí (GPS)', { exact: true })).toBeVisible();
    const map = page.getByRole('region', { name: 'Bản đồ điểm dịch vụ' });
    await expect(map).toBeVisible();
    await expect(map.locator('canvas')).toBeVisible();
    await expect.poll(() => workerResponses).toContain(200);
    await map.getByRole('button', { name: /Demo/ }).first().click();
    await expect(map.getByRole('link', { name: 'Google Maps chỉ đường' })).toHaveAttribute('href', /origin=10.7769/);
    await map.evaluate(element => { element.scrollIntoView({ block: 'start' }); element.parentElement?.scrollTo(0, 0); window.scrollBy(0, -240); });
    await map.screenshot({ path: testInfo.outputPath('gps-map-desktop.png') });
    const tileSummary = await page.evaluate(() => performance.getEntriesByType('resource').filter(entry => entry.name.includes('tile.openstreetmap.org')).map(entry => ({ url: entry.name, duration: entry.duration })));
    const networkPath = testInfo.outputPath('basemap-network.json');
    await writeFile(networkPath, JSON.stringify({ note: 'Resource timing proves attempted tile loads only; canvas/worker assertions do not prove basemap pixels.', outcomes: tileNetwork, attempts: tileSummary }, null, 2));
    await testInfo.attach('basemap-network.json', { path: networkPath, contentType: 'application/json' });
    if (timing === 'before') caseId = await createCase(page);
    const location = async () => (await (await page.request.get(`/api/v1/customer/cases/${caseId}`, { headers })).json()).data.location;
    await expect.poll(async () => (await location())?.status).toBe('CONSENTED');
    expect((await location()).latitude).toBe(10.7769);
    // A different real customer cannot update or read this case.
    const other = await page.request.post('/api/v1/auth/register', { data: { username: `other_${Date.now()}`, password } });
    expect(other.ok()).toBeTruthy();
    const otherToken = (await other.json()).data.token;
    const deniedRead = await page.request.get(`/api/v1/customer/cases/${caseId!}`, { headers: { Authorization: `Bearer ${otherToken}` } });
    expect(deniedRead.status()).toBe(403);
    const denied = await page.request.post('/api/v1/customer/location', { headers: { Authorization: `Bearer ${otherToken}` }, data: { case_id: caseId!, status: 'NOT_SHARED', source: 'USER_TEXT', location_label: 'Không chia sẻ', share_with_staff: false } });
    expect(denied.status()).toBe(403);
    await page.getByRole('button', { name: 'Nhập khu vực', exact: true }).click();
    await page.setViewportSize({ width: 375, height: 812 });
    const manualInput = page.getByPlaceholder('Nhập km cao tốc, trạm sạc hoặc khu vực...');
    await manualInput.fill('Quận 1');
    await manualInput.scrollIntoViewIfNeeded();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: testInfo.outputPath('manual-form-mobile.png'), fullPage: true });
    await page.getByRole('button', { name: 'Xác nhận', exact: true }).click();
    await expect.poll(async () => (await location())?.status).toBe('MANUAL');
    expect((await location()).latitude).toBeNull();
    expect((await location()).longitude).toBeNull();
    await page.setViewportSize({ width: 375, height: 812 });
    await page.screenshot({ path: testInfo.outputPath('manual-mobile.png'), fullPage: true });
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.getByTitle('Đổi lại vị trí').click();
    await page.getByRole('button', { name: /Bỏ qua/ }).click();
    await expect.poll(async () => (await location())?.status).toBe('NOT_SHARED');
    expect(await location()).toMatchObject({ latitude: null, longitude: null, share_with_staff: false, location_label: '' });
    await page.reload();
    await expect(page.getByText('Xe VF 8 có khói và mùi khét từ pin, xe đang cháy', { exact: true })).toBeVisible();
  });
}

test('production hydration across time zones and minute changes', async ({ browser }) => {
  for (const timezoneId of ['Pacific/Honolulu', 'Asia/Bangkok']) {
    const context = await browser.newContext({ timezoneId });
    const page = await context.newPage();
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    await page.clock.install({ time: new Date('2026-10-13T12:34:59Z') });
    await page.goto('/chat');
    const time = page.locator('time').first();
    await expect(time).not.toHaveText('');
    const original = await time.textContent();
    await page.clock.fastForward(2000);
    await page.getByPlaceholder('Quý khách cần em hỗ trợ gì ạ?').fill('Timestamp remains stable');
    await expect(time).toHaveText(original!);
    await page.reload();
    await expect(time).not.toHaveText('');
    expect(errors.filter(value => /hydration|#42[35]|did not match/i.test(value))).toEqual([]);
    await context.close();
  }
});
