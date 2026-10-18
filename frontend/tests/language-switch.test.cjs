const test=require('node:test');
const assert=require('node:assert/strict');
const React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');
const {loader}=require('./render-loader.cjs');

for(const language of ['vi','en']) test(`language switch presents two pressed buttons for ${language}`,async()=>{
  const load=await loader();
  const {LocaleProvider}=load('features/shared/context/LocaleContext.tsx');
  const {LanguageSwitch}=load('features/shared/components/LanguageSwitch.tsx');
  const html=renderToStaticMarkup(React.createElement(LocaleProvider,{initialLanguage:language},React.createElement(LanguageSwitch)));
  assert.match(html,/role="group"/);
  assert.equal((html.match(/type="button"/g)||[]).length,2);
  assert.equal((html.match(/aria-pressed="true"/g)||[]).length,1);
  assert.match(html,new RegExp(`aria-pressed="true"[^>]*>${language.toUpperCase()}<`));
  assert.doesNotMatch(html,/<select/);
});
test('language switch uses the existing locale setter',async()=>{
  const chosen=[];
  const load=await loader({'@/features/shared/context/LocaleContext':{useLocale:()=>({language:'vi',setLanguage:value=>chosen.push(value)})}});
  const {LanguageSwitch}=load('features/shared/components/LanguageSwitch.tsx');
  const tree=LanguageSwitch();
  tree.props.children[1].props.onClick();
  assert.deepEqual(chosen,['en']);
});
