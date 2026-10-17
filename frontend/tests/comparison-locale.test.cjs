const test=require('node:test'),assert=require('node:assert/strict');
const React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');
const {loader}=require('./render-loader.cjs');

test('English comparison retains already translated specs and localizes legacy charging times',async()=>{
 const load=await loader();
 const {VehicleComparison}=load('features/chat/components/VehicleComparison.tsx');
 const cards=['VF 6 Eco','VF 8 Eco'].map((name,i)=>({
  name,specs:[{label:'Seats',value:'5 seats'},{label:'Range',value:i?'635 km (NEDC)':'485 km (NEDC)'}],
  battery_capacity:i?'87,7 kWh':'59,6 kWh',fast_charge_time:i?'31 phút':'25 minutes',
  price_label:'From 646.000.000 VNĐ',
 }));
 const html=renderToStaticMarkup(React.createElement(VehicleComparison,{cards,language:'en'}));
 for(const value of ['5 seats','485 km (NEDC)','635 km (NEDC)','59,6 kWh','87,7 kWh','31 minutes']) assert.ok(html.includes(value),value);
 assert.doesNotMatch(html,/Data unavailable|phút/);
});
