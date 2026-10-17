const test=require('node:test');const assert=require('node:assert/strict');const React=require('react');const {renderToStaticMarkup}=require('react-dom/server');const {loader}=require('./render-loader.cjs');
async function render(tab,state={}) {
 const load=await loader({
  react:{...React,useState:initial=>React.useState(initial==='queue'?tab:initial)},
  '../hooks/useTickets':{useTickets:()=>({tickets:[],filteredTickets:[],statusFilter:'ALL',priorityFilter:'ALL',searchQuery:'',loading:false,error:null,stats:{total:0,reviewing:0,critical:0,needsInfo:0,inProgress:0,resolved:0},isLiveApi:true,...state})},
  '@/features/shared':{useAuth:()=>({user:{name:'QA Staff'},logout(){}}),ProductMark:()=>null},
  '@/features/shared/context/LocaleContext':{useLocale:()=>({language:'en',t:text=>translations[text]||text})},
  './TicketDetailPanel':{cleanTicketHeadline:text=>text,TicketDetailPanel:()=>null},
  '@/features/shared/components/ThemeToggle':{ThemeToggle:()=>null},
  'next/link':{__esModule:true,default:({children,...props})=>React.createElement('a',props,children)},
 });
 const translations=load('features/console/consoleTranslations.ts').CONSOLE_ENGLISH;
 return renderToStaticMarkup(React.createElement(load('features/console/components/StaffConsoleShell.tsx').StaffConsoleShell));
}
for(const [tab,heading] of [['queue','The work queue is empty'],['overview','Shift overview'],['history','Case history and audit'],['routing','Routing directory'],['knowledge','Official source'],['preview','Customer live preview'],['profile','Staff profile']]) {
 test('English staff '+tab+' renders localized static copy',async()=>{const html=await render(tab);assert.ok(html.includes(heading),heading);assert.doesNotMatch(html,/Hồ sơ trong hàng đợi:|Cơ sở:|Dùng phím|Chưa chọn hồ sơ nào/)});
}
test('English staff queue renders translated API failure',async()=>{const html=await render('queue',{isLiveApi:false,error:'Không thể tải hàng đợi. Vui lòng thử lại.'});assert.match(html,/Unable to load the queue\. Please try again\./);assert.doesNotMatch(html,/Cơ sở:/)});

const caseItem={id:'CASE-QA',mock_customer_id:'QA',vehicle_model:'VF8',intent:'Service/Incident',priority:'HIGH',status:'Resolved',created_at:'2026-10-17',confidence_score:1,issue_summary:'Nội dung khách hàng giữ nguyên',suggested_action:'Ghi chú gốc của nhân viên'};
test('English history keeps original case content and server enum values',async()=>{const html=await render('history',{tickets:[caseItem],filteredTickets:[caseItem]});assert.match(html,/CASE-QA/);assert.ok(html.includes('Service/Incident'));assert.match(html,/Resolved/);assert.match(html,/Review case/);assert.doesNotMatch(html,/Đã xác nhận|Chưa xác nhận|Xem lại hồ sơ/)});
test('English queue preserves original customer issue text',async()=>{const item={...caseItem,status:'Staff Reviewing'};const html=await render('queue',{tickets:[item],filteredTickets:[item]});assert.match(html,/Nội dung khách hàng giữ nguyên/);assert.match(html,/High priority/);assert.doesNotMatch(html,/Chờ duyệt|Cần thêm tin|Đang xử lý|chờ [0-9]+/)});

