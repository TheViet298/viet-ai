const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

test('legacy structured warning evidence renders without private metadata', () => {
  const source = fs.readFileSync(require.resolve('../src/features/shared/utils/customerWarningText.ts'), 'utf8');
  const module = { exports: {} };
  vm.runInNewContext(ts.transpileModule(source, {compilerOptions: {module: ts.ModuleKind.CommonJS}}).outputText,
    {module, exports: module.exports, require});
  const present = module.exports.toCustomerWarningText;
  for (const value of [[{owner_user_id: 'PRIVATE', image_routing: 'PRIVATE'}], {unexpected: 'PRIVATE'},
      ['Đèn đỏ', {owner_user_id: 'PRIVATE'}]]) {
    const text = present({visual_signals: value});
    const html = renderToStaticMarkup(React.createElement('span', null, text));
    assert.match(html, /Đã nhận bằng chứng ảnh/);
    assert.doesNotMatch(html, /PRIVATE|owner_user_id|image_routing|\[object/);
  }
  assert.equal(present({warning_symbol: 'Rùa vàng'}), 'Rùa vàng');
  assert.equal(present({warning_light: ['Đèn đỏ', 'Đèn pin']}), 'Đèn đỏ; Đèn pin');
  for (const value of [null, [], '', undefined]) assert.equal(present({visual_signals: value}), undefined);
});
