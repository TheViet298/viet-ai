const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const {loader} = require('./render-loader.cjs');
exports.ticket = {id: 'QA-LIVE-DETAIL', mock_customer_id: 'CUSTOMER-1', customer_name: 'Nguyễn Văn QA',
  vehicle_model: 'VF7', priority: 'CRITICAL', intent: 'Service/Incident', status: 'Staff Reviewing',
  created_at: '2026-10-17T01:00:00Z', safety_status: 'unconfirmed'};
exports.detail = ticket => ({case: {...ticket}, case_brief: {summary: 'Customer authored summary',
  captured_fields: {vehicle_model: 'VF7', error_code: 'CC01'}, suggested_action: 'Technician proposal',
  confidence_score: 0.91}, conversation_history: [{sender:'CUSTOMER',content:'Customer authored message',created_at:ticket.created_at}]});
exports.harness = async function({ticket = exports.ticket, language = 'en', getDetail, submitAction, onStatusUpdate, onActionComplete} = {}) {
  const translate = (await loader())('features/shared/context/LocaleContext.tsx').translate;
  const states = [], refs = [], effects = [], dependencies = [], cleanups = [];
  let cursor = 0, refCursor = 0, effectCursor = 0, tree;
  const load = await loader({
    react: {...React, useState(initial) {const i=cursor++; if(!(i in states)) states[i]=typeof initial==='function'?initial():initial;
      return [states[i], value=>{states[i]=typeof value==='function'?value(states[i]):value}];},
      useRef: initial=>{const i=refCursor++;return refs[i] ||= {current:initial}},
      useEffect(fn,deps) {const i=effectCursor++; if(!dependencies[i] || deps.some((v,j)=>v!==dependencies[i][j])) {
        dependencies[i]=deps; effects.push(()=>{cleanups[i]?.();cleanups[i]=fn()});}},
    },
    '@/features/shared': {useAuth:()=>({user:{name:'QA Staff'}})},
    '@/features/shared/context/LocaleContext': {useLocale:()=>({language,t:text=>translate(text,language)})},
    './StaffConsoleShell': {ROUTING_DEPARTMENTS:[
      {id:'service_center',name:'Service Center',badge:'Xưởng',lead:'QA',description:'Workshop'},
      {id:'emergency_demo',name:'Emergency Response',badge:'Khẩn cấp',lead:'QA',description:'Emergency assistance'},
    ]},
    '../api/consoleApi': {getTicketDetail: getDetail || (async()=>({success:true,data:exports.detail(ticket)})),
      submitStaffAction: submitAction || (async()=>({success:true,data:{success:true,case_id:ticket.id}}))},
  });
  const Panel = load('features/console/components/TicketDetailPanel.tsx').TicketDetailPanel;
  function nodes(n) {if(!n || typeof n!=='object')return []; if(Array.isArray(n))return n.flatMap(nodes); return [n,...nodes(n.props?.children)];}
  function text(n) {if(Array.isArray(n))return n.map(text).join(''); if(!n || typeof n==='boolean')return ''; return typeof n==='object'?text(n.props?.children):String(n);}
  return {
    render(nextTicket=ticket) {ticket=nextTicket;cursor=refCursor=effectCursor=0;tree=Panel({ticket,onStatusUpdate,onActionComplete});return renderToStaticMarkup(tree)},
    effects(){effects.splice(0).forEach(fn=>fn())},
    click(label){const button=nodes(tree).find(n=>n.type==='button'&&text(n.props.children).includes(label));if(!button)throw Error('Button not found: '+label);return button.props.onClick()},
    changeSummary(value){const input=nodes(tree).find(n=>n.type==='textarea');if(!input)throw Error('Textarea not found');input.props.onChange({target:{value}})},
    unmount(){cleanups.forEach(fn=>fn?.())},
  };
};
exports.flush = ()=>new Promise(setImmediate);
