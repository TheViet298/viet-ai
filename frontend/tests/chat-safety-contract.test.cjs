const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

test('new vehicle polling keeps old danger and acknowledges the danger case', async () => {
  const danger = { case_id: 'old-danger', incident_version: 2, safety_status: 'unconfirmed' };
  const h = harness({
    getCaseStatus: async () => ({ success: true, data: { case_id: 'new-car', status: 'Staff Reviewing', priority: 'HIGH', incident_version: 1, emergency_context: danger } }),
    acknowledgeCaseSafety: async (id, version) => {
      assert.equal(id, 'old-danger'); assert.equal(version, 2);
      return { success: true, data: { case_id: id, incident_version: version, safety_status: 'customer_reported_safe' } };
    },
  }, { caseId: 'new-car' }, true);
  h.render(); h.render();
  await h.poll();
  assert.equal(h.render().criticalBanner, true);
  await h.render().dismissCriticalBanner();
  assert.equal(h.render().criticalBannerDismissed, true);
});

function harness(api, context, effectsEnabled = false, simulateServer = false, storage) {
  const slots = []; let cursor = 0;
  let interval;
  const effects = [];
  const queued = [];
  const source = fs.readFileSync(path.join(__dirname, '../src/features/chat/hooks/useChat.ts'), 'utf8');
  const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
  const module = { exports: {} };
  let removed = 0;
  const browserWindow = { addEventListener: () => {}, removeEventListener: () => {} };
  const scope = {
    module, exports: module.exports, Date, Math, crypto: { randomUUID: () => 'request-test' },
    setTimeout: fn => fn(), setInterval: fn => { interval = fn; return 1; }, clearInterval: () => {},
    window: simulateServer ? undefined : browserWindow,
    localStorage: storage || { getItem: key => simulateServer ? (key === 'vf_customer_token' ? 'demo-token' : 'real') : null, setItem: () => {}, removeItem: () => { removed++; } },
    require: id => {
      if (id === 'react') return {
        useState: initial => { const i = cursor++; if (!(i in slots)) slots[i] = typeof initial === 'function' ? initial() : initial;
          return [slots[i], val => { slots[i] = typeof val === 'function' ? val(slots[i]) : val; }]; },
        useRef: initial => { const i = cursor++; if (!(i in slots)) slots[i] = { current: initial }; return slots[i]; },
        useEffect: (fn, deps) => { const i = cursor++; if (!effectsEnabled) return;
          if (!effects[i] || deps.some((v, n) => v !== effects[i].deps[n])) {
            queued.push(() => { effects[i]?.cleanup?.(); effects[i] = { deps, cleanup: fn() }; });
          }
        },
      };
      if (id === '../api/chatApi') return api;
      if (id === '../constants') return { checkHardEmergency: () => true };
      throw Error(id);
    },
  };
  vm.runInNewContext(compiled, scope);
  const render = () => { cursor = 0; const hook = module.exports.useChat(context); scope.window = browserWindow; queued.splice(0).forEach(fn => fn()); return hook; };
  return { render, slots, poll: () => interval(), removed: () => removed };
}

test('normal server response never flashes a local emergency before receipt', async () => {
  let finish;
  const h = harness({ sendChatMessage: () => new Promise(resolve => { finish = resolve; }) });
  const pending = h.render().sendMessage('Xe dang chay binh thuong');
  assert.equal(h.render().criticalBanner, false);
  finish({ success: true, data: { message: 'Normal', show_emergency_banner: false } });
  await pending;
  assert.equal(h.render().criticalBanner, false);
});

test('safe acknowledgement waits for backend and errors keep emergency visible', async () => {
  let reject;
  const h = harness({
    sendChatMessage: async () => ({ success: true, data: { message: 'Safety', case_id: 'real', priority: 'CRITICAL', show_emergency_banner: true, incident_version: 1, safety_status: 'unconfirmed' } }),
    acknowledgeCaseSafety: () => new Promise((_, bad) => { reject = bad; }),
  });
  await h.render().sendMessage('Xe bốc khói');
  const pending = h.render().dismissCriticalBanner();
  assert.equal(h.render().criticalBannerDismissed, false);
  reject(Error('offline'));
  await pending;
  assert.equal(h.render().criticalBannerDismissed, false);
  assert.match(h.render().safetyError, /chưa/i);
});

test('successful acknowledgement persists and a fresh incident resets ribbon', async () => {
  let version = 1;
  let calls = 0;
  const h = harness({
    sendChatMessage: async () => ({ success: true, data: { message: 'Safety', case_id: 'real', priority: 'CRITICAL', show_emergency_banner: true, incident_version: version, safety_status: 'unconfirmed' } }),
    acknowledgeCaseSafety: async (id, v) => { calls++; assert.equal(id, 'real'); assert.equal(v, 1); return { success: true, data: { case_id: id, incident_version: v, safety_status: 'customer_reported_safe' } }; },
  });
  await h.render().sendMessage('Xe bốc khói');
  await h.render().dismissCriticalBanner();
  assert.equal(calls, 1);
  assert.equal(h.render().criticalBannerDismissed, true);
  version = 2;
  await h.render().sendMessage('Xe lại bốc khói');
  assert.equal(h.render().criticalBannerDismissed, false);
});

test('old status poll cannot hide a newer critical turn', async () => {
  let finishSend;
  const polls = [];
  const h = harness({
    getCaseStatus: () => new Promise(resolve => polls.push(resolve)),
    sendChatMessage: () => new Promise(resolve => { finishSend = resolve; }),
  }, { caseId: 'real' }, true);
  h.render();
  h.render();
  polls.shift()({ success: true, data: { case_id: 'real', status: 'Staff Reviewing', priority: 'MEDIUM', incident_version: 1 } });
  await Promise.resolve();
  const sending = h.render().sendMessage('Xe bốc khói');
  const polling = h.poll();
  finishSend({ success: true, data: { message: 'Safety', case_id: 'real', priority: 'CRITICAL', incident_version: 2, show_emergency_banner: true } });
  await sending;
  assert.equal(h.render().criticalBanner, true);
  polls.shift()({ success: true, data: { case_id: 'real', status: 'Staff Reviewing', priority: 'MEDIUM', incident_version: 1 } });
  await polling;
  assert.equal(h.render().criticalBanner, true);
});

test('response from reset conversation cannot repopulate it', async () => {
  let finish;
  const h = harness({ sendChatMessage: () => new Promise(resolve => { finish = resolve; }) });
  const pending = h.render().sendMessage('Xe bốc khói');
  h.render().resetChat();
  finish({ success: true, data: { message: 'Safety', case_id: 'old', priority: 'CRITICAL', show_emergency_banner: true } });
  await pending;
  assert.equal(h.render().currentCaseId, null);
  assert.equal(h.render().criticalBanner, false);
  assert.equal(h.render().messages.length, 1);
});

test('browser hydration restores stored case before persistence can erase it', async () => {
  const h = harness({ getCaseStatus: async () => ({ success: true, data: { case_id: 'real', priority: 'CRITICAL', status: 'In Progress', incident_version: 1, safety_status: 'customer_reported_safe' } }) }, undefined, true, true);
  assert.equal(h.render().currentCaseId, null);
  assert.equal(h.render().currentCaseId, 'real');
  await h.poll();
  assert.equal(h.render().criticalBanner, true);
  assert.equal(h.render().criticalBannerDismissed, true);
  assert.equal(h.removed(), 0);
});

test('reload continues the same memory session and reset starts another', async () => {
  const saved = new Map([['vf_customer_token', 'customer-test']]);
  const storage = { getItem: key => saved.get(key) || null, setItem: (key, value) => saved.set(key, value), removeItem: key => saved.delete(key) };
  const sent = [];
  const api = {
    sendChatMessage: async payload => { sent.push(payload); return { success: true, data: { message: 'Recorded', case_id: 'existing-case' } }; },
    getCaseStatus: async () => ({ success: true, data: { case_id: 'existing-case', status: 'New', priority: 'HIGH' } }),
  };
  const first = harness(api, undefined, true, false, storage);
  first.render(); first.render();
  await first.render().sendMessage('Xe VF8 không sạc được, trụ P04, lỗi CC04');
  first.render();
  const reloaded = harness(api, undefined, true, false, storage);
  reloaded.render(); reloaded.render();
  await reloaded.render().sendMessage('Xe vẫn không sạc được');
  assert.equal(sent[1].sessionId, sent[0].sessionId, 'reload must keep server memory namespace');
  assert.equal(sent[1].caseId, 'existing-case');
  reloaded.render().resetChat(); reloaded.render();
  await reloaded.render().sendMessage('Một cuộc trò chuyện mới');
  assert.notEqual(sent[2].sessionId, sent[0].sessionId);
  assert.equal(sent[2].caseId, null);
});
