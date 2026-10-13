const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
function load(file) {
  const exports = {};
  const code = ts.transpileModule(fs.readFileSync(path.join(__dirname, '../src/features/chat', file), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
  new Function('exports', 'require', code)(exports, require);
  return exports;
}
const { resolveManualArea, searchManualAreas } = load('constants/manualAreas.ts');
const { createRasterMapStyle } = load('utils/mapTileProvider.ts');
test('manual aliases support accents, casing, punctuation, and search selection', () => {
  assert.equal(resolveManualArea('  HÀ NỘI ').id, 'ha-noi');
  assert.equal(resolveManualArea('TP.HCM').id, 'ho-chi-minh');
  assert.equal(resolveManualArea('Sai Gon').id, 'ho-chi-minh');
  assert.equal(resolveManualArea('da nang').id, 'da-nang');
  assert.deepEqual(searchManualAreas('long').map(a => a.id), ['long-thanh']);
  assert.equal(searchManualAreas('').length, 4);
});
test('ambiguous, street-name and unknown text do not produce a reference coordinate', () => {
  for (const text of ['', 'DN', 'Đồng Nai', 'Hà Nội / TP.HCM', '159 Xa Lộ Hà Nội, TP.HCM', 'đường Đà Nẵng', 'Dầu Giây', 'Hà Nộiabc']) {
    assert.equal(resolveManualArea(text), undefined, text);
  }
  assert.equal(searchManualAreas('unknown').length, 0);
});
test('default and custom raster providers retain attribution', () => {
  const defaultStyle = createRasterMapStyle();
  assert.equal(defaultStyle.sources.basemap.attribution, '© OpenStreetMap contributors');
  const custom = createRasterMapStyle('https://tiles.example.test/{z}/{x}/{y}.png', 'Test provider');
  assert.equal(custom.sources.basemap.tiles[0], 'https://tiles.example.test/{z}/{x}/{y}.png');
  assert.equal(custom.sources.basemap.attribution, 'Test provider');
  assert.equal(custom.layers[0].source, 'basemap');
});
test('invalid/mixed-content custom configuration fails safely instead of dropping attribution', () => {
  for (const [url, credit] of [
    ['http://tiles.example.test/{z}/{x}/{y}.png', 'Example'],
    ['https://tiles.example.test/{z}/{x}/{y}.png', ''],
    ['https://tiles.example.test/static.png', 'Example'],
    ['', 'Example'],
    ['https://user:password@tiles.example.test/{z}/{x}/{y}.png', 'Example'],
  ]) assert.throws(() => createRasterMapStyle(url, credit));
});
test('frontend fallback matches canonical nearby catalog and provenance', () => {
  const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, '../../fixtures/nearby_service_points.demo.json'), 'utf8'));
  const { SEED_SERVICE_POINTS } = load('constants/servicePoints.ts');
  assert.deepEqual(SEED_SERVICE_POINTS, fixture.points.map(point => ({
    id: point.id, name: point.name, type: point.category, address: point.address,
    demo: fixture.metadata.demo, source: fixture.metadata.source,
    updatedAt: fixture.metadata.updated_at, verificationStatus: fixture.metadata.verification_status,
    hotline: point.hotline, coords: { lat: point.latitude, lng: point.longitude },
  })));
});
