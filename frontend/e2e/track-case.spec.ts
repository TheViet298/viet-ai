import { test, expect } from '@playwright/test';
import { ChatPage } from './pages/ChatPage';

test('legacy object evidence renders without exposing routing metadata', async ({page}) => {
  test.skip(!process.env.QA_CUSTOMER_USERNAME || !process.env.QA_CUSTOMER_PASSWORD, 'Requires QA seeded historical cases');
  const chat = new ChatPage(page);
  await chat.login(process.env.QA_CUSTOMER_USERNAME!, process.env.QA_CUSTOMER_PASSWORD!);
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/api/v1/customer/cases**', async route => {
    if (route.request().method() !== 'GET') return route.continue();
    const response = await route.fetch();
    const body = await response.json();
    const inject = (value: unknown): void => {
      if (!value || typeof value !== 'object') return;
      if ('captured_fields' in value) Object.assign(value, {captured_fields: {
        visual_signals: [{owner_user_id:'PRIVATE_FIXTURE', image_routing:'PRIVATE_FIXTURE'}],
      }});
      for (const item of Object.values(value)) inject(item);
    };
    inject(body);
    await route.fulfill({response, json:body});
  });
  await page.goto('/track-case');
  await expect(page.getByText('Đã nhận bằng chứng ảnh; cần đối chiếu hiện tượng.', {exact:false}).first()).toBeVisible();
  expect(errors).toEqual([]);
  await expect(page.getByText('PRIVATE_FIXTURE', {exact:false})).toHaveCount(0);
});
