const test=require('node:test'),assert=require('node:assert/strict');
const React=require('react'),{renderToStaticMarkup}=require('react-dom/server');
const {loader}=require('./render-loader.cjs');

test('English structured cards and comparison localize values without mutating verified data',async()=>{
 const load=await loader();
 const card={name:'VF7 Plus',image_url:'/car.png',verified_at:'2026-10-16',source_url:'https://example.test',
  specs:[{label:'Quãng đường',value:'500,5 km (NEDC)'}],battery_capacity:'87,7 kWh',price_label:'From 830.000.000 VNĐ'};
 const original=JSON.stringify(card);
 const {VehicleInfoCard}=load('features/chat/components/VehicleInfoCard.tsx');
 const {VehicleComparison}=load('features/chat/components/VehicleComparison.tsx');
 for(const html of [renderToStaticMarkup(React.createElement(VehicleInfoCard,{card,language:'en'})),
                   renderToStaticMarkup(React.createElement(VehicleComparison,{cards:[card,{...card,name:'VF8 Plus'}],language:'en'}))]) {
   assert.match(html,/500\.5 km \(NEDC\)/);
   assert.match(html,/830,000,000 VND/);
 }
 assert.equal(JSON.stringify(card),original);
});
