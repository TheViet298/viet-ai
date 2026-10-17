import { test, expect } from '@playwright/test';
import fs from 'node:fs';

for (const theme of ['light', 'dark']) for (const language of ['vi', 'en']) {
  test(`guest contrast and chat targets: ${theme}/${language}`, async ({page}) => {
    await page.addInitScript(({theme, language}) => {
      localStorage.setItem('vf_theme',theme);
      localStorage.setItem('vf_language',language);
    }, {theme,language});
    for (const route of ['/', '/login', '/register', '/chat', '/track-case', '/console']) {
      await page.goto(route);
      await page.waitForFunction(language => document.documentElement.lang === language, language);
      await page.waitForFunction(() => document.getAnimations().every(animation =>
        animation.playState !== 'running' || !Number.isFinite(animation.effect?.getComputedTiming().endTime)));
      await page.addScriptTag({content:fs.readFileSync(require.resolve('axe-core/axe.min.js'),'utf8')});
      const violations = await page.evaluate(async () => {
        const axe=(window as any).axe;
        return (await axe.run(document,{runOnly:{type:'rule',values:['color-contrast','target-size','select-name']}})).violations;
      });
      expect(violations, `${route} ${theme}/${language}`).toEqual([]);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      if (route === '/chat' && (page.viewportSize()?.width || 0) < 1024) {
        const history=page.getByTitle(language === 'en' ? 'Conversation history' : 'Lịch sử cuộc trò chuyện',{exact:true});
        await expect(history).toBeVisible();
        const reachable=await history.evaluate(button=>{
          const rect=button.getBoundingClientRect();
          return [0.15,0.5,0.85].every(x=>[0.15,0.5,0.85].every(y=>button.contains(document.elementFromPoint(rect.x+rect.width*x,rect.y+rect.height*y))));
        });
        expect(reachable, 'History button must remain unobscured').toBe(true);
        await history.click();
        await expect(page.getByRole('button',{name:language === 'en'?'Collapse sidebar':'Thu gọn sidebar'})).toBeVisible();
      }
    }
  });
}
