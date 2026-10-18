const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

test('Step 4b Frontend: ServicePointCard renders workshop, charging station, showroom, and correct source label', () => {
  const cardPath = path.resolve(__dirname, '../src/features/chat/components/ServicePointCard.tsx');
  const cardContent = fs.readFileSync(cardPath, 'utf8');

  // 1. Phải có ID chuẩn để cuộn đến card khi bấm marker
  assert.ok(
    cardContent.includes('id={`service-point-card-${point.id}`}'),
    'ServicePointCard must have id="service-point-card-${point.id}"'
  );

  // 2. Không còn dòng "Chưa xác minh"
  assert.ok(
    !cardContent.includes('Chưa xác minh'),
    'ServicePointCard must not include "Chưa xác minh"'
  );

  // 3. Nhãn nguồn dùng snapshot/VinFast thu thập
  assert.ok(
    cardContent.includes('VinFast (dữ liệu snapshot thu thập)'),
    'ServicePointCard must use snapshot source label'
  );

  // 4. Trạm sạc phải có thông điệp chưa công bố công suất
  assert.ok(
    cardContent.includes('Chưa công bố công suất'),
    'ServicePointCard must display "Chưa công bố công suất" for charging stations'
  );

  // 5. Xưởng dịch vụ có giờ mở cửa, hotline dịch vụ, badge đồng sơn, nút đặt lịch
  assert.ok(
    cardContent.includes('Giờ mở cửa:'),
    'ServicePointCard must display operating hours for workshops'
  );
  assert.ok(
    cardContent.includes('Hotline dịch vụ:'),
    'ServicePointCard must display hotline for workshops'
  );
  assert.ok(
    cardContent.includes('Đồng sơn'),
    'ServicePointCard must display Dong Son badge when applicable'
  );
  assert.ok(
    cardContent.includes('Taxi GSM'),
    'ServicePointCard must display Taxi GSM badge when applicable'
  );
  assert.ok(
    cardContent.includes('Đặt lịch'),
    'ServicePointCard must include booking button when booking_url exists'
  );
});

test('Step 4b Frontend: ServiceMapPanel unifies with Vietmap and dynamic rescue banner', () => {
  const panelPath = path.resolve(__dirname, '../src/features/chat/components/ServiceMapPanel.tsx');
  const panelContent = fs.readFileSync(panelPath, 'utf8');

  // 1. Sử dụng VietmapMiniMap thay vì MapLibre/OSM cũ
  assert.ok(
    panelContent.includes('VietmapMiniMap'),
    'ServiceMapPanel must import and use VietmapMiniMap'
  );
  assert.ok(
    !panelContent.includes('createRasterMapStyle'),
    'ServiceMapPanel must no longer use createRasterMapStyle or OSM tiles'
  );

  // 2. Sử dụng component ServicePointCard dùng chung
  assert.ok(
    panelContent.includes('ServicePointCard'),
    'ServiceMapPanel must use shared ServicePointCard component'
  );

  // 3. Banner cứu hộ động hiển thị đầu tiên khi rescueHotline có giá trị
  assert.ok(
    panelContent.includes('rescueHotline &&'),
    'ServiceMapPanel must conditionally render rescue hotline banner'
  );
  assert.ok(
    panelContent.includes('tel:${rescueHotline.replace(/[^0-9]/g, "")}'),
    'Rescue hotline link must use dynamic phone number from response'
  );

  // 4. Hỗ trợ truy vấn theo caseId khi có mã hồ sơ
  assert.ok(
    panelContent.includes('getCaseServicePoints(caseId)'),
    'ServiceMapPanel must fetch from getCaseServicePoints when caseId is provided'
  );

  // 5. Xử lý trạng thái no_points_nearby
  assert.ok(
    panelContent.includes('noPointsNearby'),
    'ServiceMapPanel must handle no_points_nearby empty state'
  );
});

test('Step 4b Frontend: VietmapMiniMap styles markers by category and auto-scrolls to card on click', () => {
  const miniMapPath = path.resolve(__dirname, '../src/features/chat/components/VietmapMiniMap.tsx');
  const miniMapContent = fs.readFileSync(miniMapPath, 'utf8');

  // 1. Marker màu riêng cho từng loại điểm:
  assert.ok(
    miniMapContent.includes('bg-emerald-600') && miniMapContent.includes('isCharging'),
    'Charging stations must use emerald green marker color'
  );
  assert.ok(
    miniMapContent.includes('bg-blue-600') && miniMapContent.includes('isWorkshop'),
    'Workshops must use blue marker color'
  );
  assert.ok(
    miniMapContent.includes('bg-amber-600') && miniMapContent.includes('isShowroom'),
    'Showrooms must use amber marker color'
  );

  // 2. Số thứ tự trên marker khớp số card
  assert.ok(
    miniMapContent.includes('pinEl.textContent = String(index + 1)'),
    'Marker pin number must match 1-based card index'
  );

  // 3. Chạm marker cuộn đến card tương ứng
  assert.ok(
    miniMapContent.includes('document.getElementById(`service-point-card-${point.id}`)') &&
      miniMapContent.includes('scrollIntoView'),
    'Clicking a marker pin must scroll the corresponding service point card into view'
  );

  // 4. Chấm vị trí khách chỉ hiển thị khi có userLocation từ trình duyệt
  assert.ok(
    miniMapContent.includes('if (userLocation)'),
    'Client position marker must only be drawn when userLocation is present'
  );
});

test('Step 4b Frontend: NearbyResults in chat uses ServicePointCard and passes caseId to ServiceMapPanel', () => {
  const nearbyPath = path.resolve(__dirname, '../src/features/chat/components/NearbyResults.tsx');
  const nearbyContent = fs.readFileSync(nearbyPath, 'utf8');

  assert.ok(
    nearbyContent.includes('ServicePointCard'),
    'NearbyResults must import and render ServicePointCard'
  );
  assert.ok(
    nearbyContent.includes('caseId={caseId}'),
    'NearbyResults must forward caseId to ServiceMapPanel'
  );
  assert.ok(
    !nearbyContent.includes('Chưa xác minh hoạt động hiện tại'),
    'NearbyResults must not display obsolete "Chưa xác minh" label'
  );
});
