const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

function loadChatMessageItem() {
  const source = fs.readFileSync(require.resolve('../src/features/chat/components/ChatMessageItem.tsx'), 'utf8');
  const code = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      jsx: ts.JsxEmit.ReactJSX,
      target: ts.ScriptTarget.ES2020,
    },
  }).outputText;
  const module = { exports: {} };
  const jsx = (type, props) => ({ type, props });
  vm.runInNewContext(code, {
    module,
    exports: module.exports,
    Date,
    require: (name) => {
      if (name === 'react') {
        return {
          useMemo: (fn) => fn(),
          Children: { toArray: (c) => Array.isArray(c) ? c : [c] },
          isValidElement: () => true,
        };
      }
      if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx };
      return { default: name };
    },
  });
  return module.exports.ChatMessageItem;
}

test('ChatMessageItem enables markdown table elements and provides responsive custom components', () => {
  const ChatMessageItem = loadChatMessageItem();
  const tableContent = `
### So sánh thông số kỹ thuật VinFast VF 3 và VinFast VF 5 Plus

| Tiêu chí | VinFast VF 3 | VinFast VF 5 Plus |
| :--- | :--- | :--- |
| **Phân khúc** | Mini SUV điện đô thị | A-SUV điện đô thị |
| **Số chỗ ngồi** | 4 chỗ | 5 chỗ |
`;

  const tree = ChatMessageItem({
    message: {
      sender: 'AGENT',
      content: tableContent,
      citations: [
        {
          title: 'Cẩm nang kỹ thuật & Thông số VinFast VF 3',
          url: 'https://vinfastauto.com/vn_vi/mau-xe-vf-3',
        },
        {
          title: 'Cẩm nang kỹ thuật & Thông số VinFast VF 5 Plus',
          url: 'https://vinfastauto.com/vn_vi/mau-xe-vf-5-plus',
        },
      ],
    },
    isLastMessage: true,
    onSelectReply: () => {},
  });

  // Tìm react-markdown node
  const queue = [tree];
  let markdown;
  while (queue.length) {
    const item = queue.shift();
    if (!item || typeof item !== 'object') continue;
    if (item.type === 'react-markdown') {
      markdown = item;
      break;
    }
    queue.push(...Object.values(item));
  }

  assert.ok(markdown, 'ReactMarkdown component must be rendered');
  const allowed = markdown.props.allowedElements;
  assert.ok(allowed.includes('table'), 'allowedElements must include table');
  assert.ok(allowed.includes('thead'), 'allowedElements must include thead');
  assert.ok(allowed.includes('tbody'), 'allowedElements must include tbody');
  assert.ok(allowed.includes('tr'), 'allowedElements must include tr');
  assert.ok(allowed.includes('th'), 'allowedElements must include th');
  assert.ok(allowed.includes('td'), 'allowedElements must include td');

  // Kiểm tra custom component table bọc overflow-x-auto cho mobile
  const components = markdown.props.components;
  assert.equal(typeof components.table, 'function');
  const tableEl = components.table({ children: 'table_body' });
  const tableJson = JSON.stringify(tableEl);
  assert.ok(tableJson.includes('overflow-x-auto'), 'table wrapper must have overflow-x-auto');
  assert.ok(tableJson.includes('border'), 'table wrapper must have border');

  // Kiểm tra custom thead có nền xám
  assert.equal(typeof components.thead, 'function');
  const theadEl = components.thead({ children: 'th_content' });
  const theadJson = JSON.stringify(theadEl);
  assert.ok(theadJson.includes('bg-slate-200'), 'thead must have grey background bg-slate-200');

  // Kiểm tra rendered citations: phải hiện ĐỦ 2 citation cho cả VF3 và VF5
  const rendered = JSON.stringify(tree);
  assert.ok(rendered.includes('mau-xe-vf-3'), 'Must contain VF3 citation link');
  assert.ok(rendered.includes('mau-xe-vf-5-plus'), 'Must contain VF5 Plus citation link');
  assert.ok(rendered.includes('Cẩm nang kỹ thuật & Thông số VinFast VF 3'), 'Must contain VF3 title');
  assert.ok(rendered.includes('Cẩm nang kỹ thuật & Thông số VinFast VF 5 Plus'), 'Must contain VF5 Plus title');
});
