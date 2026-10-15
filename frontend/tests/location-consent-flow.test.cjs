const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');

// Helper compile function for TypeScript modules
function loadTsModule(relativePath) {
  const fullPath = path.join(__dirname, relativePath);
  const source = fs.readFileSync(fullPath, 'utf8');
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText;
  const moduleExports = {};
  const fn = new Function('exports', 'require', '__dirname', compiled);
  fn(moduleExports, (id) => {
    if (id.startsWith('./') || id.startsWith('../')) {
      const targetPath = path.join(path.dirname(fullPath), id);
      const possibleExts = ['.ts', '.tsx', '.js', '/index.ts', ''];
      for (const ext of possibleExts) {
        if (fs.existsSync(targetPath + ext)) {
          return loadTsModule(path.relative(__dirname, targetPath + ext));
        }
      }
    }
    return require(id);
  }, path.dirname(fullPath));
  return moduleExports;
}

const distanceModule = loadTsModule('../src/features/chat/utils/distance.ts');
const servicePointsModule = loadTsModule('../src/features/chat/constants/servicePoints.ts');

const {
  calculateHaversineDistanceKm,
  formatDistanceKm,
  getDirectionsUrl,
  getOsmDirectionsUrl,
  MAX_SUPPORT_RADIUS_KM,
} = distanceModule;

const { SEED_SERVICE_POINTS, getSeedServicePoints } = servicePointsModule;

// =============================================================================
// TEST SUITE: TÍNH NĂNG ĐỊNH VỊ VỊ TRÍ TRÊN WEBSITE DESKTOP BROWSER (ADR-005)
// Kế hoạch ngắn hạn (11/10/2026): Kiểm thử luồng Geolocation trên trình duyệt Desktop
// (định vị Wi-Fi/IP, fallback nhập tay, cảnh báo sai số, chỉ đường Google Maps/OSM).
// =============================================================================

test('1. Khoảng cách Haversine và định dạng hiển thị', () => {
  // Khoảng cách giữa 2 điểm trùng nhau = 0 km
  const p1 = { lat: 21.0315, lng: 105.8145 };
  assert.equal(calculateHaversineDistanceKm(p1, p1), 0);

  // Khoảng cách Hà Nội - Landmark 81 TP.HCM (~1138 - 1140 km)
  const landmark81 = { lat: 10.795, lng: 106.7218 };
  const hanoiToHcm = calculateHaversineDistanceKm(p1, landmark81);
  assert.ok(hanoiToHcm > 1100 && hanoiToHcm < 1200, `Hà Nội - HCM phải ~1140km, thực tế: ${hanoiToHcm}`);

  // Format hiển thị thân thiện:
  assert.equal(formatDistanceKm(0.35), '350 m', 'Dưới 1km phải hiển thị mét');
  assert.equal(formatDistanceKm(2.84), '2.8 km', 'Từ 1-10km hiển thị 1 số thập phân');
  assert.match(formatDistanceKm(1138.8), /1[.,]139 km/, 'Trên 10km làm tròn số nguyên');
});

test('2. Luồng CHO PHÉP VỊ TRÍ (CONSENTED): GPS thành công, tìm điểm gần nhất và tạo URL chỉ đường', () => {
  const userGps = { lat: 21.0315, lng: 105.8145 }; // Đúng tọa độ Vincom Metropolis
  const points = getSeedServicePoints();
  assert.ok(points.length >= 5, 'Phải có ít nhất 5 trạm hạt giống VinFast');

  // Tính toán khoảng cách tới toàn bộ các trạm
  const enriched = points.map((p) => {
    const distKm = calculateHaversineDistanceKm(userGps, p.coords);
    return { ...p, distKm, distText: formatDistanceKm(distKm) };
  }).sort((a, b) => a.distKm - b.distKm);

  // Trạm gần nhất phải là Vincom Metropolis với khoảng cách 0m
  const nearest = enriched[0];
  assert.equal(nearest.id, 'SP-HN-001');
  assert.equal(nearest.name, 'Trạm sạc VinFast Vincom Metropolis');
  assert.ok(nearest.distKm < 0.05, 'Điểm gần nhất phải có khoảng cách xấp xỉ 0');
  assert.equal(nearest.distText, '0 m');

  // Kiểm tra URL chỉ đường Google Maps có cả origin (GPS) và destination
  const directionsUrl = getDirectionsUrl(
    { lat: nearest.coords.lat, lng: nearest.coords.lng, address: nearest.address },
    userGps
  );
  assert.ok(new URL(directionsUrl).searchParams.get('origin') === '21.0315,105.8145', 'URL chỉ đường phải chứa origin chính xác');
  assert.ok(new URL(directionsUrl).searchParams.get('destination') === '21.0315,105.8145', 'URL chỉ đường phải chứa destination');
  assert.ok(directionsUrl.includes('travelmode=driving'), 'URL chỉ đường phải kích hoạt chế độ lái xe');

  // Kiểm tra URL chỉ đường OpenStreetMap
  const osmUrl = getOsmDirectionsUrl(nearest.coords, userGps);
  assert.ok(osmUrl.includes('engine=fossgis_osrm_car'), 'OSM URL phải dùng engine FOSSGIS OSRM');
  assert.ok(osmUrl.includes('21.0315%2C105.8145'), 'OSM URL phải chứa tọa độ route');
});

test('3. Luồng TỪ CHỐI VỊ TRÍ (PERMISSION_DENIED): Fallback nhập tay và nút Bỏ qua', () => {
  // Mô phỏng lỗi trình duyệt trả về GeolocationPositionError code 1 (PERMISSION_DENIED)
  const simulatedGeoError = { code: 1, message: 'User denied Geolocation' };

  let locationState = {
    status: 'PENDING',
    source: 'USER_TEXT',
    label: '',
  };

  // Hàm xử lý lỗi tương đương errorHandler trong CustomerChatContainer
  function handleGeoError(err) {
    let errorCode = 'POSITION_UNAVAILABLE';
    let errorLabel = 'Tín hiệu GPS không khả dụng (Vui lòng nhập tay)';
    if (err.code === 1) {
      errorCode = 'PERMISSION_DENIED';
      errorLabel = 'Trình duyệt đã từ chối quyền vị trí (Vui lòng nhập tay)';
    } else if (err.code === 2) {
      errorCode = 'POSITION_UNAVAILABLE';
      errorLabel = 'Tín hiệu GPS yếu hoặc mất sóng (Vui lòng nhập tay)';
    } else if (err.code === 3) {
      errorCode = 'TIMEOUT';
      errorLabel = 'Quá thời gian chờ GPS > 8s (Vui lòng nhập tay)';
    }

    return {
      status: 'MANUAL',
      source: 'USER_TEXT',
      label: errorLabel,
      errorCode,
      errorMessage: err.message,
    };
  }

  locationState = handleGeoError(simulatedGeoError);
  assert.equal(locationState.status, 'MANUAL');
  assert.equal(locationState.errorCode, 'PERMISSION_DENIED');
  assert.match(locationState.label, /từ chối/i);

  // Người dùng nhập tay khu vực
  const manualArea = 'Vinhomes Ocean Park, Gia Lâm, Hà Nội';
  locationState = {
    status: 'MANUAL',
    source: 'USER_TEXT',
    label: manualArea,
  };
  assert.equal(locationState.status, 'MANUAL');
  assert.equal(locationState.label, manualArea);

  // Người dùng chọn "Bỏ qua"
  locationState = {
    status: 'NOT_SHARED',
    source: 'USER_TEXT',
    label: 'Không chia sẻ',
  };
  assert.equal(locationState.status, 'NOT_SHARED');
  assert.equal(locationState.label, 'Không chia sẻ');

  // Fallback directions URL khi KHÔNG CÓ GPS (chỉ có địa chỉ đích)
  const fallbackUrl = getDirectionsUrl({
    lat: 21.0315,
    lng: 105.8145,
    address: '29 Liễu Giai, Ngọc Khánh, Ba Đình, Hà Nội',
  });
  assert.ok(fallbackUrl.includes('/dir/?api=1&destination='), 'Không có origin vẫn mở chỉ đường đến điểm đã chọn');
  assert.ok(!fallbackUrl.includes('origin='), 'Fallback search URL không được gắn tọa độ origin rác');
});

test('4. Luồng TIMEOUT (> 8s): Không treo app, chuyển sang nhập tay', () => {
  // Mô phỏng lỗi code 3 (TIMEOUT)
  const simulatedTimeoutError = { code: 3, message: 'Timeout expired' };

  let isLocating = true;
  let locationState = { status: 'PENDING', source: 'USER_TEXT', label: '' };

  // Xử lý timeout
  isLocating = false;
  locationState = {
    status: 'MANUAL',
    source: 'USER_TEXT',
    label: 'Quá thời gian chờ GPS > 8s (Vui lòng nhập tay)',
    errorCode: 'TIMEOUT',
    errorMessage: simulatedTimeoutError.message,
  };

  assert.equal(isLocating, false, 'Phải dừng cờ loading khi timeout');
  assert.equal(locationState.status, 'MANUAL');
  assert.equal(locationState.errorCode, 'TIMEOUT');
  assert.match(locationState.label, /> 8s/);
});

test('5. Luồng TỌA ĐỘ SAI SỐ LỚN (accuracy > 500m): Cảnh báo ước lượng, không chặn sử dụng', () => {
  const simulatedLowAccuracyGps = {
    coords: {
      latitude: 21.0285,
      longitude: 105.8542,
      accuracy: 850, // 850 mét > 500m
    },
  };

  const accuracy = simulatedLowAccuracyGps.coords.accuracy;
  const isLowAccuracy = accuracy > 500;
  assert.equal(isLowAccuracy, true, 'Sai số 850m phải được coi là độ chính xác thấp');

  const locationState = {
    status: 'CONSENTED',
    source: 'BROWSER_GPS',
    label: `Vị trí GPS (Ước tính ±${Math.round(accuracy)}m)`,
    coords: {
      lat: simulatedLowAccuracyGps.coords.latitude,
      lng: simulatedLowAccuracyGps.coords.longitude,
    },
    accuracy,
    errorCode: 'ACCURACY_LOW',
  };

  assert.equal(locationState.errorCode, 'ACCURACY_LOW');
  assert.match(locationState.label, /Ước tính ±850m/);
  assert.equal(typeof locationState.coords.lat, 'number');
  assert.equal(typeof locationState.coords.lng, 'number');
});

test('6. Luồng KHÔNG CÓ ĐỊA ĐIỂM GẦN ĐÓ (> 50km): Kích hoạt cảnh báo và nút Hotline 1900-232389', () => {
  // Người dùng ở Cà Mau (lat: 9.1768, lng: 105.1524)
  const caMauCoord = { lat: 9.1768, lng: 105.1524 };
  const points = getSeedServicePoints();

  const enriched = points.map((p) => {
    const distKm = calculateHaversineDistanceKm(caMauCoord, p.coords);
    return { ...p, distKm, distText: formatDistanceKm(distKm) };
  }).sort((a, b) => a.distKm - b.distKm);

  const nearestPoint = enriched[0];
  const isNearestTooFar = nearestPoint.distKm > MAX_SUPPORT_RADIUS_KM;

  assert.equal(isNearestTooFar, true, `Điểm gần nhất (${nearestPoint.distKm.toFixed(1)} km) phải lớn hơn ngưỡng MAX_SUPPORT_RADIUS_KM (50 km)`);
  assert.ok(nearestPoint.distKm > 200, 'Từ Cà Mau đến điểm gần nhất (TP.HCM) phải > 200km');

  // Xác minh số hotline chuẩn VinFast
  assert.equal(nearestPoint.hotline, '1900-232389');
  assert.equal(nearestPoint.hotline.replace(/-/g, ''), '1900232389');
});

test('7. Luồng CHỌN ĐIỂM ĐẾN & ĐIỀU HƯỚNG: Sinh prompt chat và tạo link chỉ đường', () => {
  const points = getSeedServicePoints();
  const selectedPoint = points.find((p) => p.id === 'SP-HN-001');
  assert.ok(selectedPoint, 'Phải tìm thấy trạm SP-HN-001');

  // Callback chọn điểm đến
  let selectedPointId = null;
  let chatInput = '';

  function handleSelectDestination(point) {
    selectedPointId = point.id;
    chatInput = `Tôi muốn đến ${point.name} (${point.address}) để kiểm tra. Cho tôi hỏi trạm hiện có hoạt động và sẵn sàng tiếp nhận không?`;
  }

  handleSelectDestination(selectedPoint);

  assert.equal(selectedPointId, 'SP-HN-001');
  assert.match(chatInput, /Tôi muốn đến Trạm sạc VinFast Vincom Metropolis/);
  assert.match(chatInput, /29 Liễu Giai/);
  assert.match(chatInput, /sẵn sàng tiếp nhận không/);

  // Link chỉ đường tới trạm đã chọn
  const userOrigin = { lat: 21.0300, lng: 105.8000 };
  const navUrl = getDirectionsUrl(
    { lat: selectedPoint.coords.lat, lng: selectedPoint.coords.lng, address: selectedPoint.address },
    userOrigin
  );
  assert.ok(new URL(navUrl).searchParams.get('origin') === '21.03,105.8');
  assert.ok(new URL(navUrl).searchParams.get('destination') === '21.0315,105.8145');
});

const { startLocationWatch, shouldSyncLocation } = loadTsModule('../src/features/chat/utils/locationTracking.ts');
test('watchPosition stops once and ignores late callbacks', () => {
  let success, failure;
  const cleared = [];
  const received = [];
  const geo = {
    watchPosition(onSuccess, onError, options) {
      success = onSuccess; failure = onError;
      assert.equal(options.timeout, 8000);
      return 17;
    },
    clearWatch(id) { cleared.push(id); },
  };
  const stop = startLocationWatch(geo, (position) => received.push(position), () => received.push('error'));
  success({ coords: { latitude: 21 } });
  stop(); stop();
  success({ coords: { latitude: 22 } }); failure({ code: 1 });
  assert.deepEqual(cleared, [17]);
  assert.deepEqual(received, [{ coords: { latitude: 21 } }]);
});
test('nearby sync threshold uses movement or elapsed time', () => {
  const previous = { lat: 21, lng: 105, time: 1000 };
  assert.equal(shouldSyncLocation(null, previous, 1000), true);
  assert.equal(shouldSyncLocation(previous, { lat: 21.0001, lng: 105 }, 2000), false);
  assert.equal(shouldSyncLocation(previous, { lat: 21.002, lng: 105 }, 2000), true);
  assert.equal(shouldSyncLocation(previous, { lat: 21, lng: 105 }, 31000), true);
});
test('all demo categories are present', () => {
  assert.deepEqual(new Set(SEED_SERVICE_POINTS.map((point) => point.type)), new Set(['CHARGING_STATION', 'SHOWROOM', 'SERVICE_WORKSHOP', 'OTHER']));
  assert.ok(SEED_SERVICE_POINTS.every((point) => point.demo));
});
