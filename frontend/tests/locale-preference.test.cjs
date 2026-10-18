const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

function harness({ history = [], stored = {}, send } = {}) {
  const states = [], effects = [], refs = [];
  let stateCursor = 0, refCursor = 0, nonce = 0;
  let language = 'en', version = 0;
  const setLanguage = value => { language = value; version++; };
  const module = {exports:{}};
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(require.resolve('../src/features/chat/hooks/useChat.ts'),'utf8'), {
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020},
  }).outputText, {
    module,exports:module.exports,Date,Math,URLSearchParams,
    crypto:{randomUUID:()=> `locale-test-${++nonce}`},setTimeout:fn=>fn(),
    window:{addEventListener(){},removeEventListener(){}},
    localStorage:{getItem:key=>stored[key],setItem:(key,value)=>stored[key]=value,removeItem:key=>delete stored[key]},
    require(id) {
      if (id==='react') return {
        useState(initial){const i=stateCursor++;if(!(i in states))states[i]=typeof initial==='function'?initial():initial;return [states[i],value=>states[i]=typeof value==='function'?value(states[i]):value];},
        useEffect:fn=>effects.push(fn),useRef(initial){const i=refCursor++;return refs[i] ||= {current:initial};},
      };
      if(id.endsWith('/LocaleContext')) return {useLocale:()=>({language,setLanguage,getSelectionVersion:()=>version,t:x=>x}),translate:x=>x};
      if(id==='../api/chatApi') return {sendChatMessage:send,getSessionHistory:async()=>({success:true,data:{messages:history}})};
      throw new Error(id);
    },
  });
  const render=()=>{stateCursor=0;refCursor=0;return module.exports.useChat();};
  return {hook:render(),render,effects,states,setLanguage,language:()=>language};
}

const vietnameseHistory=[{id:'old',sender:'AGENT',content:'Xin chào',language:'vi',timestamp:'2026-10-01T00:00:00Z'}];
test('opening Vietnamese history preserves the selected English UI',async()=>{
  const h=harness({history:vietnameseHistory});
  await h.hook.loadSession('sess_vf_old_vi');
  assert.equal(h.language(),'en');
  assert.equal(h.states[0][0].language,'vi');
});
test('restoring Vietnamese history on mount preserves saved English UI',async()=>{
  const h=harness({history:vietnameseHistory,stored:{'vf_chat_session:guest':'sess_vf_old_vi'}});
  await h.effects[0](); await new Promise(resolve=>setTimeout(resolve,0));
  assert.equal(h.language(),'en');
  assert.equal(h.states[0][0].language,'vi');
});
for(const selections of [['vi'],['vi','en']]) test(`late response cannot overwrite explicit selections ${selections}`,async()=>{
  let complete;
  const h=harness({send:()=>new Promise(resolve=>complete=resolve)});
  const pending=h.hook.sendMessage('Please answer in Vietnamese');
  for(const language of selections) h.setLanguage(language);
  complete({success:true,data:{language:'vi',message:'Xin chào'}});
  await pending;
  assert.equal(h.language(),selections.at(-1));
  assert.equal(h.states[0].at(-1).language,'vi');
});
test('an explicit language request can synchronize the UI when no newer selection exists',async()=>{
  const h=harness({send:async()=>({success:true,data:{language:'vi',message:'Xin chào'}})});
  await h.hook.sendMessage('Please answer in Vietnamese');
  assert.equal(h.language(),'vi');
});
for(const nextLanguage of ['vi','en']) test(`retry identity respects the selected language ${nextLanguage}`,async()=>{
  const requests=[];
  const h=harness({send:async payload=>{
    requests.push(payload);
    if(requests.length===1) throw new Error('network unavailable');
    return {success:true,data:{language:nextLanguage,message:'Reply'}};
  }});
  await h.hook.sendMessage('Tell me about VF7');
  h.setLanguage(nextLanguage);
  await h.render().sendMessage('Tell me about VF7');
  assert.equal(requests[0].language,'en');
  assert.equal(requests[1].language,nextLanguage);
  if(nextLanguage==='en') assert.equal(requests[0].requestId,requests[1].requestId);
  else assert.notEqual(requests[0].requestId,requests[1].requestId);
});
