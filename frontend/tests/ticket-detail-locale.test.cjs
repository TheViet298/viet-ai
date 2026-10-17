const test = require('node:test');
const assert = require('node:assert/strict');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const {loader} = require('./render-loader.cjs');
const {harness, ticket: defaultTicket, flush} = require('./ticket-detail-harness.cjs');

async function renderDetail(status = 'Staff Reviewing', language = 'en') {
  const h = await harness({ticket: {...defaultTicket, status}, language});
  h.render(); h.effects(); await flush(); return h.render();
}

test('English case detail translates visible labels and defaults while retaining customer name and identifiers', async () => {
  const html = await renderDetail();
  for (const text of ['Approve &amp; dispatch', 'Incident record', 'Conversation history', 'Workshop dispatch',
    'Extracted technical details', 'Vehicle model', 'Battery charge (SoC)', 'Warning / Error code',
    'Customer safety not confirmed!', 'Copy full case ID']) assert.ok(html.includes(text), text);
  assert.match(html, /Nguyễn Văn QA/);
  assert.match(html, /QA-LIVE-DETAIL/);
  assert.doesNotMatch(html, /Duyệt|Hồ sơ|Chưa|Đang|Ghi chú|Dữ kiện/);
});

for (const [status, expected] of [['Needs Information','Remind customer'], ['In Progress','Resolve'],
  ['Resolved','Close case'], ['Closed','Reopen case']]) test(`English detail actions for ${status}`, async () => {
  const html = await renderDetail(status);
  assert.ok(html.includes(expected), expected);
  assert.doesNotMatch(html, /Duyệt|Nhắc khách|Giải quyết|Đóng hồ sơ|Mở lại/);
});

test('Vietnamese case detail retains Vietnamese controls', async () => {
  const html = await renderDetail('Staff Reviewing', 'vi');
  assert.match(html, /Duyệt &amp; Điều phối/);
  assert.match(html, /Hồ sơ sự cố/);
});
