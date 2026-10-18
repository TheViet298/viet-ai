const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const icons = require('lucide-react');

function renderSupportCard(currentCase) {
  const source = fs.readFileSync(require.resolve('../src/app/track-case/page.tsx'),'utf8');
  const card = source.match(/\{\/\*[\s=]*Card 2:[\s\S]*?\*\/\}([\s\S]*?)\{\/\* Card 3:/)[1].trim();
  const module = {exports:{}};
  const code = ts.transpileModule('exports.card = ('+card+');',{compilerOptions:{
    module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2020,
  }}).outputText;
  const servicePointsData = currentCase?.suggestedServicePoints?.length ? { recommended_points: currentCase.suggestedServicePoints.map(p => ({ display_name: p.address, address: p.address, distance_km: p.distance ? parseFloat(p.distance) : null, distance_from_area_km: null })) } : null;
  vm.runInNewContext(code,{module,exports:module.exports,require,currentCase,servicePointsData,showTechDetails:false,VietmapMiniMap:()=>null,clientUserCoord:null,isRequestingLocation:false,handleShareLocation:()=>{},t:text=>text,encodeURIComponent,...icons});
  return renderToStaticMarkup(module.exports.card);
}

test('unlocated case support card invents neither distance nor a directions destination',()=>{
  const html=renderSupportCard({locationShared:false,stationLocation:'Gợi ý: Trạm sạc / Xưởng dịch vụ VinFast gần nhất',suggestedServicePoints:[]});
  assert.doesNotMatch(html,/1\.2 km|Khoảng cách:|maps\.google\.com|Chỉ đường/);
});

test('provided location keeps directions without inventing a measured distance',()=>{
  const address='12 Nguyễn Huệ, Hồ Chí Minh';
  const html=renderSupportCard({locationShared:true,stationLocation:address,suggestedServicePoints:[]});
  assert.ok(html.includes(encodeURIComponent(address)));
  assert.doesNotMatch(html,/1\.2 km|Khoảng cách:/);
});

test('provided support-point measurements and address are preserved',()=>{
  const address='Verified service address';
  const html=renderSupportCard({locationShared:true,stationLocation:'Actual customer location',suggestedServicePoints:[{address,distance:'7.4 km'}]});
  assert.match(html,/7\.4 km/);
  assert.ok(html.includes(encodeURIComponent(address)));
});
