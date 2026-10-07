const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

function harness({ sendChatMessage, getSessionHistory, initialStorage = {} }) {
  const states = [];
  const effectCallbacks = [];
  const storage = { ...initialStorage };

  const source = fs.readFileSync(path.join(__dirname, '../src/features/chat/hooks/useChat.ts'), 'utf8');
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText;

  const module = { exports: {} };
  vm.runInNewContext(compiled, {
    module,
    exports: module.exports,
    Date,
    Math,
    crypto: { randomUUID: () => 'test-req-id' },
    setTimeout: (cb) => cb(),
    window: {
      addEventListener: () => {},
      removeEventListener: () => {},
    },
    localStorage: {
      getItem: (k) => storage[k] || null,
      setItem: (k, v) => { storage[k] = String(v); },
      removeItem: (k) => { delete storage[k]; },
    },
    require: (id) => {
      if (id === 'react') return {
        useState: (initial) => {
          const index = states.length;
          states.push(typeof initial === 'function' ? initial() : initial);
          return [states[index], (value) => {
            states[index] = typeof value === 'function' ? value(states[index]) : value;
          }];
        },
        useEffect: (cb) => {
          effectCallbacks.push(cb);
        },
        useRef: (initial) => ({ current: initial }),
      };
      if (id === '../api/chatApi') return {
        sendChatMessage: sendChatMessage || (async () => ({ success: true, data: {} })),
        getSessionHistory: getSessionHistory || (async () => ({ success: true, data: { messages: [] } })),
        getCaseStatus: async () => ({ success: true, data: { status: 'New' } }),
        acknowledgeCaseSafety: async () => ({ success: true }),
      };
      if (id === '../constants') return { checkHardEmergency: () => false };
      throw new Error(`Unexpected import: ${id}`);
    },
  });

  const hook = module.exports.useChat();
  return { hook, states, effectCallbacks, storage };
}

test('useChat hydrates messages from restored session', async () => {
  const historyData = {
    session_id: 'sess_vf_restored1',
    case_id: 'CASE-20261006-001',
    messages: [
      { id: 'msg-1', sender: 'CUSTOMER', content: 'Xe báo lỗi sạc', timestamp: '2026-10-06T10:00:00Z' },
      { id: 'msg-2', sender: 'AGENT', content: 'Em ghi nhận sự cố sạc', timestamp: '2026-10-06T10:00:05Z' },
    ],
    total: 2,
  };

  let historySessionQueried = null;
  const { states, effectCallbacks } = harness({
    initialStorage: {
      'vf_chat_session:guest': 'sess_vf_restored1',
    },
    getSessionHistory: async (sid) => {
      historySessionQueried = sid;
      return { success: true, data: historyData };
    },
  });

  // Chạy mount effects
  for (const cb of effectCallbacks) {
    await cb();
  }

  // Đợi microtasks nếu có
  await new Promise((r) => setTimeout(r, 10));

  assert.equal(historySessionQueried, 'sess_vf_restored1');
  const messages = states[0];
  assert.equal(messages.length, 2);
  assert.equal(messages[0].content, 'Xe báo lỗi sạc');
  assert.equal(messages[1].content, 'Em ghi nhận sự cố sạc');
});

test('useChat dismisses location request card when switching topic', async () => {
  let locationReqState = null;
  const { hook, states } = harness({
    sendChatMessage: async () => ({
      success: true,
      data: {
        message: 'BMS là hệ thống quản lý pin',
        request_location: false,
      },
    }),
  });

  // Giả lập trạng thái trước đó requestLocation = true
  states[9] = true; // requestLocation index trong useState

  await hook.sendMessage('BMS là gì?');

  // requestLocation phải được đặt về false
  assert.equal(states[9], false);
});
