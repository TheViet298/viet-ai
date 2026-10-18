const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

test('welcome initialization does not read the clock; mount timestamp can be supplied', () => {
  const source = fs.readFileSync(path.join(__dirname, '../src/features/chat/hooks/useChat.ts'), 'utf8');
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
  const exports = {};
  vm.runInNewContext(code, {
    exports,
    Date: class { constructor() { throw new Error('Clock read before mount'); } },
    require: id => {
      if (id.includes('LocaleContext')) return { translate: s => s, useLocale: () => ({ language: 'vi', t: s => s }) };
      return {};
    }
  });
  assert.equal(exports.createWelcomeMessage().timestamp, '');
  assert.equal(exports.INITIAL_WELCOME_MESSAGE.timestamp, '');
  assert.equal(exports.createWelcomeMessage({}, '2026-10-13T12:34:00Z').timestamp, '2026-10-13T12:34:00Z');
});

test('message render uses supplied timestamp and remains blank until mount', () => {
  const source = fs.readFileSync(path.join(__dirname, '../src/features/chat/components/ChatMessageItem.tsx'), 'utf8');
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText;
  let mounted = false;
  const exports = {};
  const jsx = (type, props) => ({ type, props });
  vm.runInNewContext(code, {
    exports,
    Date,
    Number,
    require: id => {
      if (id === 'react') return { useMemo: fn => fn(), useState: () => [mounted, () => {}], useEffect() {} };
      if (id === 'react/jsx-runtime') return { jsx, jsxs: jsx };
      if (id.includes('LocaleContext')) return { useLocale: () => ({ language: 'vi', t: s => s }) };
      if (id.includes('utils')) return { parseServerTimestamp: s => new Date(s) };
      return {};
    }
  });
  const props = { message: { sender: 'CUSTOMER', timestamp: '2026-10-13T12:34:00Z', content: 'Test' }, isLastMessage: false, onSelectReply() {} };
  const findTime = node => {
    if (!node || typeof node !== 'object') return null;
    if (node.type === 'time') return node;
    return [node.props?.children].flat().map(findTime).find(Boolean);
  };
  assert.equal(findTime(exports.ChatMessageItem(props)).props.children, '');
  mounted = true;
  const first = findTime(exports.ChatMessageItem(props));
  assert.equal(first.props.dateTime, props.message.timestamp);
  assert.equal(first.props.children, new Date(props.message.timestamp).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }));
  assert.equal(findTime(exports.ChatMessageItem(props)).props.children, first.props.children);
});
