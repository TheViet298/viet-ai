const test=require('node:test');const assert=require('node:assert/strict');const React=require('react');const {renderToStaticMarkup}=require('react-dom/server');const {loader}=require('./render-loader.cjs');
async function render(state) {
 const load=await loader({
  '../hooks/useTickets':{useTickets:()=>({tickets:[],filteredTickets:[],statusFilter:'ALL',priorityFilter:'ALL',searchQuery:'',stats:{total:0,reviewing:0,critical:0,needsInfo:0,inProgress:0,resolved:0},isLiveApi:false,...state})},
  '@/features/shared':{useAuth:()=>({user:{name:'QA Staff'},logout(){}}),ProductMark:()=>null},
  '@/features/shared/context/LocaleContext':{useLocale:()=>({language:'vi',t:text=>text})},
  '@/features/shared/components/ThemeToggle':{ThemeToggle:()=>null},
  'next/link':{__esModule:true,default:({children,...props})=>React.createElement('a',props,children)},
 });
 return renderToStaticMarkup(React.createElement(load('features/console/components/StaffConsoleShell.tsx').StaffConsoleShell));
}
test('staff queue renders loading before an empty result',async()=>{const html=await render({loading:true,error:null});assert.match(html,/Đang tải hàng đợi/);assert.doesNotMatch(html,/Hàng đợi xử lý hiện đang trống|Chế độ mẫu/)});
test('staff queue renders an API error separately from empty queue',async()=>{const html=await render({loading:false,error:'Không thể tải hàng đợi. Vui lòng thử lại.'});assert.match(html,/role="alert"/);assert.match(html,/Không thể tải hàng đợi/);assert.doesNotMatch(html,/Hàng đợi xử lý hiện đang trống|Chế độ mẫu/)});
