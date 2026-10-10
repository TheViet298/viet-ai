const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

function load(relative, overrides = {}) {
  const code = ts.transpileModule(fs.readFileSync(path.join(__dirname, relative), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText;
  const module = { exports: {} };
  const scope = { module, exports: module.exports, process: { env: {} }, window: {},
    localStorage: { getItem: () => null }, FormData, AbortSignal, ...overrides };
  vm.runInNewContext(code, scope);
  return module.exports;
}

test('Guest upload is rejected without login or upload network requests', async () => {
  const calls = [];
  const api = load('../src/features/chat/api/chatApi.ts', {
    fetch: async (...args) => { calls.push(args); return { ok: true, json: async () => ({ data: { token: 'demo-token' } }) }; },
  });
  await assert.rejects(api.uploadAttachment(new Blob(['image'])), /đăng nhập/i);
  assert.equal(calls.length, 0);
});

test('logged-in upload sends file with existing customer token', async () => {
  const calls = [];
  const api = load('../src/features/chat/api/chatApi.ts', {
    localStorage: { getItem: () => 'customer-token' },
    fetch: async (url, options) => { calls.push({ url, options }); return { ok: true, json: async () => ({ success: true }) }; },
  });
  await api.uploadAttachment(new Blob(['image']), 'auto');
  assert.equal(calls.length, 1);
  assert.equal(calls[0].options.headers.Authorization, 'Bearer customer-token');
  assert.equal(calls[0].options.body.get('image_kind'), 'auto');
});

test('Guest chat supplies guest identity instead of automatically authenticating', async () => {
  const calls = [];
  const api = load('../src/features/chat/api/chatApi.ts', {
    fetch: async (url, options) => { calls.push({ url, options }); return { ok: true, json: async () => ({ success: true }) }; },
  });
  await api.sendChatMessage({ sessionId: 'guest-test', message: 'xin chào' });
  assert.equal(calls.length, 1);
  assert.equal(JSON.parse(calls[0].options.body).guest_session_id, 'guest-test');
  assert.equal(calls[0].options.headers.Authorization, undefined);
});

test('failed known-type analysis is blocked and reports a service error', () => {
  const { getUploadError } = load('../src/features/chat/uploadState.ts');
  const message = getUploadError({ analysis_status: 'FAILED', detected_signals: {
    image_kind: 'dashboard', analysis_error: 'vision_request_failed',
  }});
  assert.match(message, /dịch vụ|hệ thống/i);
});

test('uncertain image and unavailable service receive different guidance', () => {
  const { getUploadError } = load('../src/features/chat/uploadState.ts');
  const uncertain = getUploadError({ analysis_status: 'FAILED', detected_signals: {
    image_kind: 'unknown', analysis_error: 'routing_uncertain',
  }});
  const unavailable = getUploadError({ analysis_status: 'FAILED', detected_signals: {
    image_kind: 'unknown', analysis_error: 'routing_unavailable',
  }});
  assert.match(uncertain, /loại ảnh|ảnh rõ/i);
  assert.match(unavailable, /dịch vụ|hệ thống/i);
  assert.notEqual(uncertain, unavailable);
  assert.equal(getUploadError({ analysis_status: 'ANALYZED', detected_signals: { image_kind: 'exterior' } }), null);
});
