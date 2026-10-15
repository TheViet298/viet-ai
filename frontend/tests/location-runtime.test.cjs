const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const vm = require('node:vm');

// Execute the real TSX handlers/effects with a small deterministic hook renderer.
function harness() {
  const slots = [], effects = [], calls = [];
  let cursor = 0, tree, dirty = true, caseId = null, fail = false, success, error, starts = 0, stops = 0;
  const jsx = (type, props) => ({ type, props });
  const react = {
    useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = typeof initial === 'function' ? initial() : initial; return [slots[i], value => { slots[i] = typeof value === 'function' ? value(slots[i]) : value; dirty = true; }]; },
    useCallback(cb, deps) { const i = cursor++; const old=slots[i]; if(!old || deps.some((v,j)=>!Object.is(v,old.deps[j]))) slots[i]={deps,cb}; return slots[i].cb; },
    useRef(initial) { const i = cursor++; return slots[i] ??= { current: initial }; },
    useEffect(cb, deps) { const i = cursor++; const old = slots[i]; if (!old || !deps || deps.some((v,j) => !Object.is(v,old.deps[j]))) { slots[i] = { deps, cleanup: old?.cleanup }; effects.push(() => { slots[i].cleanup?.(); slots[i].cleanup = cb(); }); } },
  };
  const components = {};
  const chat = { messages: [], input: '', setInput() {}, sendMessage() {}, resetChat() { caseId = null; }, loading: false, requestLocation: true, nearbyAction: null };
  const geo = { getCurrentPosition(s,e) { starts++; success=s; error=e; return starts; }, clearWatch() { stops++; } };
  function load(relative) {
    const file = path.resolve(__dirname, relative);
    const code = ts.transpileModule(fs.readFileSync(file,'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX } }).outputText;
    const exports = {};
    vm.runInNewContext(code, { exports, Date, Math, Number, crypto: { randomUUID: () => "test-action" }, window: { matchMedia: () => ({ matches: false }) }, navigator: { geolocation: geo }, sessionStorage: { getItem() { return null; }, removeItem() {} }, require(id) {
      if (id === 'react') return react;
      if (id === 'react/jsx-runtime') return { jsx, jsxs: jsx };
      if (id === '../hooks/useChat') return { useChat: () => ({ ...chat, currentCaseId: caseId }) };
      if (id === '@/features/shared') return { useAuth: () => ({ role: 'CUSTOMER' }), ProductMark: 'ProductMark' };
      if (id === '../api/chatApi') return { submitCustomerLocation(payload) { calls.push(payload); return fail ? Promise.reject(new Error('offline')) : Promise.resolve({}); } };
      if (id === '../constants/servicePoints') return { getSeedServicePoints: () => [] };
      if (id === '../utils/locationTracking') return load('../src/features/chat/utils/locationTracking.ts');
      if (id === './distance') return load('../src/features/chat/utils/distance.ts');
      return new Proxy({}, { get(_, name) { return components[name] ??= name; } });
    } });
    return exports;
  }
  const { CustomerChatContainer } = load('../src/features/chat/components/CustomerChatContainer.tsx');
  function render() { cursor=0; dirty=false; tree=CustomerChatContainer(); while(effects.length) effects.shift()(); }
  function nodes(node) { if (!node || typeof node !== 'object') return []; if (Array.isArray(node)) return node.flatMap(n=>nodes(n)); return [node,...nodes(node.props?.children)]; }
  function card() { return nodes(tree).find(n=>n.type==='LocationConsentCard')?.props; }
  return { calls, card, action(value = { type: 'FIND_NEARBY', request_id: String(Date.now()), turn_id: 'turn', category: 'CHARGING_STATION', vehicle_type: 'CAR', requires_location: true, reason: 'Tìm trạm sạc', limit: 5 }) { chat.nearbyAction=value; dirty=true; },
    loading(value) { chat.loading=value; dirty=true; },
    results() { return nodes(tree).find(n=>n.type==='NearbyResults').props; }, nodes: () => nodes(tree), geo: () => ({starts,stops}),
    async flush() { for(let i=0;i<8;i++) { if(dirty) render(); await Promise.resolve(); } },
    case(value) { caseId=value; dirty=true; }, fail(value) { fail=value; },
    position(lat=21.0315,lng=105.8145,accuracy=850) { success({coords:{latitude:lat,longitude:lng,accuracy}}); },
    error(code) { error({code}); },
    unmount() { for(const slot of slots) slot?.cleanup?.(); },
  };
}

test('login and legacy request_location do not open a prompt; contextual action requires explicit GPS consent', async () => {
  const h=harness(); await h.flush(); assert.equal(h.card(),undefined); assert.equal(h.geo().starts,0);
  h.action(); await h.flush(); assert.ok(h.card()); assert.equal(h.geo().starts,0);
  h.card().onConsentGps(); assert.equal(h.geo().starts,1); h.position(); await h.flush();
  assert.equal(h.card(),undefined); assert.equal(h.results().locationState.status,'CONSENTED');
  h.case('CASE-NEW'); await h.flush(); assert.equal(h.calls.length,0, 'search consent must not automatically share with a case');
  h.nodes().find(n=>n.type==='button' && n.props.children==='Chia sẻ vị trí với hồ sơ').props.onClick(); await h.flush();
  assert.equal(h.calls.at(-1).status,'CONSENTED'); assert.equal(h.calls.at(-1).precision,'APPROXIMATE');
  h.results().onStopSharing(); await h.flush(); assert.equal(h.calls.at(-1).status,'NOT_SHARED');
  assert.equal(h.calls.at(-1).latitude,null);
});

test('skipping pending GPS invalidates a late callback', async () => {
  const h=harness(); await h.flush(); h.action(); await h.flush();
  const card=h.card(); card.onConsentGps(); card.onSkip(); await h.flush();
  h.position(); await h.flush(); assert.equal(h.results().locationState.status,'NOT_SHARED'); assert.equal(h.calls.length,0);
});

test('denied and timed out GPS permit manual area without coordinates', async () => {
  for (const code of [1,3]) {
    const h=harness(); await h.flush(); h.action(); await h.flush(); h.card().onConsentGps(); h.error(code); await h.flush();
    assert.ok(h.card().locationState.errorCode); h.card().onManualLocation('Đà Nẵng'); await h.flush();
    assert.equal(h.results().locationState.status,'MANUAL'); assert.equal(h.results().locationState.coords,undefined);
    h.position(); await h.flush(); assert.equal(h.results().locationState.status,'MANUAL');
  }
});

test('a new chat turn cancels pending geolocation and unmount rejects callbacks', async () => {
  const h=harness(); await h.flush(); h.action(); await h.flush(); h.card().onConsentGps();
  h.loading(true); await h.flush(); h.position(); await h.flush(); assert.equal(h.results().locationState.status,'PENDING');
  h.unmount(); h.position(); await h.flush(); assert.equal(h.calls.length,0);
});

test('failed explicit case sharing and clearing can be retried against the original case', async () => {
  const h=harness(); await h.flush(); h.action(); await h.flush(); h.card().onConsentGps(); h.position(); h.case('CASE-OLD'); await h.flush();
  h.fail(true); h.nodes().find(n=>n.type==='button' && n.props.children==='Chia sẻ vị trí với hồ sơ').props.onClick(); await h.flush();
  assert.ok(h.nodes().some(n=>n.props?.role==='alert'));
  h.fail(false); h.nodes().find(n=>n.type==='button' && n.props.children==='Thử lại đồng bộ').props.onClick(); await h.flush();
  assert.equal(h.calls.at(-1).case_id,'CASE-OLD');
  h.fail(true); h.nodes().find(n=>n.type==='button' && n.props.title==='Làm mới cuộc trò chuyện').props.onClick(); await h.flush();
  h.fail(false); h.nodes().find(n=>n.type==='button' && n.props.children==='Thử lại đồng bộ').props.onClick(); await h.flush();
  assert.equal(h.calls.at(-1).case_id,'CASE-OLD'); assert.equal(h.calls.at(-1).status,'NOT_SHARED');
});
