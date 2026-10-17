const test = require('node:test');
const assert = require('node:assert/strict');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const {loader} = require('./render-loader.cjs');

async function footer(language) {
  const load = await loader({
    'next/navigation': {usePathname: () => '/chat'},
    '../context/AuthContext': {useAuth: () => ({role:'GUEST'})},
  });
  const {LocaleProvider} = load('features/shared/context/LocaleContext.tsx');
  const {Footer} = load('features/shared/components/Footer.tsx');
  return renderToStaticMarkup(React.createElement(LocaleProvider,{initialLanguage:language},React.createElement(Footer)));
}

test('English footer localizes shared links and roadside label while keeping their destinations', async()=>{
  const html=await footer('en');
  for(const label of ['Chat Assistant','My requests','Technical guide','Privacy policy','Emergency roadside assistance:']) assert.ok(html.includes(label),label);
  assert.doesNotMatch(html,/Trợ lý Chat|Yêu cầu của tôi|Cẩm nang kỹ thuật|Chính sách bảo mật|Cứu hộ khẩn cấp:/);
  for(const href of ['/chat','/track-case','/#knowledge-hub','tel:1900232389']) assert.ok(html.includes(`href="${href}"`),href);
});

test('Vietnamese remains the default footer locale',async()=>{
  const html=await footer(undefined);
  for(const label of ['Trợ lý Chat','Yêu cầu của tôi','Cẩm nang kỹ thuật','Chính sách bảo mật','Cứu hộ khẩn cấp:']) assert.ok(html.includes(label),label);
});
