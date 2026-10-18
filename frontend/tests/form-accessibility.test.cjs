const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
function load(path, overrides = {}) {
  const module = {exports: {}};
  const source = fs.readFileSync(require.resolve(path), 'utf8');
  vm.runInNewContext(ts.transpileModule(source, {compilerOptions: {
    module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
  }}).outputText, {module, exports: module.exports, require: name => overrides[name] || (name.endsWith('/LocaleContext') ? {useLocale: () => ({language: "vi", setLanguage() {}, t: text => text}), translate: text => text} : require(name))});
  return module.exports;
}
test('chat and image inputs expose accessible names', () => {
  const {ChatInputBar} = load('../src/features/chat/components/ChatInputBar.tsx');
  const html = renderToStaticMarkup(React.createElement(ChatInputBar, {input: '', onSend() {}, onChangeInput() {}}));
  assert.match(html, /type="text"[^>]*aria-label="Tin nhắn/);
  assert.match(html, /type="file"[^>]*aria-label="Tải ảnh/);
});
test('login labels target real fields with autocomplete', () => {
  const {default: Login} = load('../src/app/login/page.tsx', {
    'next/navigation': {useRouter: () => ({push() {}})},
    'next/link': ({children, ...props}) => React.createElement('a', props, children),
    '@/features/shared': {useAuth: () => ({login() {}, logout() {}}), ProductMark: () => null},
  });
  const html = renderToStaticMarkup(React.createElement(Login));
  for (const id of ['login-identifier', 'login-password']) {
    assert.match(html, new RegExp('for="' + id + '"'));
    assert.match(html, new RegExp('id="' + id + '"'));
  }
  assert.match(html, /autoComplete="current-password"/i);
});
