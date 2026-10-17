import { test, expect } from '@playwright/test';
import { ChatPage } from './pages/ChatPage';

test('customer history is isolated after account switch', async ({page}) => {
  test.skip(process.env.QA_ALLOW_MUTATIONS !== '1' || !process.env.QA_CUSTOMER_USERNAME || !process.env.QA_CUSTOMER_PASSWORD ||
    !process.env.QA_CUSTOMER2_USERNAME || !process.env.QA_CUSTOMER2_PASSWORD, 'Requires two QA accounts in an isolated environment');
  const chat = new ChatPage(page);
  await chat.login(process.env.QA_CUSTOMER_USERNAME!, process.env.QA_CUSTOMER_PASSWORD!);
  const marker = `Tư vấn VF7 ${Date.now()}`;
  await chat.send(marker);
  await page.getByRole('button', {name:'Đăng xuất', exact:true}).click();
  await chat.login(process.env.QA_CUSTOMER2_USERNAME!, process.env.QA_CUSTOMER2_PASSWORD!);
  await expect(page.getByText(marker, {exact:true})).toHaveCount(0);
  await page.goto('/console');
  await expect(page.getByRole('heading', {name:'Khu Vực Bàn Điều Phối (Staff Portal)'})).toBeVisible();
  await expect(page.getByRole('button', {name:'Duyệt & Điều phối', exact:true})).toHaveCount(0);
});
