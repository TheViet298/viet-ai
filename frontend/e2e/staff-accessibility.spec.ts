import {test, expect} from '@playwright/test';
import fs from 'node:fs';

test('staff queue and real case detail have named controls and readable text',async({page})=>{
 test.skip(!process.env.QA_STAFF_USERNAME||!process.env.QA_STAFF_PASSWORD||!process.env.QA_CASE_ID,'Requires isolated QA staff account and seeded case');
 await page.addInitScript(()=>localStorage.setItem('vf_language','en'));
 await page.goto('/login');
 await page.getByRole('button',{name:'Technician (Staff)',exact:true}).click();
 await page.locator('#login-identifier').fill(process.env.QA_STAFF_USERNAME!);
 await page.locator('#login-password').fill(process.env.QA_STAFF_PASSWORD!);
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await page.waitForURL('**/console');
 const item=page.getByText(process.env.QA_CASE_ID!,{exact:true}).first();
 await expect(item).toBeVisible();
 await item.click();
 await page.waitForFunction(()=>!document.body.innerText.includes('Loading case details'));
 await page.addScriptTag({content:fs.readFileSync(require.resolve('axe-core/axe.min.js'),'utf8')});
 const violations=await page.evaluate(async()=>{
  return (await (window as any).axe.run(document,{runOnly:{type:'rule',values:['button-name','color-contrast','select-name']}})).violations;
 });
 expect(violations).toEqual([]);
});
