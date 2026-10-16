const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

test('vehicle card renders four labeled specs, price and a real test-drive link', () => {
  const source = fs.readFileSync(require.resolve('../src/features/chat/components/VehicleInfoCard.tsx'), 'utf8');
  const code = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(code, { module, exports: module.exports, require });
  const card = { model: 'VF8', variant: 'plus', name: 'VinFast VF 8 Plus',
    image_url: 'https://static-cms-prod.vinfastauto.com/vf8.webp',
    specs: ['Số chỗ ngồi', 'Quãng đường', 'Thời gian sạc', 'Công suất tối đa'].map(label => ({ label, value: 'Verified value' })),
    price_label: 'Từ 1.079.000.000 VNĐ', source_url: 'https://vinfastauto.com/vn_vi/dat-coc-xe-vf8',
    specs_source_url: 'https://vinfastauto.com/vn_vi/cau-hoi-thuong-gap',
    verified_at: '2026-10-14', test_drive_url: 'https://shop.vinfastauto.com/vn_vi/dang-ky-lai-thu.html?modelId=VF8' };
  const html = renderToStaticMarkup(React.createElement(module.exports.VehicleInfoCard, { card }));
  assert.equal((html.match(/<dt /g) || []).length, 4);
  assert.match(html, /Đăng ký lái thử/);
  assert.match(html, /modelId=VF8/);
  assert.doesNotMatch(html, /Thông số theo FAQ/);
  assert.match(html, /1\.079\.000\.000 VNĐ/);
  assert.match(html, /alt="VinFast VF 8 Plus"/);
});

test('comparison aligns two vehicles under shared labels and retains missing-data fallback', () => {
  const source = fs.readFileSync(require.resolve('../src/features/chat/components/VehicleComparison.tsx'), 'utf8');
  const module = { exports: {} };
  const code = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  vm.runInNewContext(code, { module, exports: module.exports, require });
  const cards = ['VF 6 Eco', 'VF 8 Eco'].map((name, index) => ({
    model: index ? 'VF8' : 'VF6', name, image_url: 'https://static-cms-prod.vinfastauto.com/car.webp',
    specs: [{ label: 'Số chỗ ngồi', value: '5 chỗ' }, { label: 'Quãng đường', value: index ? '635 km (NEDC)' : '485 km (NEDC)' }],
    battery_capacity: index ? '87,7 kWh' : '59,6 kWh', fast_charge_time: index ? '31 phút' : '25 phút',
    price_label: 'Từ 898.000.000 VNĐ', test_drive_url: 'https://shop.vinfastauto.com/vn_vi/dang-ky-lai-thu.html',
  }));
  const render = () => renderToStaticMarkup(React.createElement(module.exports.VehicleComparison, { cards }));
  const html = render();
  assert.equal((html.match(/<tbody>/g) || []).length, 5);
  assert.equal((html.match(/<img /g) || []).length, 2);
  assert.match(html, /59,6 kWh/);
  assert.match(html, /87,7 kWh/);
  assert.match(html, /Đăng ký lái thử VF 6 Eco/);
  assert.match(html, /Đăng ký lái thử VF 8 Eco/);
  assert.doesNotMatch(html, /FAQ/);
  cards[0].battery_capacity = null;
  assert.match(render(), /Chưa có dữ liệu/);
});
