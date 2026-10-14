const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

function loadApi(fetch, token, env = {}) {
  const source = fs.readFileSync(path.join(__dirname, '../src/features/chat/api/chatApi.ts'), 'utf8');
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText;
  const exports = {};
  vm.runInNewContext(compiled, {
    exports,
    fetch,
    process: { env },
    URLSearchParams,
    window: {},
    localStorage: { getItem: () => token },
  });
  return exports;
}

const gpsPayload = {
  case_id: 'CASE-TEST-1',
  status: 'CONSENTED',
  source: 'BROWSER_GPS',
  location_label: 'Vị trí GPS',
  latitude: 21.0315,
  longitude: 105.8145,
  precision: 'EXACT',
  share_with_staff: true,
};

test('nearby API uses same origin and preserves catalog provenance conservatively', async () => {
  let calledUrl;
  const point = { id: 'synthetic', name: 'Synthetic point', category: 'SHOWROOM', address: 'Synthetic area', latitude: 12, longitude: 98, hotline: '', source: 'Test catalog', updated_at: '2026-10-13', demo: false, verification_status: 'VERIFIED' };
  const api = loadApi(async url => {
    calledUrl = url;
    return { ok: true, json: async () => ({ data: { points: [point, { ...point, id: 'demo', demo: true }, { ...point, id: 'legacy', demo: undefined, verification_status: undefined }] } }) };
  }, null);
  const points = await api.getNearbyServicePoints({ lat: 12, lng: 98 }, 'ALL');
  assert.ok(calledUrl.startsWith('/api/v1/customer/service-points/nearby?'));
  assert.equal(points[0].source, 'Test catalog');
  assert.equal(points[0].updatedAt, '2026-10-13');
  assert.equal(points[0].demo, false);
  assert.equal(points[0].verificationStatus, 'VERIFIED');
  assert.equal(points[1].verificationStatus, 'UNVERIFIED');
  assert.equal(points[2].demo, true);
  assert.equal(points[2].verificationStatus, 'UNVERIFIED');
});

test('explicit API origin override removes a trailing slash', async () => {
  let calledUrl;
  const api = loadApi(async url => { calledUrl = url; return { ok: true, json: async () => ({ data: { points: [] } }) }; }, null, { NEXT_PUBLIC_API_URL: 'https://api.example.test/' });
  await api.getNearbyServicePoints({ lat: 12, lng: 98 }, 'ALL');
  assert.ok(calledUrl.startsWith('https://api.example.test/api/v1/'));
});

test('location API requires customer authentication before sending coordinates', async () => {
  let calls = 0;
  const api = loadApi(() => { calls += 1; }, null);
  await assert.rejects(api.submitCustomerLocation(gpsPayload), /đăng nhập/);
  assert.equal(calls, 0);
});

test('skipping location clears coordinates after an in-flight GPS update', async () => {
  let finishGps;
  const calls = [];
  const api = loadApi((url, options) => {
    calls.push({ url, options });
    if (calls.length === 1) {
      return new Promise(resolve => { finishGps = resolve; });
    }
    return Promise.resolve({ ok: true, json: async () => ({ success: true, data: {}, error: null }) });
  }, 'customer-token');

  const gpsRequest = api.submitCustomerLocation(gpsPayload);
  const skipRequest = api.submitCustomerLocation({
    ...gpsPayload,
    status: 'NOT_SHARED',
    location_label: '',
  });
  await new Promise(setImmediate);
  assert.equal(calls.length, 1, 'skip waits until the GPS update finishes');

  finishGps({ ok: true, json: async () => ({ success: true, data: {}, error: null }) });
  await Promise.all([gpsRequest, skipRequest]);
  assert.equal(calls.length, 2);
  assert.equal(calls[1].url, '/api/v1/customer/location');
  assert.equal(calls[1].options.headers.Authorization, 'Bearer customer-token');
  assert.deepEqual(JSON.parse(calls[1].options.body), {
    ...gpsPayload,
    status: 'NOT_SHARED',
    location_label: 'Không chia sẻ',
    latitude: null,
    longitude: null,
    share_with_staff: false,
  });
});

test('location API reports a failed server update', async () => {
  const api = loadApi(async () => ({ ok: false, status: 422 }), 'customer-token');
  await assert.rejects(api.submitCustomerLocation(gpsPayload), /422/);
});
