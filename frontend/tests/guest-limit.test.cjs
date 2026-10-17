const test = require('node:test');
const assert = require('node:assert/strict');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { loader } = require('./render-loader.cjs');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

for (const detail of [
  { code: 'GUEST_LIMIT_REACHED', message: 'Đã hết lượt sử dụng' },
  'Quý khách đã sử dụng hết 5 lượt chat thử nghiệm.',
]) test('chat transport identifies the guest limit for current and legacy APIs: ' + typeof detail, async () => {
  const source = fs.readFileSync(require.resolve('../src/features/chat/api/chatApi.ts'), 'utf8');
  const module = { exports: {} };
  vm.runInNewContext(ts.transpileModule(source, {compilerOptions: {module: ts.ModuleKind.CommonJS}}).outputText, {
    module, exports: module.exports, require, process: {env: {}},
    fetch: async () => ({ok: false, status: 403, text: async () => JSON.stringify({detail})}),
  });
  await assert.rejects(module.exports.sendChatMessage({sessionId: 'guest-test', message: 'VF7'}),
    error => error.status === 403 && error.code === 'GUEST_LIMIT_REACHED');
});

test('exhausted guest sees the notice immediately before the composer', async () => {
  const load = await loader({
    '@/features/shared': { useAuth: () => ({ isReady: true, role: 'GUEST' }), ProductMark: () => null },
    '@/features/shared/context/LocaleContext': { useLocale: () => ({ t: text => text }) },
    '../hooks/useChat': { useChat: () => ({ guestLimitReached: true, messages: [], input: '' }) },
    './ChatInputBar': { ChatInputBar: () => React.createElement('textarea', { 'aria-label': 'Chat composer' }) },
    './ChatFeed': { ChatFeed: () => null },
    './ChatHistorySidebar': { ChatHistorySidebar: () => null },
    'next/link': { __esModule: true, default: ({ children }) => React.createElement('a', null, children) },
  });
  const { CustomerChatContainer } = load('features/chat/components/CustomerChatContainer.tsx');
  const html = renderToStaticMarkup(React.createElement(CustomerChatContainer));
  assert.match(html, /role="alert"[^>]*>Quý khách đã hết lượt sử dụng, cần phải đăng nhập để sử dụng tiếp dịch vụ<\/p><textarea/);
});
