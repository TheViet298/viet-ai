# KẾ HOẠCH KỸ THUẬT CHI TIẾT: TÍNH NĂNG VỊ TRÍ, TÌM ĐIỂM DỊCH VỤ & CHỈ ĐƯỜNG WEB DESKTOP

## 1. Bối cảnh & Phạm vi Kỹ thuật (Scope)
- **Mục tiêu:** Thêm vị trí hiện tại để tìm điểm dịch vụ gần nhất và mở chỉ đường cho khách hàng trên website desktop (tuân thủ ADR-001, ADR-005, AGENTS.md).
- **Scope chính:** `docs/gps_plans/location-feature.md` (Kế hoạch 11/10/2026 cho Website Desktop Browser).
- **Tài liệu tham khảo khảo sát cũ:** `docs/gps_plans/gps-cli-plan-20261012-122832.md` (giữ vai trò dữ liệu tham khảo, không làm thay đổi scope chính).
- **Ranh giới bắt buộc:**
  + Chỉ thiết kế cho desktop browser (Chrome, Edge, Firefox, Brave, Safari trên máy tính/laptop).
  + Định vị theo dõi liên tục khi di chuyển qua `navigator.geolocation.watchPosition()` sau khi khách hàng đồng ý (explicit consent); giải phóng tài nguyên qua `clearWatch(watchId)` khi dừng chia sẻ, chuyển nhập tay, đóng bản đồ hoặc unmount.
  + Luôn có form nhập tay và gợi ý nhanh tỉnh/thành nếu từ chối quyền hoặc lỗi tín hiệu.
  + Bộ lọc 4 phân loại điểm: Trụ sạc (CHARGING_STATION), Showroom (SHOWROOM), Xưởng kỹ thuật (SERVICE_WORKSHOP), Loại khác / Cứu hộ (OTHER). Mặc định là Tất cả (ALL).
  + Bố cục Split View: Cột thông tin/bộ lọc/danh sách trạm bên trái; Bản đồ tương tác và ghim vị trí thời gian thực bên phải.
  + Xử lý sai số: Đọc `coords.accuracy`, hiển thị vòng tròn bán kính sai số trên bản đồ, badge cảnh báo khi `accuracy > 500m`.
  + Deep-link chỉ đường: Google Maps Driving URL và OpenStreetMap (FOSSGIS OSRM); truyền tọa độ origin và destination.
  + Dữ liệu demo có nhãn: Gắn nhãn `[Demo]` rõ ràng, không coi là trạm thực tế đã xác minh.
  + Không lưu lịch sử tọa độ: Chỉ lưu 1 vị trí hiện tại duy nhất/case trong `case_locations` (`unique=True`), xóa tọa độ khi `MANUAL` hoặc `NOT_SHARED`.

---

## 2. So sánh Thiết kế, Khảo sát cũ và Hành vi Code Thực tế (Design vs Reality)

1. **Cơ chế định vị (`watchPosition` vs `getCurrentPosition`):**
   - *Thiết kế (`location-feature.md`):* `watchPosition()` theo dõi liên tục khi mở; gọi `clearWatch(watchId)` khi dừng/đóng/rời/unmount.
   - *Khảo sát cũ:* Đề xuất snapshot 1 lần qua `getCurrentPosition`.
   - *Hành vi Code hiện tại (`CustomerChatContainer.tsx`):* Sử dụng `getCurrentPosition()` (snapshot); hoàn toàn chưa có `watchPosition`, không lưu `watchIdRef`, không có hàm gọi `clearWatch()`, không có nút "Dừng chia sẻ".
2. **Nền tảng & Layout Desktop:**
   - *Thiết kế:* Chỉ thiết kế cho desktop; Split View chia đôi.
   - *Khảo sát cũ & Code hiện tại:* Còn tồn tại mobile bottom-sheet modal (`isMobileModal`) và floating button (`lg:hidden fixed bottom-6 right-4`). Trong `ServiceMapPanel.tsx`, bản đồ được xếp ở trên (45%), danh sách ở dưới (55%) theo chiều dọc, chưa phải Split View ngang chuẩn.
3. **Bộ lọc danh mục:**
   - *Thiết kế:* 4 danh mục (`CHARGING_STATION`, `SHOWROOM`, `SERVICE_WORKSHOP`, `OTHER`).
   - *Hành vi Code hiện tại:* `types.ts` và `ServiceMapPanel.tsx` chỉ có `CHARGING_STATION`, `SERVICE_WORKSHOP`, `EXPRESSWAY_RESCUE` (thiếu `SHOWROOM` và `OTHER`). Điểm Smart City (`SP-HN-002`) là Showroom nhưng đang bị gán nhãn `SERVICE_WORKSHOP`.
4. **Xử lý Sai số (Accuracy):**
   - *Thiết kế:* Vẽ vòng tròn bán kính sai số trên bản đồ; hiển thị cảnh báo khi `accuracy > 500m`.
   - *Hành vi Code hiện tại:* `LocationConsentCard.tsx` có badge cảnh báo, nhưng `ServiceMapPanel.tsx` chưa hề vẽ vòng tròn bán kính sai số trên bản đồ (chỉ có radar ping cố định).
5. **Hiển thị Bản đồ khi Nhập tay:**
   - *Thiết kế:* Vị trí nhập tay được gán tọa độ tham chiếu theo tỉnh/thành và hiển thị trên bản đồ.
   - *Hành vi Code hiện tại:* `ServiceMapPanel.tsx` dòng 243 ẩn hoàn toàn iframe bản đồ nếu không có GPS (`{!hasRealGps && <p>...}`). Người dùng nhập tay không xem được bản đồ.
6. **Deep-Link Chỉ đường:**
   - *Thiết kế:* Hỗ trợ cả Google Maps và OpenStreetMap Directions.
   - *Hành vi Code hiện tại:* `distance.ts` đã có cả 2 hàm, nhưng giao diện `ServiceMapPanel.tsx` chỉ đưa ra nút mở Google Maps, chưa có nút mở OpenStreetMap.

---

## 3. Tra cứu Nguồn Chuẩn Quốc tế (Official Standards Reference)

- **W3C / MDN Geolocation API:**
  + `const watchId = navigator.geolocation.watchPosition(successCallback, errorCallback, options);`
  + `navigator.geolocation.clearWatch(watchId);`
  + Options: `{ enableHighAccuracy: true, timeout: 8000, maximumAge: 5000 }`.
  + Vòng đời: Bắt buộc gọi `clearWatch` trong cleanup return function của `useEffect` khi unmount hoặc khi chuyển trạng thái sang manual/stop để tránh rò rỉ bộ nhớ và tiêu tốn pin thiết bị desktop.
- **Google Maps Platform URL Scheme:**
  + Driving Mode URL: `https://www.google.com/maps/dir/?api=1&origin=${origin.lat},${origin.lng}&destination=${dest.lat},${dest.lng}&travelmode=driving`
  + Fallback Search URL: `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`
- **OpenStreetMap Directions (FOSSGIS OSRM):**
  + Routing URL: `https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${origin.lat}%2C${origin.lng}%3B${dest.lat}%2C${dest.lng}`
- **MapLibre GL JS:**
  + Thư viện bản đồ mã nguồn mở WebGL client-side. Tuy nhiên, việc tích hợp đòi hỏi thêm npm dependency (`maplibre-gl`) và nguồn vector tile bên ngoài, xung đột với quy định cấm cài package của task.

---

## 4. Lý do Trả Trạng thái BLOCKED & Quyết định Quan trọng Cần Phê duyệt

1. **Rào cản Dependency & Khóa API:**
   - Thiết kế trong `location-feature.md` đề xuất Google Maps JS API (cần API key) hoặc MapLibre GL JS (cần cài npm package).
   - Ràng buộc task: *"Không tạo API key, cài package, commit, push, deploy, sửa cấu hình/quyền."*
   - Giải pháp thay thế khả thi: Sử dụng giải pháp OpenStreetMap embed iframe kết hợp lớp Ghim SVG/HTML động tính theo Bounding Box (sẵn có trong repo, không cần cài thêm package hay API key). Cần người dùng phê duyệt phương án này.
2. **Quyết định Chuẩn hóa Phân loại Trạm:**
   - Cần phê duyệt việc cập nhật `ServicePointSeed.type` trong `types.ts` và `SEED_SERVICE_POINTS` trong `servicePoints.ts` để hỗ trợ đầy đủ 4 danh mục: `CHARGING_STATION`, `SHOWROOM`, `SERVICE_WORKSHOP`, `OTHER`.
3. **Quyết định Bản đồ cho Vị trí Nhập tay:**
   - Cần phê duyệt việc mở bản đồ căn theo tọa độ tham chiếu của thành phố người dùng đã chọn/nhập tay (thay vì ẩn hoàn toàn bản đồ như code hiện tại).
4. **Quyết định Bố cục Split View Desktop:**
   - Cần phê duyệt cấu trúc Split View ngang (Trái: Info/Filters, Phải: Map) khi mở rộng panel trên màn hình desktop.

---

## 5. Thứ tự Triển khai Chi tiết (Execution Order)

- **Giai đoạn 1: Chuẩn hóa Types & Constants Dữ liệu Hạt giống Demo**
  1. Chỉnh sửa `frontend/src/features/chat/types.ts`: Bổ sung `"SHOWROOM" | "OTHER"` vào `ServicePointSeed.type`; thêm `isTracking?: boolean` vào `UserLocationState`.
  2. Chỉnh sửa `frontend/src/features/chat/constants/servicePoints.ts`: Cập nhật `SEED_SERVICE_POINTS` với 5 trạm chuẩn hóa, gán đúng loại Showroom (`SP-HN-002`) và Cứu hộ (`SP-DN-001`), gắn nhãn demo rõ ràng.
- **Giai đoạn 2: Quản lý Vòng đời `watchPosition` & `clearWatch`**
  3. Chỉnh sửa `frontend/src/features/chat/components/CustomerChatContainer.tsx`:
     - Khởi tạo `watchIdRef = useRef<number | null>(null)`.
     - Thay thế `getCurrentPosition` bằng `navigator.geolocation.watchPosition`.
     - Cài đặt hàm `stopWatchingLocation()` gọi `navigator.geolocation.clearWatch(watchIdRef.current)`.
     - Kích hoạt `stopWatchingLocation()` trong: `useEffect` unmount cleanup, khi bấm nút "Dừng chia sẻ", khi chuyển sang "Nhập khu vực", khi bấm "Bỏ qua", hoặc khi gọi `handleResetAll()`.
     - Thêm cơ chế throttling gọi API backend: Tọa độ bản đồ client cập nhật tức thời; chỉ đồng bộ lên backend `submitCustomerLocation` khi di chuyển $\ge 100\text{m}$ hoặc sau $\ge 30\text{s}$.
- **Giai đoạn 3: Hoàn thiện Split View, Sai số & Deep-link Chỉ đường**
  4. Chỉnh sửa `frontend/src/features/chat/components/LocationConsentCard.tsx`: Bổ sung nút "Dừng chia sẻ" khi đang định vị; giữ các nút preset khu vực (Hà Nội, TP.HCM, Đà Nẵng, Long Thành).
  5. Chỉnh sửa `frontend/src/features/chat/components/ServiceMapPanel.tsx`:
     - Bổ sung đủ 4 tab bộ lọc danh mục.
     - Cho phép hiển thị bản đồ khi ở chế độ `MANUAL` với tọa độ tham chiếu khu vực.
     - Vẽ vòng tròn bán kính sai số dựa trên `coords.accuracy` và hiển thị badge cảnh báo khi `accuracy > 500m`.
     - Bổ sung nút chỉ đường OpenStreetMap (FOSSGIS OSRM) cạnh nút Google Maps.
     - Hiển thị badge `[Demo]` trên từng thẻ trạm.
     - Thiết lập bố cục Split View ngang khi mở rộng trên desktop.
- **Giai đoạn 4: Cập nhật Bộ Kiểm thử Tự động**
  6. Chỉnh sửa `frontend/tests/location-consent-flow.test.cjs`:
     - Bổ sung test case kiểm tra `watchPosition` và đảm bảo `clearWatch` được gọi chính xác khi dừng chia sẻ/reset/unmount.
     - Bổ sung test case lọc theo 4 danh mục.
     - Bổ sung test case kiểm tra hiển thị vòng tròn sai số và bản đồ tham chiếu khi nhập tay.
     - Bổ sung test case kiểm tra sinh link chỉ đường OpenStreetMap.
     - Bổ sung test case xác minh nhãn demo trên dữ liệu hạt giống.

---

## 6. Danh mục Tệp Sửa đổi & Kế hoạch Kiểm thử

### Các tệp sửa đổi dự kiến:
1. `frontend/src/features/chat/types.ts`
2. `frontend/src/features/chat/constants/servicePoints.ts`
3. `frontend/src/features/chat/components/CustomerChatContainer.tsx`
4. `frontend/src/features/chat/components/LocationConsentCard.tsx`
5. `frontend/src/features/chat/components/ServiceMapPanel.tsx`
6. `frontend/tests/location-consent-flow.test.cjs`

### Kế hoạch Kiểm thử (Sẽ chạy sau khi người dùng phê duyệt kế hoạch):
- Kiểm thử đơn vị frontend:
  `node --test frontend/tests/location-consent-flow.test.cjs`
  `node --test frontend/tests/customer-location-api.test.cjs`
- Kiểm thử hồi quy backend:
  `python3 -m pytest tests/test_agents/test_location_and_memory.py tests/test_api/test_location_extraction.py tests/test_api/test_aligned_spec.py`
- Kiểm thử thủ công trên Desktop Browser (`http://localhost:3000/chat`):
  + Kiểm tra cấp quyền Wi-Fi/IP, theo dõi ghim di chuyển.
  + Kiểm tra nút "Dừng chia sẻ" gọi `clearWatch`.
  + Kiểm tra từ chối quyền mở form nhập tay.
  + Kiểm tra các nút lọc 4 danh mục trạm.
  + Kiểm tra link chỉ đường Google Maps & OSM mở tab mới có origin & destination.
  + Kiểm tra F5 tải lại trang reset về PENDING, không lưu ngầm lịch sử tọa độ.


## Quyết định triển khai theo yêu cầu người dùng
Người dùng đã yêu cầu triển khai toàn bộ kế hoạch và tự làm việc với Antigravity.
Bốn danh mục, desktop split view, theo dõi liên tục và nhập tay đã được chấp thuận trong scope; không cần hỏi lại.
MapLibre GL JS được coordinator cài sẵn. Dùng SDK này với raster OSM và attribution đúng, không dùng iframe+overlay, không tạo API key. Đây là cấu hình demo; ghi rõ giới hạn nhà cung cấp tile production.
Không tự cài thêm dependency. Không commit/push/deploy. Chỉ sửa frontend/src/tests/docs GPS, src và tests liên quan.
Bổ sung đầy đủ GET /api/v1/customer/service-points/nearby theo mục 6.1: lat/lng/category/radius_km/limit có validation, Haversine, demo labels và không ghi tọa độ vào DB/log; frontend gọi theo ngưỡng 150m hoặc 30s, loại callback/request cũ khi đổi filter/dừng/nhập tay.
Giữ route case service-points tương thích. Dữ liệu demo đủ SHOWROOM/OTHER/CHARGING_STATION/SERVICE_WORKSHOP, không mô tả trạm đã xác minh hay tình trạng trực tiếp.
Tọa độ watch chỉ nằm RAM, không localStorage/history. Mọi clearWatch khi skip/stop/manual/close/reset/unmount; callback muộn không được phục hồi. Không tự khởi động lại watch khi mở map.
Manual text không tự nhận là GPS; nếu dùng tâm khu vực cần ghi rõ tham chiếu/ước lượng, khu vực không nhận diện không tạo khoảng cách từ Hà Nội giả. Có chọn nhanh khu vực.
MapLibre markers và accuracy circle theo tọa độ địa lý, đúng vị trí khi pan/zoom; dynamic import/client only; map.remove/marker cleanup, fallback lỗi WebGL/network và danh sách vẫn dùng được.
Test phải chạy logic ứng dụng thực, không tự chép lại handler vào test. Bổ sung lifecycle, lỗi, callbacks muộn, throttle, category, selection, API validation/auth/demo/privacy.
Đọc scope gốc để bổ sung các yêu cầu còn thiếu; không coi kế hoạch Antigravity là giới hạn thấp hơn scope.
Coordinator sẽ chạy full verify; chỉ chạy focused checks khi cần. Ghi báo cáo tệp sửa/test/giới hạn thực tế.
