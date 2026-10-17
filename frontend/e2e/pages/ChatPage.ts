import { expect, Page } from '@playwright/test';

export class ChatPage {
  constructor(readonly page: Page) {}
  async login(username: string, password: string) {
    await this.page.goto('/login');
    await this.page.getByLabel('Số điện thoại / Tên đăng nhập').fill(username);
    await this.page.getByLabel('Mật khẩu', {exact: true}).fill(password);
    await this.page.getByRole('button', {name: 'Đăng nhập', exact: true}).click();
    await expect(this.page).toHaveURL(/\/chat$/);
  }
  async send(text: string) {
    const input = this.page.getByRole('textbox', {name: 'Tin nhắn gửi trợ lý VinFast'});
    await input.fill(text);
    const response = this.page.waitForResponse(r => r.url().endsWith('/api/v1/customer/chat') && r.request().method() === 'POST');
    await this.page.getByRole('button', {name: 'Gửi', exact: true}).click();
    const result = await response;
    expect(result.status()).toBe(200);
    return (await result.json()).data;
  }
}
