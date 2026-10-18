const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
function mapPoints(providedPoints, caseData = null) {
  let slot = 0;
  const jsx = (type, props) => ({ type, props });
  const react = { useEffect() {}, useMemo: cb => cb(), useRef: v => ({current:v}), useState: v => [slot++ === 2 ? caseData : v, () => {}] };
  const code = ts.transpileModule(fs.readFileSync(path.join(__dirname, '../src/features/chat/components/ServiceMapPanel.tsx'), 'utf8'), {compilerOptions:{module:ts.ModuleKind.CommonJS, jsx:ts.JsxEmit.ReactJSX}}).outputText;
  const exports = {};
  vm.runInNewContext(code, { exports, require(name) {
    if (name==='react') return react;
    if (name==='react/jsx-runtime') return {jsx,jsxs:jsx};
    if (name.includes('VietmapMiniMap')) return {VietmapMiniMap:'map'};
    if (name.includes('distance')) return {calculateHaversineDistanceKm:()=>75};
    return new Proxy({}, {get:(_,key)=>key});
  }});
  const tree = exports.ServiceMapPanel({ isOpen:true, caseId:'CASE-A', providedPoints, servicePoints:[], locationState:{status:'CONSENTED',coords:{lat:10.7,lng:106.7}}, selectedPointId:null, onSelectPoint() {}, onClose() {} });
  function find(n) { if (!n || typeof n!=='object') return; if(n.type==='map') return n.props.points; for(const c of [n.props?.children].flat(Infinity)) { const result=find(c); if(result) return result; } }
  return find(tree);
}
const station = { id:'nearby', name:'Current search', type:'CHARGING_STATION', coords:{lat:10.8,lng:106.8}, distance_km:75 };
test('nearby map normalizes seed coordinates and preserves expanded-radius results', () => {
  const points = mapPoints([station]);
  assert.equal(points.length, 1);
  assert.equal(points[0].latitude, 10.8);
  assert.equal(points[0].longitude, 106.8);
});
test('provided nearby results stay authoritative over recommendations from a case', () => {
  const points = mapPoints([station], {recommended_points:[{id:'old-case',name:'Old case recommendation'}]});
  assert.equal(points[0].id, 'nearby');
});
