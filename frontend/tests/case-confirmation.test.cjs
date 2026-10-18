const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

function renderPage(confirmCustomerCase) {
  const states = [];
  const currentCase = {
    id: 'CASE-TEST-1', vehicleModel: 'VF6', vehicleCode: 'DEMO',
    status: 'Resolved', priority: 'MEDIUM', createdAt: 'Hôm nay',
    issueSummary: 'Yêu cầu kiểm tra', suggestedAction: 'Chờ xác nhận',
    customerUpdate: { staffName: 'Cố vấn demo', resolutionSummary: 'Đã xử lý', nextStepGuidance: 'Vui lòng xác nhận' },
  };
  const source = fs.readFileSync(path.join(__dirname, '../src/app/track-case/page.tsx'), 'utf8');
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 },
  }).outputText;
  const exports = {};
  const jsx = (type, props) => ({ type, props });
  vm.runInNewContext(compiled, {
    exports, Error,
    require: id => {
      if (id === 'react') return {
        useState: initial => {
          const index = states.length;
          states.push(index === 2 ? currentCase : typeof initial === 'function' ? initial() : initial);
          return [states[index], value => { states[index] = typeof value === 'function' ? value(states[index]) : value; }];
        },
        useEffect: () => {},
        useMemo: callback => callback(),
      };
      if (id === 'react/jsx-runtime') return { jsx, jsxs: jsx, Fragment: 'fragment' };
      if (id === 'next/link') return { default: 'a' };
      if (id === 'lucide-react') return new Proxy({}, { get: (_target, key) => key });
      if (id === '@/features/shared') return { useAuth: () => ({ role: 'CUSTOMER' }) };
      if (id === '@/features/chat/api/chatApi') return { confirmCustomerCase, getCaseServicePoints: () => Promise.resolve({ success: true, data: null }), submitCustomerLocation: () => Promise.resolve() };
      if (id === '@/features/chat/components/VietmapMiniMap') return { VietmapMiniMap: () => null };
      if (id.includes('LocaleContext')) return { useLocale: () => ({ t: (s) => s, language: 'vi' }) };
      if (id.includes('customerWarningText')) return { formatWarningDisplay: (s) => s };
      throw new Error(`Unexpected import: ${id}`);
    },
  });
  return { states, tree: exports.default() };
}

function textOf(node) {
  if (typeof node === 'string') return node;
  if (Array.isArray(node)) return node.map(textOf).join('');
  return node?.props ? textOf(node.props.children) : '';
}

function findConfirmButton(node) {
  if (!node) return;
  if (Array.isArray(node)) return node.map(findConfirmButton).find(Boolean);
  if (node.type === 'button' && textOf(node).includes('Đã được hỗ trợ')) return node;
  return findConfirmButton(node.props?.children);
}

for (const [name, response] of [
  ['network failure', async () => { throw new Error('offline'); }],
  ['server rejection', async () => ({ success: false, error: 'Chưa chấp nhận' })],
]) {
  test(`${name} keeps the case resolved and reports failure`, async () => {
    const { states, tree } = renderPage(response);
    const button = findConfirmButton(tree);
    assert.ok(button, 'customer confirmation button is available');
    await button.props.onClick();
    assert.equal(states[2].status, 'Resolved');
    assert.ok(states.includes('IDLE'));
    assert.ok(states.some(value => typeof value === 'string' && (value.startsWith('Chưa xác nhận hoàn tất hồ sơ:') || value.startsWith('Lưu ý:'))));
    assert.ok(!states.includes('RESOLVED_CONFIRMED'));
  });
}

test('accepted confirmation closes the case', async () => {
  let submitted;
  const { states, tree } = renderPage(async (caseId, payload) => {
    submitted = { caseId, confirmation: payload.confirmation };
    return { success: true };
  });
  await findConfirmButton(tree).props.onClick();
  assert.deepEqual(submitted, { caseId: 'CASE-TEST-1', confirmation: 'RESOLVED_CONFIRMED' });
  assert.equal(states[2].status, 'Closed');
  assert.ok(states.includes('RESOLVED_CONFIRMED'));
});
