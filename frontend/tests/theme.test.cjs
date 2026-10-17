const test=require('node:test');
const assert=require('node:assert/strict');
const React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');
const {loader}=require('./render-loader.cjs');
test('theme toggle has an accessible action and toggles independently of language',async()=>{
  let selected;
  const load=await loader({'@/features/shared/context/ThemeContext':{useTheme:()=>({theme:'light',setTheme:v=>selected=v})},'@/features/shared/context/LocaleContext':{useLocale:()=>({t:v=>v})}});
  const {ThemeToggle}=load('features/shared/components/ThemeToggle.tsx');
  const tree=ThemeToggle();
  assert.equal(tree.props['aria-label'],'Chuyển sang giao diện tối');
  tree.props.onClick(); assert.equal(selected,'dark');
  assert.match(renderToStaticMarkup(tree),/type="button"/);
});
test('VI guide label maps to Knowledge Hub in English',async()=>{
  const load=await loader(); const {ENGLISH}=load('features/shared/context/LocaleContext.tsx');
  assert.equal(ENGLISH['Cẩm nang'],'Knowledge Hub');
});
const vm=require('node:vm');
const fs=require('node:fs');
const ts=require('typescript');
for (const saved of ['light','dark',null,'invalid']) test(`theme initialization handles saved preference ${saved}`,()=>{
  const module={exports:{}};
  const doc={documentElement:{dataset:{}}};
  const source=ts.transpileModule(fs.readFileSync('src/features/shared/utils/theme-init.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText;
  vm.runInNewContext(source,{module,exports:module.exports});
  vm.runInNewContext(module.exports.THEME_INIT,{document:doc,localStorage:{getItem:()=>saved},matchMedia:()=>({matches:true})});
  assert.equal(doc.documentElement.dataset.theme,saved==='light'?'light':'dark');
});
test('blocked browser storage still initializes a usable light theme',()=>{
  const module={exports:{}};
  vm.runInNewContext(ts.transpileModule(fs.readFileSync('src/features/shared/utils/theme-init.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,{module,exports:module.exports});
  const doc={documentElement:{dataset:{}}};
  vm.runInNewContext(module.exports.THEME_INIT,{document:doc,localStorage:{getItem:()=>{throw Error('blocked')} }});
  assert.equal(doc.documentElement.dataset.theme,'light');
});
test('theme provider applies and persists only its own preference',()=>{
  const module={exports:{}}; const writes=[]; const effects=[];
  const doc={documentElement:{dataset:{theme:'dark'}}};
  const values=[];
  vm.runInNewContext(ts.transpileModule(fs.readFileSync('src/features/shared/context/ThemeContext.tsx','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,{
    module,exports:module.exports,document:doc,localStorage:{setItem:(...args)=>writes.push(args)},
    require:id=>id==='react'?{createContext:()=>({Provider:'provider'}),useContext:()=>{},useState:()=>['light',v=>values.push(v)],useEffect:fn=>effects.push(fn)}:require(id)
  });
  const tree=module.exports.ThemeProvider({children:null}); effects[0]();
  assert.equal(values.at(-1),'dark');
  tree.props.value.setTheme('light');
  assert.equal(doc.documentElement.dataset.theme,'light');
  assert.deepEqual(writes,[['vf_theme','light']]);
});
