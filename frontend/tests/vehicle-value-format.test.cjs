const test = require('node:test');
const assert = require('node:assert/strict');
const {loader} = require('./render-loader.cjs');
test('structured vehicle values format Vietnamese numeric punctuation for English only', async () => {
  const {formatVehicleValue} = (await loader())('features/shared/context/LocaleContext.tsx');
  for (const [input, expected] of [['740.000.000 VNĐ', '740,000,000 VND'], ['500,5 km', '500.5 km'], ['500,5 km (NEDC)', '500.5 km (NEDC)'], ['87,7 kWh', '87.7 kWh'], ['20.000 km', '20,000 km']]) {
    assert.equal(formatVehicleValue(input, 'en'), expected);
    assert.equal(formatVehicleValue(input, 'vi'), input);
  }
});
test('vehicle formatting preserves English numbers, URLs, codes, dates and prose', async () => {
  const {formatVehicleValue} = (await loader())('features/shared/context/LocaleContext.tsx');
  for (const value of ['740,000,000 VND', '500.5 km', 'VND 740,000,000', 'https://example.com/500,5', 'CC01', '30/09/2026', '2026-09-30', 'VF 8', 'From 740.000.000 VNĐ', 'Error 500,5 km']) assert.equal(formatVehicleValue(value, 'en'), value);
});
