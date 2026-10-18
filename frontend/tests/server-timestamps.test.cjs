const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const { loader } = require('./render-loader.cjs');

process.env.TZ = 'Asia/Ho_Chi_Minh';

class FrozenDate extends Date {
  constructor(...args) { super(...(args.length ? args : ['2026-10-16T22:34:00Z'])); }
}

test('sidebar groups naive server UTC by the customer local day and preserves explicit offsets', async () => {
  assert.equal(new FrozenDate().getHours(), 5, 'test runs in Asia/Saigon');
  const load = await loader();
  const helpers = load('lib/utils.ts');
  const source = fs.readFileSync(require.resolve('../src/features/chat/components/ChatHistorySidebar.tsx'), 'utf8');
  const body = source.match(/const groupedSessions = useMemo\(\(\) => \{([\s\S]*?)\n  \}, \[sessions, searchQuery\]\);/)[1];
  const sessions = [
    ['naive', '2026-10-16T22:33:00.123456'],
    ['utc', '2026-10-16T22:33:00Z'],
    ['local', '2026-10-17T05:33:00+07:00'],
    ['yesterday', '2026-10-16T22:33:00+07:00'],
  ].map(([session_id, updated_at]) => ({session_id, updated_at, title: 'Current conversation'}));
  const group = vm.runInNewContext(ts.transpileModule('(() => {' + body + '})', {}).outputText,
    {...helpers, Date: FrozenDate, sessions, searchQuery: ''});
  const result = group();
  assert.equal(result.today.map(item => item.session_id).join(','), 'naive,utc,local');
  assert.equal(result.yesterday.map(item => item.session_id).join(','), 'yesterday');
});

test('restored message timestamp displays naive UTC at the same time as an explicit UTC timestamp', async () => {
  const React = require('react');
  const {renderToStaticMarkup} = require('react-dom/server');
  const load = await loader();
  const {ChatMessageItem} = load('features/chat/components/ChatMessageItem.tsx');
  const render = timestamp => renderToStaticMarkup(React.createElement(ChatMessageItem, {
    message:{id:'history',sender:'AGENT',language:'en',content:'Saved answer',timestamp},
    isLastMessage:false,onSelectReply(){},
  }));
  const explicit = render('2026-10-16T22:33:00Z');
  assert.match(explicit,/05:33 AM/);
  assert.equal(render('2026-10-16T22:33:00'),explicit);
});
