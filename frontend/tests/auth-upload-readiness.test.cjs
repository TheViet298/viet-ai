const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

function harness(fetch, initial = {}) {
  const storage = new Map(Object.entries(initial));
  const states = [], refs = [], effects = [];
  let index = 0, refIndex = 0;
  const react = {
    createContext: () => ({ Provider: 'provider' }), useContext: () => {},
    useState: (initial) => { const i = index++; if (!(i in states)) states[i] = initial;
      return [states[i], (value) => { states[i] = value; }]; },
    useRef: (initial) => { const i = refIndex++; return refs[i] ||= { current: initial }; },
    useEffect: (effect) => { if (!effects.length) effects.push(effect); },
  };
  const code = ts.transpileModule(fs.readFileSync(require.resolve('../src/features/shared/context/AuthContext.tsx'), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(code, { module, exports: module.exports, process: { env: {} }, fetch,
    localStorage: { getItem: (key) => storage.get(key) || null,
      setItem: (key, value) => storage.set(key, value), removeItem: (key) => storage.delete(key) },
    require: (name) => name === 'react' ? react : { jsx: (_type, props) => props },
  });
  const render = () => { index = refIndex = 0; return module.exports.AuthProvider({ children: null }).value; };
  render(); effects[0]();
  return { render, storage };
}

test('upload role becomes customer only after the login token arrives', async () => {
  let resolve;
  const app = harness(() => new Promise((done) => { resolve = done; }));
  const pending = app.render().loginAs('CUSTOMER');
  assert.equal(app.render().role, 'GUEST');
  resolve({ ok: true, json: async () => ({ data: { token: 'token' } }) });
  assert.equal(await pending, true);
  assert.equal(app.render().role, 'CUSTOMER');
  assert.equal(app.storage.get('vf_customer_token'), 'token');
});

test('failed login and tokenless stored profile do not enable upload', async () => {
  const app = harness(async () => ({ ok: false }), {
    vf_serviceflow_auth: JSON.stringify({ role: 'CUSTOMER', name: 'Saved user' }),
  });
  assert.equal(app.render().role, 'GUEST');
  assert.equal(await app.render().loginAs('CUSTOMER'), false);
  assert.equal(app.render().role, 'GUEST');
});

test('logout cancels a pending login so upload stays disabled', async () => {
  let resolve;
  const app = harness(() => new Promise((done) => { resolve = done; }));
  const pending = app.render().loginAs('CUSTOMER');
  app.render().logout();
  resolve({ ok: true, json: async () => ({ data: { token: 'token' } }) });
  assert.equal(await pending, false);
  assert.equal(app.render().role, 'GUEST');
  assert.equal(app.storage.has('vf_customer_token'), false);
});
