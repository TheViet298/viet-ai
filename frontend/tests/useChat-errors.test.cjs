const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

// Exercise the hook's asynchronous transport flow without a browser or a live API.
function harness(sendChatMessage, language = "vi") {
  let preferredLanguage = language;
  const states = [];
  const source = fs.readFileSync(path.join(__dirname, '../src/features/chat/hooks/useChat.ts'), 'utf8');
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(compiled, {
    module, exports: module.exports, Date, Math, crypto: { randomUUID: () => 'test-request' },
    setTimeout: (callback) => callback(),
    require: (id) => {
      if (id.endsWith('/LocaleContext')) return {useLocale: () => ({language, setLanguage: value => {preferredLanguage = value}, t: text => text}), translate: text => text};
      if (id === 'react') return {
        useState: (initial) => {
          const index = states.length;
          states.push(typeof initial === 'function' ? initial() : initial);
          return [states[index], (value) => {
            states[index] = typeof value === 'function' ? value(states[index]) : value;
          }];
        },
        useEffect: () => {},
        useRef: initial => ({ current: initial }),
      };
      if (id === '../api/chatApi') return { sendChatMessage };
      if (id === '../constants') return { checkHardEmergency: (text) => text.includes('mất phanh') };
      throw new Error(`Unexpected import: ${id}`);
    },
  });
  return { hook: module.exports.useChat(), states, preferredLanguage: () => preferredLanguage };
}

for (const [name, text, transport] of [
  ['concept network failure', 'Con rùa vàng là gì?', async () => { throw new Error('offline'); }],
  ['incident network failure', 'Xe tôi bị mất phanh', async () => { throw new Error('offline'); }],
  ['unsuccessful API envelope', 'Giá lăn bánh VF8', async () => ({ success: false })],
  ['missing API payload', 'ADAS là gì?', async () => ({ success: true, data: null })],
]) {
  test(name + ' reports failure without invented evidence or cases', async () => {
    const { hook, states } = harness(transport);
    await hook.sendMessage(text);
    const reply = states[0].at(-1);
    assert.equal(reply.sender, 'AGENT');
    assert.match(reply.content, /chưa nhận được phản hồi/i);
    assert.equal(reply.citations, undefined);
    assert.equal(reply.case_id, undefined);
    assert.equal(states[4], null, 'must not invent a case');
    assert.equal(states[2], false, 'must clear loading');
    assert.equal(states[5], false, 'unconfirmed text must not create a server emergency state');
  });
}

test('successful API response retains server answer and evidence', async () => {
  const data = { message: 'Server answer', case_id: 'REAL-123', citations: [{ source_id: 'verified' }], vehicle_cards: [{ model: 'VF5' }], vehicle_comparison: true };
  const { hook, states } = harness(async () => ({ success: true, data }));
  await hook.sendMessage('Xe bị lỗi');
  assert.equal(states[0].at(-1).content, data.message);
  assert.equal(states[0].at(-1).citations, data.citations);
  assert.equal(states[0].at(-1).vehicle_cards, data.vehicle_cards);
  assert.equal(states[0].at(-1).vehicle_comparison, true);
  assert.equal(states[4], 'REAL-123');
});

test('image-only message shows image while sending routing text and attachment ID to API', async () => {
  let request;
  const { hook, states } = harness(async (payload) => {
    request = payload;
    return { success: true, data: { message: 'Image analyzed' } };
  });
  const image = { src: 'data:image/png;base64,example', name: 'car.png', caption: '' };
  await hook.sendMessage('Internal image routing prompt', ['attachment-1'], image);
  const user = states[0][1];
  assert.equal(user.content, '');
  assert.equal(user.image.src, image.src);
  assert.equal(user.image.name, image.name);
  assert.equal(request.message, 'Internal image routing prompt');
  assert.equal(request.attachmentIds[0], 'attachment-1');
  assert.equal(request.image, undefined, 'preview bytes stay in the UI');
});

test('image message preserves a caption explicitly typed by the user', async () => {
  const { hook, states } = harness(async () => ({ success: true, data: { message: 'Analyzed' } }));
  await hook.sendMessage('Vết này là gì?', ['attachment-2'], {
    src: 'data:image/png;base64,example', name: 'detail.png', caption: 'Vết này là gì?',
  });
  assert.equal(states[0][1].content, 'Vết này là gì?');
  assert.equal(states[0][1].image.name, 'detail.png');
});


test('chat sends no assumed vehicle and welcomes without a default model', async () => {
  let request;
  const { hook, states } = harness(async (payload) => {
    request = payload;
    return { success: true, data: { message: 'Answer' } };
  });
  assert.doesNotMatch(states[0][0].content, /VF8/);
  await hook.sendMessage('VF5 bảo hành bao lâu?');
  assert.equal(request.clientContext.vehicle_model, undefined);
  assert.equal(request.clientContext.vehicle_code_mock, undefined);
});


test('chat sends current locale and adopts the server response language', async () => {
  let request;
  const h = harness(async payload => {request=payload;return {success:true,data:{message:'English response',language:'en'}}}, 'vi');
  await h.hook.sendMessage('Please answer in English');
  assert.equal(request.language, 'vi');
  assert.equal(h.states[0].at(-1).language, 'en');
  assert.equal(h.preferredLanguage(), 'en');
});
