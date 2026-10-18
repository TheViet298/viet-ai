const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

test('Step 4 Frontend: Rescue banner renders BEFORE all cards and uses dynamic tel hotline', () => {
  const pagePath = path.resolve(__dirname, '../src/app/track-case/page.tsx');
  const content = fs.readFileSync(pagePath, 'utf8');

  // 1. Kiểm tra thứ tự DOM trong cột phải (lg:col-span-4)
  const colRightIdx = content.indexOf('lg:col-span-4');
  assert.ok(colRightIdx > 0, 'lg:col-span-4 column should exist');

  const afterColRight = content.slice(colRightIdx);
  const rescueBannerIdx = afterColRight.indexOf('servicePointsData?.rescue_hotline');
  const card1VehicleIdx = afterColRight.indexOf('Thông tin xe & Dữ kiện');
  const card2ServicePointsIdx = afterColRight.indexOf('Điểm hỗ trợ VinFast');

  assert.ok(rescueBannerIdx > 0, 'Rescue banner should exist in right column');
  assert.ok(card1VehicleIdx > 0, 'Vehicle card should exist in right column');
  assert.ok(card2ServicePointsIdx > 0, 'Service points card should exist in right column');

  // Khẳng định banner cứu hộ xuất hiện TRƯỚC mọi card
  assert.ok(
    rescueBannerIdx < card1VehicleIdx,
    'Rescue hotline banner must render BEFORE Card 1 (Vehicle card) in DOM order'
  );
  assert.ok(
    rescueBannerIdx < card2ServicePointsIdx,
    'Rescue hotline banner must render BEFORE Card 2 (Service points card) in DOM order'
  );

  // 2. Nút gọi điện trong banner cứu hộ dùng đúng số từ response, không hardcode
  const bannerSlice = afterColRight.slice(rescueBannerIdx, card1VehicleIdx);
  assert.ok(
    bannerSlice.includes('tel:${servicePointsData.rescue_hotline.replace(/[^0-9]/g, "")}'),
    'Rescue tel link must dynamically read from servicePointsData.rescue_hotline'
  );
  assert.ok(
    bannerSlice.includes('{servicePointsData.rescue_hotline}'),
    'Rescue banner text must dynamically display servicePointsData.rescue_hotline'
  );
});

test('Step 4 Frontend: Missing NEXT_PUBLIC_VIETMAP_API_KEY hides mini map while cards remain visible', () => {
  const miniMapPath = path.resolve(__dirname, '../src/features/chat/components/VietmapMiniMap.tsx');
  const miniMapContent = fs.readFileSync(miniMapPath, 'utf8');

  // Kiểm tra điều kiện apiKey
  assert.ok(
    miniMapContent.includes('process.env.NEXT_PUBLIC_VIETMAP_API_KEY'),
    'VietmapMiniMap must read NEXT_PUBLIC_VIETMAP_API_KEY from environment'
  );
  assert.ok(
    miniMapContent.includes('!apiKey'),
    'VietmapMiniMap must check !apiKey'
  );
  assert.ok(
    miniMapContent.includes('return null;'),
    'VietmapMiniMap must return null when apiKey is missing without console errors'
  );

  // Kiểm tra track-case/page.tsx render card ngay cả khi không có map
  const pagePath = path.resolve(__dirname, '../src/app/track-case/page.tsx');
  const content = fs.readFileSync(pagePath, 'utf8');
  assert.ok(
    content.includes('<VietmapMiniMap'),
    'track-case/page.tsx must embed VietmapMiniMap'
  );
  assert.ok(
    content.includes('Danh sách các card điểm dịch vụ'),
    'Service points card list must render independently of map'
  );
});

test('Step 4 Frontend: Sparse area no_points_nearby renders message and hides share location button', () => {
  const pagePath = path.resolve(__dirname, '../src/app/track-case/page.tsx');
  const content = fs.readFileSync(pagePath, 'utf8');

  // Nút chia sẻ vị trí bị ẩn khi no_points_nearby = true
  assert.ok(
    content.includes('!servicePointsData?.no_points_nearby'),
    'Share location button must be hidden when no_points_nearby is true'
  );

  // Message tiếng Việt từ backend được hiển thị
  assert.ok(
    content.includes('servicePointsData?.no_points_nearby ?'),
    'Sparse area condition must render custom message block'
  );
  assert.ok(
    content.includes('servicePointsData.message'),
    'Must display dynamic message from response when no_points_nearby is true'
  );
});

test('Step 4 Frontend: Distance display formats according to GPS vs area_reference', () => {
  const pagePath = path.resolve(__dirname, '../src/app/track-case/page.tsx');
  const content = fs.readFileSync(pagePath, 'utf8');

  // Kiểm tra hiển thị "Cách bạn: x.xx km" khi distance_km có giá trị
  assert.ok(
    content.includes('Cách Quý khách: {point.distance_km} km'),
    'Must display "Cách Quý khách: {point.distance_km} km" when distance_km is present'
  );

  // Kiểm tra hiển thị "Khoảng N km từ {areaLabel}" khi distance_km null và distance_from_area_km có giá trị
  assert.ok(
    content.includes('Khoảng {nStr} từ {areaLabel} (đường chim bay, không phải khoảng cách từ vị trí của Quý khách)'),
    'Must display "Khoảng N km từ {area_reference.label}..." when distance_from_area_km is present'
  );
  assert.ok(
    content.includes('roundedKm < 5 ? "dưới 5 km"'),
    'Must display "dưới 5 km" when distance is under 5 km'
  );

  // Types interface check
  const typesPath = path.resolve(__dirname, '../src/features/chat/types.ts');
  const typesContent = fs.readFileSync(typesPath, 'utf8');
  assert.ok(
    typesContent.includes('distance_from_area_km?: number | null;'),
    'ServicePointApiItem must have distance_from_area_km'
  );
  assert.ok(
    typesContent.includes('area_reference?:'),
    'ServicePointsApiResponse must have area_reference'
  );
});

test('Step 4 Frontend: VietmapMiniMap for no-GPS cases does not draw user pin and fits bounds around service points', () => {
  const miniMapPath = path.resolve(__dirname, '../src/features/chat/components/VietmapMiniMap.tsx');
  const miniMapContent = fs.readFileSync(miniMapPath, 'utf8');

  // User location marker is ONLY drawn when userLocation is present
  assert.ok(
    miniMapContent.includes('if (userLocation) {'),
    'User marker must only be created if userLocation is truthy'
  );

  // fitBounds is called on bounds
  assert.ok(
    miniMapContent.includes('instance.fitBounds(bounds'),
    'Must call fitBounds around valid points/bounds'
  );
});
