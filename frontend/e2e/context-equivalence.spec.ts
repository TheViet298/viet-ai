import { test, expect } from '@playwright/test';
import { ChatPage } from './pages/ChatPage';

const phrases = ['Tư vấn về VF 7', 'tư vấn xe vf7', 'tôi muốn hỏi về vf7', 'tu van vf7'];
for (const phrase of phrases) test(phrase, async ({page}) => {
  test.skip(process.env.QA_ALLOW_MUTATIONS !== '1' || !process.env.QA_CUSTOMER_PASSWORD || !process.env.QA_CUSTOMER_USERNAME,
    'Requires explicitly isolated QA environment and environment credentials');
  const chat = new ChatPage(page);
  await chat.login(process.env.QA_CUSTOMER_USERNAME!, process.env.QA_CUSTOMER_PASSWORD!);
  const data = await chat.send(phrase);
  expect(data.vehicle_cards.map((card: {variant: string}) => card.variant)).toEqual(['eco', 'plus', 'plus-awd']);
  for (const card of data.vehicle_cards) {
    const image = page.getByRole('img', {name: card.name, exact:true});
    await image.scrollIntoViewIfNeeded();
    await expect(image).toBeVisible();
    await expect.poll(() => image.evaluate(element => (element as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  }
  const cost = await chat.send('Giá sạc VF7 bao nhiêu?');
  expect(cost.vehicle_cards).toEqual([]);
  expect(cost.message).not.toMatch(/giá niêm yết|dự toán lăn bánh/i);
  await page.reload();
  await expect(page.getByRole('textbox', {name:'Tin nhắn gửi trợ lý VinFast'})).toBeVisible();
});
