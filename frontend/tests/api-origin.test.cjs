const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

for (const [modulePath, invoke] of [
  ['features/chat/api/chatApi.ts', api => api.getPublicArticles()],
  ['features/console/api/consoleApi.ts', api => api.getTicketQueue()],
]) for (const base of ['', 'https://api.example.test']) {
  test(`${modulePath} uses ${base || 'same-origin'} API without a browser-localhost dependency`, async () => {
    const calls=[];
    const source=fs.readFileSync(path.join(__dirname,'../src',modulePath),'utf8');
    const module={exports:{}};
    vm.runInNewContext(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,{
      module,exports:module.exports,URLSearchParams,
      process:{env:{NEXT_PUBLIC_API_URL:base}},
      fetch:async url=>{calls.push(url);return {ok:true,json:async()=>({success:true,data:{items:[]}})};},
      require,
    });
    await invoke(module.exports);
    assert.equal(calls.length,1);
    assert.ok(calls[0].startsWith(base+'/api/v1/'),calls[0]);
  });
}

test('same-origin rewrite uses the server-side API origin', async () => {
  const module={exports:{}};
  const source=fs.readFileSync(path.join(__dirname,'../next.config.js'),'utf8');
  vm.runInNewContext(source,{module,process:{env:{API_INTERNAL_URL:'http://backend:8000',NEXT_PUBLIC_API_URL:''}}});
  const rewrites=await module.exports.rewrites();
  assert.equal(rewrites[0].destination,'http://backend:8000/api/v1/:path*');
});
