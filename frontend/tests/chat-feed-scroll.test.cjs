const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),ts=require('typescript');
const React=require('react');

test('chat auto-scroll moves only the message container, preserving page/header position',()=>{
 const scrolls=[];let ancestorScrolled=false;
 const container={scrollHeight:900,scrollTo:options=>scrolls.push(options)};
 let nullRefs=0;
 const hooks={...React,useState:x=>[x,()=>{}],useCallback:f=>f,useMemo:f=>f(),useEffect:f=>f(),
   useRef:initial=>({current:initial===null?(nullRefs++===0?container:{scrollIntoView:()=>{ancestorScrolled=true;}}):initial})};
 const module={exports:{}};
 const source=fs.readFileSync(require.resolve('../src/features/chat/components/ChatFeed.tsx'),'utf8');
 vm.runInNewContext(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText,{
  module,exports:module.exports,setTimeout:f=>{f();return 1;},clearTimeout(){},
  ResizeObserver:class{observe(){}disconnect(){}},
  require:id=>id==='react'?hooks:id.endsWith('/LocaleContext')?{useLocale:()=>({t:s=>s})}:id==='./ChatMessageItem'?{ChatMessageItem:()=>null}:require(id),
 });
 module.exports.ChatFeed({messages:[],loading:false,onSelectReply(){}});
 assert.equal(ancestorScrolled,false,'scrollIntoView must not scroll the document under the sticky navbar');
 assert.ok(scrolls.length>0);
 assert.equal(scrolls[0].top,900);
});
