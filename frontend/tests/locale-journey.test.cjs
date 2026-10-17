const test = require('node:test');
const assert = require('node:assert/strict');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const {loader} = require('./render-loader.cjs');
const shared = {useAuth: () => ({role: 'GUEST', user: null, isReady: true, registerCustomer() {}}), ProductMark: () => null};
async function setup(role = 'GUEST') {
  const load = await loader({
    'next/navigation': {useRouter: () => ({push() {}})},
    'next/link': ({children, ...props}) => React.createElement('a', props, children),
    '@/features/shared': {...shared, useAuth: () => ({...shared.useAuth(), role})},
    '@/features/shared/context/AuthContext': shared,
    '@/features/chat/api/chatApi': {},
  });
  const {LocaleProvider} = load('features/shared/context/LocaleContext.tsx');
  return {load, render: Component => renderToStaticMarkup(React.createElement(LocaleProvider, {initialLanguage: 'en'}, React.createElement(Component)))};
}
test('English landing translates its complete static journey and suggested prompts', async () => {
  const {load, render} = await setup();
  const html = render(load('features/landing/components/LandingPage.tsx').LandingPage);
  for (const text of ['Ask the assistant', 'Common support topics', 'Charging does not start (CC01)', 'Quick start']) assert.ok(html.includes(text), text);
  assert.match(html, /placeholder="The charger shows red error CC01/);
  assert.doesNotMatch(html, /[\u00c0-\u1ef9]/u);
});
test('English registration translates notices and associates every field with a label', async () => {
  const {load, render} = await setup();
  const html = render(load('app/register/page.tsx').default);
  assert.match(html, /Create a customer account/);
  for (const id of ['register-name', 'register-username', 'register-vehicle', 'register-password', 'register-confirm-password']) {
    assert.match(html, new RegExp(`for="${id}"`));
    assert.match(html, new RegExp(`id="${id}"`));
  }
  assert.match(html, /Complete registration/);
  assert.doesNotMatch(html, /[\u00c0-\u1ef9]/u);
});
for (const role of ['GUEST', 'CUSTOMER']) test(`English staff gate translates ${role} role and return action`, async () => {
  const {load, render} = await setup(role);
  const html = render(load('features/console/components/StaffGuardGate.tsx').StaffGuardGate);
  assert.match(html, /Restricted staff access/);
  assert.match(html, role === 'CUSTOMER' ? /Vehicle owner/ : /Guest/);
  assert.match(html, role === 'CUSTOMER' ? /Back to Support Center/ : /Back to home/);
  assert.doesNotMatch(html, /[\u00c0-\u1ef9]/u);
});
test('English profile translates visible labels, placeholders and actions', async () => {
  const fs = require('node:fs'), vm = require('node:vm'), ts = require('typescript');
  const load = await loader();
  const {LocaleProvider} = load('features/shared/context/LocaleContext.tsx');
  let cursor = 0;
  const module = {exports: {}};
  const source = fs.readFileSync(require.resolve('../src/features/shared/components/UserProfileModal.tsx'), 'utf8');
  vm.runInNewContext(ts.transpileModule(source, {compilerOptions: {module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true}}).outputText, {
    module, exports: module.exports, document: {body: {}}, require(id) {
      if (id === 'react') return {...React, useState: initial => React.useState(cursor++ === 0 ? true : initial)};
      if (id === 'react-dom') return {createPortal: content => content};
      if (id.endsWith('/AuthContext')) return {useAuth: () => ({user: {id:'abc',email:'owner@example.com',name:'Owner'}, updateProfile() {}})};
      if (id.endsWith('/LocaleContext')) return load('features/shared/context/LocaleContext.tsx');
      return require(id);
    },
  });
  const html = renderToStaticMarkup(React.createElement(LocaleProvider, {initialLanguage:'en'}, React.createElement(module.exports.UserProfileModal, {isOpen:true,onClose(){}})));
  assert.match(html, /Save changes/);
  assert.match(html, /Vehicle owner/);
  assert.match(html, /aria-label="Close"/);
  assert.doesNotMatch(html, /[\u00c0-\u1ef9]/u);
});

async function landingHandlers({language = 'en', prompt = '', image = null} = {}) {
  const fs = require('node:fs'), vm = require('node:vm'), ts = require('typescript');
  const translate = (await loader())('features/shared/context/LocaleContext.tsx').translate;
  const stored = {}, navigations = [], states = [prompt, '', 0, false, image, image ? 'dashboard.jpg' : null];
  let cursor = 0;
  const module = {exports: {}};
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(require.resolve('../src/features/landing/components/LandingPage.tsx'), 'utf8'), {compilerOptions: {module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true}}).outputText, {
    module, exports: module.exports, URLSearchParams,
    sessionStorage: {setItem: (key, value) => stored[key] = value, removeItem: key => delete stored[key]},
    require(id) {
      if (id === 'react') return {...React, useState: initial => {const i = cursor++; if (!(i in states)) states[i] = initial; return [states[i], value => states[i] = value];}, useMemo: fn => fn(), useRef: initial => ({current:initial}), useEffect() {}};
      if (id === 'next/navigation') return {useRouter: () => ({push: url => navigations.push(url)})};
      if (id.endsWith('/LocaleContext')) return {useLocale: () => ({language, t: text => translate(text, language)})};
      if (id.endsWith('/AuthContext')) return {useAuth: () => ({role:'GUEST',user:null})};
      if (id.endsWith('/chatApi')) return {};
      return require(id);
    },
  });
  function nodes(node) {if (!node || typeof node !== 'object') return []; if (Array.isArray(node)) return node.flatMap(nodes); return [node, ...nodes(node.props?.children)];}
  function text(node) {if (Array.isArray(node)) return node.map(text).join(''); if (!node || typeof node === 'boolean') return ''; return typeof node === 'object' ? text(node.props?.children) : String(node);}
  const tree = module.exports.LandingPage();
  return {click(label) {const button = nodes(tree).find(node => node.type === 'button' && text(node).includes(label)); assert.ok(button, label); button.props.onClick();}, assertPrompt(expected) {assert.equal(stored.vf_initial_prompt, expected); assert.equal(new URL(navigations.at(-1), 'https://example.test').searchParams.get('prompt'), expected);}, stored};
}
for (const [label, expected] of [
  ['Ask the assistant','The charger shows red error CC01 and will not charge...'],
  ['Charging does not start (CC01)','The VinFast charger is connected but shows red error CC01 and will not charge.'],
  ['Battery & charging','The VinFast charger shows red error CC01 and will not charge.'],
  ['Ask AI about this','Tell me about: VinFast DC charging & EV battery services'],
]) test(`English landing submits localized generated preset: ${label}`, async () => {
  const h = await landingHandlers(); h.click(label); h.assertPrompt(expected);
});
test('English landing submits localized image prompt and retains image', async () => {
  const h = await landingHandlers({image:'data:image/png;base64,photo'}); h.click('Ask the assistant');
  h.assertPrompt('Please check the visible warnings in this dashboard photo.');
  assert.equal(h.stored.vf_initial_image, 'data:image/png;base64,photo');
});
test('English landing preserves typed Vietnamese even if it matches a translated preset', async () => {
  const prompt = 'Trụ sạc báo đỏ lỗi CC01, không vào điện...';
  const h = await landingHandlers({prompt}); h.click('Ask the assistant'); h.assertPrompt(prompt);
});
test('Vietnamese landing submits the Vietnamese generated default', async () => {
  const h = await landingHandlers({language:'vi'}); h.click('Hỏi trợ lý'); h.assertPrompt('Trụ sạc báo đỏ lỗi CC01, không vào điện...');
});

test('English staff navigation and queue feedback use translated copy', async () => {
  const {translate} = (await loader())('features/shared/context/LocaleContext.tsx');
  for (const [vi, en] of [
    ['Đang tải hàng đợi…','Loading queue…'], ['Không thể tải hàng đợi','Unable to load queue'],
    ['Không thể tải hàng đợi. Vui lòng thử lại.','Unable to load the queue. Please try again.'],
    ['Hệ thống trực tuyến','System online'], ['Hàng đợi xử lý','Work queue'], ['Tổng quan ca trực','Shift overview'],
    ['Lịch sử hồ sơ','Case history'], ['Bộ phận / Routing','Departments / Routing'], ['Hồ sơ Staff','Staff profile'],
  ]) assert.equal(translate(vi,'en'), en);
});
