const $ = id => document.getElementById(id);
let sessionId = null;
let busy = false;
let lastCaseId = null;
let knownCases = [];
const intentLabels = {product: 'Tư vấn sản phẩm', customer_care: 'Chăm sóc khách hàng', technical: 'Sự cố kỹ thuật'};
const statusLabels = {WAITING: 'Chờ nhân viên', IN_PROGRESS: 'Đang xử lý', RESOLVED: 'Đã hoàn tất'};

function node(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}
function replies(container, options) {
  const row = node('div', 'quick-replies');
  options.forEach(text => {
    const button = node('button', 'quick-reply', text);
    button.type = 'button';
    button.addEventListener('click', () => send(text));
    row.append(button);
  });
  container.append(row);
}
function addMessage(text, role = 'assistant', result = null) {
  const wrapper = node('div', `message ${role}`);
  if (role === 'assistant') wrapper.append(node('span', 'message-mark', '✦'));
  const bubble = node('div', 'bubble');
  if (role === 'assistant') {
    const label = node('div', 'bubble-label', 'SERVICEFLOW');
    if (result?.priority) label.append(node('span', `badge ${result.priority}`, result.priority));
    bubble.append(label);
  }
  const body = node('div', 'bubble-body', text);
  if (result?.status === 'HANDOFF') body.className += ' handoff' + (result.priority === 'URGENT' ? ' urgent' : '');
  bubble.append(body);
  for (const citation of result?.citations || []) {
    let url;
    try { url = new URL(citation.url); } catch { continue; }
    if (!['https:', 'http:'].includes(url.protocol)) continue;
    const link = node('a', 'citation', '↗ ' + citation.title);
    link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer';
    link.append(node('span', '', citation.provenance || 'Nguồn trong database demo'));
    bubble.append(link);
  }
  if (result?.quick_replies?.length) replies(bubble, result.quick_replies);
  wrapper.append(bubble); $('messages').append(wrapper); scrollChat();
}
function welcome() {
  $('messages').replaceChildren();
  const wrapper = node('div', 'message assistant');
  wrapper.append(node('span', 'message-mark', '✦'));
  const bubble = node('div', 'bubble');
  bubble.append(node('div', 'bubble-label', 'SERVICEFLOW'));
  bubble.append(node('div', 'welcome-title', 'Xin chào, tôi có thể giúp gì cho bạn?'));
  bubble.append(node('div', 'bubble-body', 'Tôi có thể tra cứu thông tin sản phẩm, hướng dẫn dịch vụ hoặc tiếp nhận sự cố của xe. Hãy bắt đầu với một câu hỏi nhé.'));
  const cards = node('div', 'welcome-cards');
  [['◇', 'Tìm chiếc xe phù hợp', 'Tư vấn theo nhu cầu của bạn', 'Tôi cần tư vấn xe cho gia đình'], ['⌁', 'Hỗ trợ chăm sóc xe', 'Tra cứu thông tin và hướng dẫn', 'Làm thế nào đặt lịch bảo dưỡng?'], ['⚙', 'Xe đang gặp sự cố', 'Bổ sung ngữ cảnh, bàn giao kỹ thuật', 'Xe không nhận sạc'], ['↗', 'Xem luồng khẩn cấp', 'Mô phỏng hồ sơ URGENT', 'Xe đang bốc khói']].forEach(([icon, title, description, prompt]) => {
    const card = node('button', 'welcome-card'); card.type = 'button';
    card.append(node('span', '', icon), node('strong', '', title), node('div', '', description));
    card.addEventListener('click', () => send(prompt)); cards.append(card);
  });
  bubble.append(cards); wrapper.append(bubble); $('messages').append(wrapper);
}
function scrollChat() { $('messages').scrollTop = $('messages').scrollHeight; }
function updateContext(result) {
  const panel = $('contextData'); panel.replaceChildren();
  const data = [['Nhóm yêu cầu', intentLabels[result.intent]], ['Mức độ', result.priority], ['Dòng xe', result.context?.model], ['Số chỗ', result.context?.seats], ['Nhu cầu', result.context?.usage], ['Trạng thái xe', result.context?.operational_status]];
  data.filter(([, value]) => value).forEach(([key, value]) => {
    const row = node('div', 'context-row'); row.append(node('span', '', key), node('strong', '', String(value))); panel.append(row);
  });
  $('trace').replaceChildren(...result.trace.map(text => node('li', '', text)));
}
async function request(path, payload) {
  const options = payload ? {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)} : {};
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(path, {...options, signal: controller.signal});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Không thể xử lý yêu cầu');
    return data;
  } finally { clearTimeout(timeout); }
}
async function send(text) {
  text = text.trim();
  if (!text || busy) return;
  busy = true; $('sendButton').disabled = true; $('messageInput').disabled = true;
  addMessage(text, 'user'); $('messageInput').value = ''; $('waiting').classList.remove('hidden');
  $('waitingText').textContent = 'Đợi tôi một chút, tôi đang kiểm tra ngữ cảnh và tra cứu thông tin…';
  scrollChat();
  try {
    const [result] = await Promise.all([request('/api/chat', {message: text, session_id: sessionId}), new Promise(resolve => setTimeout(resolve, 600))]);
    sessionId = result.session_id; addMessage(result.message, 'assistant', result); updateContext(result);
    if (result.case_id) { lastCaseId = result.case_id; await refreshCases(); }
  } catch (error) {
    addMessage('Chưa gửi được tin nhắn. ' + (error.name === 'AbortError' ? 'Máy chủ phản hồi quá lâu.' : error.message) + ' Vui lòng thử lại.');
    $('messageInput').value = text;
  } finally {
    busy = false; $('sendButton').disabled = false; $('messageInput').disabled = false; $('waiting').classList.add('hidden'); $('messageInput').focus(); scrollChat();
  }
}
function updatePreview() {
  const item = knownCases.find(item => item.id === lastCaseId);
  const preview = $('casePreview'); preview.replaceChildren();
  if (!item) { preview.append(node('p', '', 'Chưa có hồ sơ trong cuộc trò chuyện này.')); return; }
  preview.append(node('span', `badge ${item.priority}`, item.priority), node('strong', 'case-id', item.id), node('p', '', statusLabels[item.status]));
}
async function refreshCases() {
  try {
    const data = await request('/api/cases'); knownCases = data.cases;
    $('navCount').textContent = String(knownCases.filter(item => item.status !== 'RESOLVED').length);
    updatePreview(); renderQueue();
  } catch (error) { $('queueList').replaceChildren(node('p', 'error-message', 'Không tải được hàng đợi: ' + error.message)); }
}
function renderQueue() {
  const metrics = [['Đang chờ', knownCases.filter(item => item.status === 'WAITING').length], ['URGENT chưa hoàn tất', knownCases.filter(item => item.priority === 'URGENT' && item.status !== 'RESOLVED').length], ['Đã hoàn tất', knownCases.filter(item => item.status === 'RESOLVED').length]];
  $('queueMetrics').replaceChildren(...metrics.map(([title, count]) => { const el = node('div', 'metric', title); el.append(node('strong', '', String(count))); return el; }));
  const list = $('queueList'); list.replaceChildren();
  if (!knownCases.length) { list.append(node('p', 'queue-meta', 'Chưa có hồ sơ. Gửi một tin nhắn về sự cố trong chat để bắt đầu.')); return; }
  for (const item of knownCases) {
    const card = node('article', 'queue-case' + (item.priority === 'URGENT' ? ' urgent' : ''));
    const top = node('div', 'queue-case-top'); top.append(node('span', `badge ${item.priority}`, item.priority), node('strong', '', item.id), node('span', 'queue-state', statusLabels[item.status]));
    card.append(top, node('p', 'queue-summary', item.summary));
    let context = {}; try { context = JSON.parse(item.context); } catch {}
    card.append(node('div', 'queue-meta', [context.model, context.operational_status, 'Tạo lúc ' + new Date(item.created_at).toLocaleTimeString('vi-VN')].filter(Boolean).join(' · ')));
    if (item.status !== 'RESOLVED') {
      const button = node('button', 'button', item.status === 'WAITING' ? 'Nhân viên tiếp nhận' : 'Đánh dấu hoàn tất');
      button.type = 'button';
      button.addEventListener('click', async () => {
        button.disabled = true;
        try { await request('/api/cases/action', {case_id: item.id, action: item.status === 'WAITING' ? 'ACCEPT' : 'RESOLVE'}); await refreshCases(); }
        catch (error) { card.append(node('p', 'error-message', error.message)); button.disabled = false; }
      }); card.append(button);
    }
    list.append(card);
  }
}
function showView(queue) {
  $('chatView').classList.toggle('hidden', queue); $('queueView').classList.toggle('hidden', !queue);
  $('chatNav').classList.toggle('active', !queue); $('queueNav').classList.toggle('active', queue);
  $('pageTitle').textContent = queue ? 'Bàn kỹ thuật' : 'Trợ lý dịch vụ'; if (queue) refreshCases();
}
$('chatForm').addEventListener('submit', event => { event.preventDefault(); send($('messageInput').value); });
$('messageInput').addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send(event.target.value); } });
$('chatNav').addEventListener('click', () => showView(false)); $('queueNav').addEventListener('click', () => showView(true)); $('openQueue').addEventListener('click', () => showView(true)); $('refreshQueue').addEventListener('click', refreshCases);
$('newChat').addEventListener('click', () => {
  if (busy) return;
  sessionId = null; lastCaseId = null; showView(false); welcome();
  $('contextData').replaceChildren(node('p', '', 'Trợ lý sẽ ghi nhận ngữ cảnh khi bạn bắt đầu trò chuyện.'));
  $('trace').replaceChildren(...['Kiểm tra mức độ khẩn cấp', 'Phân loại bằng luật', 'Hỏi bổ sung hoặc tra cứu', 'Trả lời / bàn giao kỹ thuật'].map(text => node('li', '', text)));
  $('messageInput').value = ''; updatePreview(); $('messageInput').focus();
});
welcome(); refreshCases(); setInterval(refreshCases, 7000);
