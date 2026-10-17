const test = require('node:test');
const assert = require('node:assert/strict');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { loader } = require('./render-loader.cjs');

test('message timestamps use saved time and identical safety guidance appears once', async () => {
  const load = await loader();
  const { ChatMessageItem } = load('features/chat/components/ChatMessageItem.tsx');
  const timestamp = '2020-01-01T01:23:00Z';
  const html = renderToStaticMarkup(React.createElement(ChatMessageItem, {
    message: {id:'old', sender:'AGENT', timestamp, content:'Move to a safe place.', safe_guidance:'Move to a safe place.', language:'en'},
    isLastMessage: false, onSelectReply() {},
  }));
  const time = new Date(timestamp).toLocaleTimeString('en-US', {hour:'2-digit',minute:'2-digit'});
  assert.ok(html.includes(time), `expected stored time ${time}`);
  assert.equal(html.split('Move to a safe place.').length - 1, 1);
  assert.match(html, /lang="en"/);
});

test('New and Reopened guidance never claims completion and Reviewing has no invented ETA', () => {
  const fs = require('node:fs');
  const ts = require('typescript');
  const vm = require('node:vm');
  const source = fs.readFileSync(require.resolve('../src/app/track-case/page.tsx'),'utf8');
  const body = source.match(/const getNextStepInfo = \(c: TrackedCase\) => \{([\s\S]*?)\n  \};/)[1];
  const get = vm.runInNewContext(ts.transpileModule('(c) => {' + body + '}', {}).outputText, {t: text => text});
  for (const status of ['New','Reopened']) assert.doesNotMatch(get({status}).highlight, /hoàn tất/i);
  assert.doesNotMatch(get({status:'Staff Reviewing'}).highlight, /3[–-]5/);
  assert.doesNotMatch(get({status:'Reopened',customerUpdate:{nextStepGuidance:'Hồ sơ đã hoàn tất.'}}).highlight,/hoàn tất/i);
  for(const status of ['Staff Reviewing','Needs Information','In Progress','New','Reopened','Unknown']) assert.doesNotMatch(get({status,priority:'CRITICAL'}).highlight,/hoàn tất/i);
  for(const status of ['Resolved','Closed']) assert.match(get({status}).highlight,/hoàn tất/i);
});

test('English locale covers loading, input labels, emergency, location and card actions', async () => {
  const load = await loader();
  const {LocaleProvider} = load('features/shared/context/LocaleContext.tsx');
  const components = [
    ['ChatFeed', {messages:[], loading:true, onSelectReply(){}}, /Checking the technical guide/, /Đang xử lý/],
    ['ChatInputBar', {input:'', onChangeInput(){}, onSend(){}}, /Message to VinFast Assistant/, /Quý khách cần/],
    ['EmergencyAlertBanner', {visible:true}, /I am safe/, /Đã an toàn/],
    ['LocationConsentCard', {locationState:{status:'PENDING'}}, /Use current location/, /Dùng vị trí/],
    ['VehicleInfoCard', {card:{name:'VF7',specs:[],price_label:'830 VND',verified_at:'2026-10-10',test_drive_url:'https://example.com'}}, /Register for a test drive/, /Đăng ký lái thử/],
  ];
  for (const [name, props, expected, absent] of components) {
    const Component = load('features/chat/components/' + name + '.tsx')[name];
    const html = renderToStaticMarkup(React.createElement(LocaleProvider, {initialLanguage:'en'}, React.createElement(Component, props)));
    assert.match(html, expected, name); assert.doesNotMatch(html, absent, name);
  }
});

test('curated topics prepare a support request without unsupported technical thresholds or procedures', () => {
  const fs=require('node:fs'), ts=require('typescript'), vm=require('node:vm');
  const source=fs.readFileSync(require.resolve('../src/app/track-case/page.tsx'),'utf8');
  const data=source.match(/const CURATED_TOPICS: CuratedTopic\[\] = (\[[\s\S]*?\n\]);/)[1];
  const topics=vm.runInNewContext(ts.transpileModule('('+data+')',{}).outputText);
  const visible=JSON.stringify(topics);
  assert.doesNotMatch(visible,/40-50|2\.0 bar|2\.3|2\.4|BMS|Chương 6|Mục 4\.2|Sờ vào|Hẹn kỹ thuật viên/);
  assert.equal(topics.length,4);
  for(const topic of topics) {
    assert.ok(topic.preparation.length > 0);
    assert.match(topic.citationUrl,/^https:\/\/(om\.)?vinfastauto\.com\//);
  }
});

test('failed resolution confirmation preserves the open case and does not claim receipt', async () => {
  const fs=require('node:fs'), ts=require('typescript'), vm=require('node:vm');
  const source=fs.readFileSync(require.resolve('../src/app/track-case/page.tsx'),'utf8');
  const body=source.match(/const handleConfirmResolved = async \(\) => \{([\s\S]*?)\n  \};/)[1];
  const initial={id:'real',status:'Resolved'};let current=initial, confirmation='IDLE', notice;
  const handler=vm.runInNewContext(ts.transpileModule('(async () => {'+body+'})',{}).outputText, {
    currentCase:initial, confirmCustomerCase:async()=>{throw Error('offline')},
    setIsSubmittingConfirm(){},setActionNotice:v=>notice=v,setConfirmStatus:v=>confirmation=v,setCurrentCase:v=>current=v,t:text=>text,
  });
  await handler();
  assert.equal(current.status,'Resolved');assert.equal(confirmation,'IDLE');assert.doesNotMatch(notice,/Đã ghi nhận|hoàn tất/i);
});

test('guest navigation, login and case tracking render English from the same locale', async () => {
  const load = await loader({
    'next/navigation': {usePathname:()=>'/chat',useRouter:()=>({push(){}})},
    '@/features/shared': {useAuth:()=>({role:'GUEST',user:null,login(){},logout(){}}),ProductMark:()=>null},
    '../context/AuthContext': {useAuth:()=>({role:'GUEST',user:null,logout(){}})},
  });
  const {LocaleProvider}=load('features/shared/context/LocaleContext.tsx');
  for(const [file,name,expected] of [
    ['features/shared/components/Navbar.tsx','Navbar',/Chat Assistant/],
    ['app/login/page.tsx','default',/Phone number \/ Username/],
    ['app/track-case/page.tsx','default',/Sign in to track your vehicle case/],
  ]) {
    const Component=load(file)[name];
    const html=renderToStaticMarkup(React.createElement(LocaleProvider,{initialLanguage:'en'},React.createElement(Component)));
    assert.match(html,expected,file);assert.doesNotMatch(html,/Đăng nhập/,file);
  }
});

test('mixed-language history retains each message labels and translates card labels only', async()=>{
  const load=await loader();const {ChatMessageItem}=load('features/chat/components/ChatMessageItem.tsx');
  const props={isLastMessage:false,onSelectReply(){}};
  const messages=[{id:'vi',sender:'AGENT',language:'vi',content:'Xin chào',timestamp:'2026-10-01T01:00:00Z'},
    {id:'en',sender:'AGENT',language:'en',content:'Hello',timestamp:'2026-10-01T02:00:00Z',vehicle_cards:[{name:'VF7',specs:[{label:'Quãng đường',value:'123 km (NEDC)'}],price_label:'830 VND',verified_at:'2026-10-10'}]}];
  const html=renderToStaticMarkup(React.createElement(React.Fragment,null,messages.map(message=>React.createElement(ChatMessageItem,{...props,message,key:message.id}))));
  assert.match(html,/lang="vi"/);assert.match(html,/lang="en"/);assert.match(html,/Trợ lý VinFast/);assert.match(html,/VinFast Assistant/);assert.match(html,/>Range</);assert.match(html,/123 km \(NEDC\)/);
});

test('locale hydration does not overwrite saved English during the initial effects', () => {
  const fs=require('node:fs'),ts=require('typescript'),vm=require('node:vm');
  const source=fs.readFileSync(require.resolve('../src/features/shared/context/LocaleContext.tsx'),'utf8');
  const effects=[];let stored='en';const module={exports:{}};
  vm.runInNewContext(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText,{
    module,exports:module.exports,document:{documentElement:{}},
    localStorage:{getItem:()=>stored,setItem:(_,value)=>{stored=value}},
    require:id=>id==='react'?{createContext:()=>({Provider:'Provider'}),useRef:initial=>({current:initial}),useState:initial=>[initial,()=>{}],useEffect:fn=>effects.push(fn)}:require(id),
  });
  module.exports.LocaleProvider({children:null});
  for(const effect of effects)effect();
  assert.equal(stored,'en');
});

