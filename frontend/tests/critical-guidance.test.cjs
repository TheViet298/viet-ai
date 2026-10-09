const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

test('critical chat response still displays its safety guidance', () => {
  const source = fs.readFileSync(require.resolve('../src/features/chat/components/ChatMessageItem.tsx'), 'utf8');
  const code = ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
    target: ts.ScriptTarget.ES2020,
  }}).outputText;
  const module = { exports: {} };
  const jsx = (type, props) => ({ type, props });
  vm.runInNewContext(code, { module, exports: module.exports, Date,
    require: (name) => name === 'react' ? { useMemo: (fn) => fn() }
      : name === 'react/jsx-runtime' ? { jsx, jsxs: jsx }
      : { default: name },
  });
  const guidance = 'Nếu xe có dấu hiệu nguy hiểm, hãy dừng tại nơi an toàn và liên hệ cứu hộ.';
  const tree = module.exports.ChatMessageItem({ message: {
    sender: 'AGENT', content: 'Đã nhận diện cảnh báo phanh', priority: 'CRITICAL',
    safe_guidance: guidance,
  }, isLastMessage: true, onSelectReply: () => {} });
  const rendered = JSON.stringify(tree);
  assert.ok(rendered.includes('Chỉ dẫn:'));
  assert.ok(rendered.includes(guidance));
});

test('rescue hotline renders a callable phone link while unsafe URLs remain blocked', async () => {
  const { defaultUrlTransform } = await import('react-markdown');
  const source = fs.readFileSync(require.resolve('../src/features/chat/components/ChatMessageItem.tsx'), 'utf8');
  const code = ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
    target: ts.ScriptTarget.ES2020,
  }}).outputText;
  const module = { exports: {} };
  const jsx = (type, props) => ({ type, props });
  vm.runInNewContext(code, { module, exports: module.exports, Date,
    require: (name) => name === 'react' ? { useMemo: (fn) => fn() }
      : name === 'react/jsx-runtime' ? { jsx, jsxs: jsx }
      : { default: name, defaultUrlTransform },
  });
  const tree = module.exports.ChatMessageItem({ message: {
    sender: 'AGENT', content: '**Hotline cứu hộ VinFast:** [1900-232389](tel:1900232389)',
  }, isLastMessage: true, onSelectReply: () => {} });
  const queue = [tree];
  let markdown;
  while (queue.length) {
    const item = queue.shift();
    if (!item || typeof item !== 'object') continue;
    if (item.type === 'react-markdown') { markdown = item; break; }
    queue.push(...Object.values(item));
  }
  assert.ok(markdown);
  const transform = markdown.props.urlTransform || defaultUrlTransform;
  assert.equal(transform('tel:1900232389'), 'tel:1900232389');
  assert.equal(transform('javascript:alert(1)'), '');
  assert.equal(transform('tel:javascript:alert(1)'), '');
  assert.equal(transform('https://vinfastauto.com/'), 'https://vinfastauto.com/');
});
