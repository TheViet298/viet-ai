const test=require('node:test');const assert=require('node:assert/strict');
const {harness,ticket,detail,flush}=require('./ticket-detail-harness.cjs');

test('structured visual evidence is described without rendering raw objects as warning text',async()=>{
 const data=detail(ticket);
 data.case_brief.captured_fields={vehicle_model:'VF7',visual_signals:[{image_routing:'PRIVATE_METADATA'}]};
 const h=await harness({getDetail:async()=>({success:true,data})});
 h.render();h.effects();await flush();
 const html=h.render();
 assert.doesNotMatch(html,/\[object Object\]|PRIVATE_METADATA/);
 assert.match(html,/Image evidence received/);
});
test('pending detail never displays a saved sample matching a real case ID',async()=>{
 const h=await harness({ticket:{...ticket,id:'CASE-20260924-001'},getDetail:()=>new Promise(()=>{})});
 const html=h.render();assert.match(html,/Loading case details/);assert.doesNotMatch(html,/Metropolis|Nguyễn Văn Tuấn|250kW/);
});
test('failed detail clears prior case data and allows retry',async()=>{
 let failed=false;const h=await harness({getDetail:async id=>{if(failed)throw Error('offline');return {success:true,data:detail({...ticket,id})}}});
 h.render();h.effects();await flush();assert.match(h.render(),/Customer authored summary/);
 failed=true;const next={...ticket,id:'QA-NEXT'};h.render(next);h.effects();await flush();
 const html=h.render();assert.match(html,/role="alert"/);assert.match(html,/Could not load case details/);assert.doesNotMatch(html,/Customer authored summary/);
 failed=false;await h.click('Try again');h.render();h.effects();await flush();assert.match(h.render(),/Customer authored summary/);
});
for(const [name,submitAction] of [['network failure',async()=>{throw Error('offline')}],['rejected envelope',async()=>({success:false})],['rejected receipt',async()=>({success:true,data:{success:false,case_id:ticket.id}})]])
 test(name+' preserves status and does not announce action success',async()=>{
  const statuses=[],messages=[];const h=await harness({submitAction,onStatusUpdate:(...args)=>statuses.push(args),onActionComplete:msg=>messages.push(msg)});
  h.render();h.effects();await flush();h.render();await h.click('Approve & dispatch');
  const html=h.render();assert.equal(statuses.length,0);assert.equal(messages.length,0);assert.match(html,/Could not save this action/);assert.match(html,/Approve &amp; dispatch/);
 });
test('brief editing reports success only after a server receipt',async()=>{
 const requests=[],messages=[];let fail=true;const h=await harness({submitAction:async(id,payload)=>{requests.push(payload);if(fail)throw Error('offline');return {success:true,data:{success:true,case_id:id}}},onActionComplete:msg=>messages.push(msg)});
 h.render();h.effects();await flush();h.render();h.click('Edit brief');h.render();h.changeSummary('Edited customer report');h.render();await h.click('Save');
 assert.equal(messages.length,0);assert.match(h.render(),/Could not save this action/);assert.equal(requests[0].action,'EDIT_BRIEF');assert.equal(requests[0].edited_brief.summary,'Edited customer report');
 fail=false;await h.click('Save');assert.equal(messages.length,1);
});
test('late action result cannot overwrite the next selected case',async()=>{
 let resolveAction;const statuses=[],messages=[];const h=await harness({
  getDetail:async id=>({success:true,data:{...detail({...ticket,id}),case_brief:{...detail(ticket).case_brief,summary:'Summary for '+id}}}),
  submitAction:()=>new Promise(resolve=>resolveAction=resolve),onStatusUpdate:(...args)=>statuses.push(args),onActionComplete:msg=>messages.push(msg)});
 h.render();h.effects();await flush();h.render();const pending=h.click('Approve & dispatch');
 h.render({...ticket,id:'QA-NEXT'});h.effects();await flush();assert.match(h.render(),/Summary for QA-NEXT/);
 resolveAction({success:true,data:{success:true,case_id:ticket.id}});await pending;
 assert.match(h.render(),/Summary for QA-NEXT/);assert.equal(statuses.length,0);assert.equal(messages.length,0);
});
test('saved action with failed refresh reports the receipt separately from refresh failure',async()=>{
 let requests=0;const statuses=[],messages=[];const h=await harness({
  getDetail:async()=>{if(requests++)throw Error('offline');return {success:true,data:detail(ticket)}},
  onStatusUpdate:(...args)=>statuses.push(args),onActionComplete:msg=>messages.push(msg)});
 h.render();h.effects();await flush();h.render();await h.click('Approve & dispatch');const html=h.render();
 assert.equal(statuses.length,1);assert.equal(messages.length,1);assert.match(html,/action was saved/);assert.doesNotMatch(html,/Could not save this action/);
});
test('dispatch rationale does not fabricate highway or charging symptoms from priority',async()=>{
 const h=await harness();h.render();h.effects();await flush();h.render();h.click('Workshop dispatch');
 const html=h.render();assert.doesNotMatch(html,/emergency on the highway|handshake error CC01/);assert.match(html,/case priority and request category/);
});
