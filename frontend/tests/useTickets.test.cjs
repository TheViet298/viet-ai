const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

function harness(getTicketQueue) {
  const states = [], refs = [], callbacks = [], pendingEffects = [], cleanups = [], dependencies = [];
  let cursor = 0, refCursor = 0, effectCursor = 0, callbackCursor = 0;
  const module = { exports: {} };
  const code = ts.transpileModule(fs.readFileSync(require.resolve('../src/features/console/hooks/useTickets.ts'), 'utf8'), {
    compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020},
  }).outputText;
  vm.runInNewContext(code, {module, exports:module.exports, require(id) {
    if(id === '../api/consoleApi') return {getTicketQueue};
    if(id === 'react') return {
      useState(initial) { const i=cursor++; if(!(i in states)) states[i]=initial; return [states[i], value => {states[i]=typeof value==='function'?value(states[i]):value}]; },
      useRef(initial) { const i=refCursor++; return refs[i] ||= {current:initial}; },
      useMemo: fn=>fn(),
      useCallback(fn,deps) { const i=callbackCursor++; if(!callbacks[i] || deps.some((d,j)=>d!==callbacks[i].deps[j])) callbacks[i]={fn,deps}; return callbacks[i].fn; },
      useEffect(fn,deps) {const i=effectCursor++; if(!dependencies[i] || deps.some((d,j)=>d!==dependencies[i][j])) {dependencies[i]=deps; pendingEffects.push(()=>{cleanups[i]?.(); cleanups[i]=fn()});}},
    };
    throw new Error(id);
  }});
  return {
    render(){cursor=refCursor=effectCursor=callbackCursor=0; return module.exports.useTickets()},
    effects(){pendingEffects.splice(0).forEach(fn=>fn())},
    unmount(){cleanups.forEach(fn=>fn?.())},
  };
}
const deferred = () => {let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject}};
const flush = async()=>{await new Promise(setImmediate)};
const item = {id:'REAL-1',status:'Staff Reviewing',priority:'HIGH',vehicle_model:'VF8',intent:'Service/Incident',mock_customer_id:'QA',created_at:'2026-10-17',confidence_score:1};
const success = items=>({success:true,data:{items,total:items.length}});

test('pending queue has loading state and no sample cases', ()=>{
  const h=harness(()=>new Promise(()=>{}));
  const state=h.render();
  assert.equal(state.tickets.length,0);
  assert.equal(state.loading,true);
});
for(const [name,response] of [['network error',()=>Promise.reject(new Error('offline'))],['unsuccessful envelope',async()=>({success:false})],['missing items',async()=>({success:true,data:{}})]]) {
  test(name+' clears stale queue and exposes an error',async()=>{
    let fail=false;
    const h=harness(()=>fail?response():Promise.resolve(success([item])));
    h.render();h.effects();await flush();
    assert.equal(h.render().tickets[0].id,'REAL-1');
    fail=true;await h.render().refreshTickets();
    const state=h.render();
    assert.equal(state.tickets.length,0);
    assert.ok(state.error);
    assert.equal(state.isLiveApi,false);
    assert.equal(state.loading,false);
  });
}
test('successful empty result is distinct from an API error',async()=>{
  const h=harness(async()=>success([]));h.render();h.effects();await flush();
  const state=h.render();assert.equal(state.tickets.length,0);assert.equal(state.error,null);assert.equal(state.isLiveApi,true);assert.equal(state.loading,false);
});
test('newer filter response wins over a late refresh',async()=>{
  const requests=[];
  const h=harness(params=>{const d=deferred();requests.push({...d,params});return d.promise});
  h.render();h.effects(); requests[0].resolve(success([item]));await flush();
  const refresh=h.render().refreshTickets();
  h.render().setPriorityFilter('CRITICAL');h.render();h.effects();
  assert.equal(requests.at(-1).params.priority,'CRITICAL');
  requests.at(-1).resolve(success([{...item,id:'NEW',priority:'CRITICAL'}]));await flush();
  requests[1].resolve(success([item]));await refresh;
  assert.equal(h.render().tickets[0].id,'NEW');
});
test('unmounted queue ignores a late manual refresh',async()=>{
  const requests=[];const h=harness(()=>{const d=deferred();requests.push(d);return d.promise});
  h.render();h.effects();requests[0].resolve(success([]));await flush();
  const refresh=h.render().refreshTickets();h.unmount();requests[1].resolve(success([item]));await refresh;
  assert.equal(h.render().tickets.length,0);
});
