import { test, expect } from '@playwright/test';
import fs from 'node:fs';

test.beforeEach(async ({page}) => {
  await page.emulateMedia({reducedMotion: 'reduce'});
  await page.route('**/api/v1/**', route => route.fulfill({json:{success:true,data:{articles:[],sessions:[],messages:[]},error:null}}));
});

test('Serv follows the real caret on home, preserves multiline typing and supports both languages', async ({page}, testInfo) => {
  await page.goto('/');
  const serv=page.locator('[data-serv]');
  await expect(serv).toHaveCount(1);
  await expect(serv.locator('[data-serv-speech]')).toBeVisible();
  expect(await serv.evaluate(e=>getComputedStyle(e,'::before').backgroundImage)).toContain('radial-gradient');
  await page.getByRole('button',{name:'Chào Serv',exact:true}).click();
  await expect(serv).toHaveAttribute('data-state','hello');
  const input=page.getByRole('textbox',{name:'Mô tả câu hỏi hoặc sự cố xe',exact:true});
  await input.fill('Xe VF 6 của tôi không nhận sạc.\nTôi cần kiểm tra điều gì trước?');
  await expect(serv).toHaveAttribute('data-state','listen');
  await expect(serv).toHaveAttribute('data-gaze-source','caret');
  await input.press('Control+Home');
  await input.evaluate(()=>new Promise<void>(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve()))));
  await expect.poll(()=>serv.evaluate(e=>parseFloat((e as HTMLElement).style.getPropertyValue('--gx')))).toBeLessThan(0);
  const left=await serv.evaluate(e=>(e as HTMLElement).style.getPropertyValue('--gx'));
  await input.press('Control+End');
  await expect.poll(()=>serv.evaluate(e=>(e as HTMLElement).style.getPropertyValue('--gx'))).not.toBe(left);
  await input.evaluate(field=>{ if (field instanceof HTMLTextAreaElement) field.setSelectionRange(0,field.value.length,'backward'); });
  await expect.poll(()=>serv.evaluate(e=>(e as HTMLElement).style.getPropertyValue('--gx'))).toBe(left);
  await input.press('Control+End');
  await expect.poll(()=>serv.evaluate(e=>(e as HTMLElement).style.getPropertyValue('--gx'))).not.toBe(left);
  const caret=await serv.evaluate(e=>(e as HTMLElement).style.getPropertyValue('--gx'));
  await page.mouse.move(2,2);
  await expect.poll(()=>serv.evaluate(e=>(e as HTMLElement).style.getPropertyValue('--gx'))).toBe(caret);
  await input.press('Shift+Enter');
  expect(await input.inputValue()).toContain('\n');
  await input.dispatchEvent('compositionstart');
  await input.press('Enter');
  await expect(page).toHaveURL(/\/$/);
  await input.dispatchEvent('compositionend');
  await page.screenshot({path:`../.impeccable/review/serv-home-${testInfo.project.name}.png`,animations:'disabled'});
  await page.getByRole('button',{name:'English',exact:true}).click();
  await page.getByRole('textbox').first().focus();
  await expect(page.getByRole('button',{name:'Say hello to Serv',exact:true})).toBeVisible();
  await expect(serv).toContainText('Serv is listening');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

test('Serv uses real chat request states and an error cannot become a result', async ({page},testInfo) => {
  let finish: (()=>void) | undefined;
  let requestNumber=0;
  await page.route('**/api/v1/customer/chat',async route=>{
    requestNumber++;
    if(requestNumber===1){
      await new Promise<void>(resolve=>{finish=resolve;});
      await route.fulfill({json:{success:true,data:{language:'vi',response_type:'FAQ_ANSWER',message:'Phản hồi kiểm thử: vui lòng kiểm tra hướng dẫn sử dụng của xe.',citations:[],suggested_replies:[]},error:null}});
    }else await route.fulfill({status:503,json:{detail:'QA simulated unavailable'}});
  });
  await page.goto('/chat');
  const serv=page.locator('[data-serv]'),input=page.getByRole('textbox',{name:'Tin nhắn gửi trợ lý VinFast',exact:true});
  await expect(serv).toHaveCount(1);await expect(input).toBeVisible();
  await expect(serv.locator('[data-serv-speech]')).toHaveCount(0);
  expect(await serv.locator('.arm').first().evaluate(e=>getComputedStyle(e).display)).toBe('none');
  expect(await serv.locator('.feet').evaluate(e=>getComputedStyle(e).display)).toBe('none');
  expect(await serv.evaluate(e=>getComputedStyle(e,'::before').display)).toBe('none');
  const header=await page.locator('[data-chat-header]').boundingBox();
  expect(header!.height).toBeGreaterThanOrEqual(55);
  expect(header!.height).toBeLessThanOrEqual(60);
  await input.fill('Cách dùng ứng dụng VinFast?');await expect(serv).toHaveAttribute('data-state','listen');
  await input.press('Shift+Enter');expect(await input.inputValue()).toContain('\n');
  await input.press('Enter');await expect(serv).toHaveAttribute('data-state','think');
  await expect(serv).toHaveAttribute('data-state','search',{timeout:5000});
  expect(finish).toBeTruthy();finish!();
  await expect(serv).toHaveAttribute('data-state','present');
  await expect(page.getByText('Phản hồi kiểm thử: vui lòng kiểm tra hướng dẫn sử dụng của xe.',{exact:true})).toBeVisible();
  await page.screenshot({path:`../.impeccable/review/serv-chat-${testInfo.project.name}.png`,animations:'disabled'});
  await input.fill('Thử lỗi kết nối');await input.press('Enter');
  await expect(serv).toHaveAttribute('data-state','care');
  await page.getByRole('button',{name:'Chào Serv',exact:true}).click();await expect(serv).toHaveAttribute('data-state','care');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

test('Serv has accessible controls and reduced motion in light and dark layouts',async({page})=>{
  const errors: string[]=[];page.on('pageerror',error=>errors.push(error.message));
  for(const route of ['/','/chat']){
    await page.goto(route);await expect(page.locator('[data-serv]')).toBeVisible();
    await page.addScriptTag({content:fs.readFileSync(require.resolve('axe-core/axe.min.js'),'utf8')});
    for(const theme of ['light','dark']){
      const toggle=page.getByRole('button',{name:theme==='light'?'Chuyển sang giao diện sáng':'Chuyển sang giao diện tối',exact:true});
      if(await toggle.count()) await toggle.click();
      const violations=await page.locator('[data-serv]').evaluate(async root=>(await (window as any).axe.run(root,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations);
      expect(violations).toEqual([]);
      expect(await page.locator('[data-serv] .float').evaluate(e=>getComputedStyle(e).animationName)).toBe('none');
    }
  }
  expect(errors).toEqual([]);
});
