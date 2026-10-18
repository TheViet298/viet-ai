# Báo cáo GPS desktop — cập nhật 14/10/2026

Đợt khắc phục giới hạn đã bổ sung hydration ổn định, Playwright production E2E với backend/DB tạm, alias/tìm kiếm khu vực thủ công, adapter danh mục có metadata và cấu hình API/proxy HTTPS thử nghiệm. Chi tiết phân công độc lập, danh sách tệp, bằng chứng mới và các phần chưa xác minh ở [remediation-verification-report.md](remediation-verification-report.md).

Commit `e6b9d9d` đã tồn tại khi tiếp tục phiên này và chứa triển khai GPS trước đó. Phần sửa tiếp và báo cáo trong phiên tiếp tục chưa stage/commit/push. Các tệp hook/logging đang sửa bởi công việc khác được giữ nguyên. Không triển khai production hoặc tạo API key.

## Snapshot lịch sử — 13/10/2026

Các kết quả và trạng thái “chưa sửa/chưa commit” dưới đây là snapshot cũ; dùng báo cáo cập nhật liên kết ở trên cho tình trạng hiện tại.

## Phạm vi và cách phối hợp

Đã đọc `window-context.md` trước, sau đó đọc toàn bộ năm tài liệu có sẵn trong `docs/gps_plans/`. Scope chính là `location-feature.md`; khảo sát CLI cũ không thay thế các quyết định triển khai đã chốt.

Tiếp tục trực tiếp trên `feature/ai-khoi`, upstream `origin/feature/ai-khoi`. Kiểm tra ban đầu chỉ thấy hai tài liệu bàn giao chưa track; phần mã GPS mô tả trong context đã tồn tại trong bản Git hiện tại. Không chạy lại pipeline yêu cầu checkout sạch, không reset/stash/switch/merge.

Antigravity được gọi qua CLI theo cơ chế structured output của `scripts/gps_agent_workflow.py`: nghiên cứu mã hiện tại, chỉ ra finding, rồi review mã và bằng chứng sau sửa. Kết quả review bản sửa các findings nghiên cứu: **PASS**. Hai lượt review bổ sung sau phần bounding box/hotline (toàn component và chỉ hai đoạn thay đổi) đều bị timeout, không có verdict hợp lệ; không coi các lượt này là PASS. Phần bổ sung đã được coordinator kiểm tra bằng full verify và Chrome production render. Các artifact hội thoại và log agent giữ trong `/tmp/gps-resume-review/`, không đưa vào repository.

## Kết quả

- Theo dõi vị trí chỉ sau thao tác đồng ý; dừng watch khi đổi sang nhập tay, dừng chia sẻ, đóng bản đồ, reset hoặc unmount. Callback GPS đến muộn không phục hồi vị trí.
- Có nhập tay/chọn nhanh; từ chối quyền, mất tín hiệu hoặc timeout mở fallback. Khu vực không nhận diện không bị gán tọa độ Hà Nội hoặc khoảng cách giả.
- Tự đồng bộ vị trí khi case được tạo sau khi đã có GPS. Giữ ngưỡng 150 m hoặc 30 giây cho cập nhật GPS; lỗi đồng bộ hiển thị thông báo và cho thử lại. Khi reset chat, thử lại thao tác xóa vẫn nhắm đúng case cũ.
- Lỗi GPS xóa tọa độ đã chia sẻ khỏi case qua payload `NOT_SHARED`. Chuyển sang nhập tay gửi tọa độ null. Hàng đợi API hiện có giữ thứ tự GPS → xóa/chuyển nhập tay.
- MapLibre hoạt động trên production build cục bộ: sửa CSS khung bản đồ để canvas có chiều cao đúng, theo dõi resize, dọn observer/map/marker khi đóng. Worker public hiện có đã được xác minh giống bản worker trong package, không cần thay thêm worker.
- Bản đồ tự căn bounding box chứa vị trí tham chiếu và các điểm được lọc; hiển thị vùng sai số, bốn loại điểm, chi tiết/hotline, Google Maps/OSM và thao tác điền điểm đến vào chat.
- Đổi bộ lọc hoặc chế độ vị trí thay request cũ; phản hồi đến muộn bị bỏ qua. Khi lỗi mạng/WebGL, danh sách demo vẫn dùng được.
- API nearby, validation và bảo vệ query khỏi access log của ứng dụng được giữ và đưa vào full verify. Không bổ sung lịch sử tọa độ hoặc lưu GPS vào localStorage/sessionStorage.

## Tệp thay đổi trong lượt này

| Tệp | Thay đổi |
| --- | --- |
| [CustomerChatContainer.tsx](../../frontend/src/features/chat/components/CustomerChatContainer.tsx) | Đồng bộ theo trạng thái/case, xử lý lỗi và retry, xóa vị trí, bỏ request reset trùng, callback chọn điểm ổn định. |
| [LocationConsentCard.tsx](../../frontend/src/features/chat/components/LocationConsentCard.tsx) | Nhập tay dừng watch ngay; cho phép bỏ qua lúc đang chờ GPS. |
| [ServiceMapPanel.tsx](../../frontend/src/features/chat/components/ServiceMapPanel.tsx) | Sửa dependency, resize/CSS canvas, request theo chế độ, callback sau cleanup, bounding box và hotline. |
| [location-runtime.test.cjs](../../frontend/tests/location-runtime.test.cjs) | Năm test chạy handler/effect TSX thật: consent, tạo case sau GPS, throttle, lỗi GPS, manual, retry, reset/close/unmount và callback muộn. |
| [verify-gps.sh](../../scripts/verify-gps.sh) | Thêm kiểm thử API nearby và privacy vào lượt verify đầy đủ. |
| [test_gps_workflow.py](../../tests/test_scripts/test_gps_workflow.py) | Cập nhật test timeout để xác nhận verifier tiếp tục qua đủ bảy nhóm kiểm tra. |
| [window-context.md](window-context.md) | Ghi trạng thái mới, giữ bản bàn giao cũ làm lịch sử. |
| [completion-report.md](completion-report.md) | Báo cáo này. |

`gps-agent-implementation-plan.md` là tài liệu chưa track đã có từ trước lượt này, không sửa nội dung.

## Kiểm thử và bằng chứng

`./scripts/verify-gps.sh` trên bản cuối trả exit 0:

- Frontend lint: không lỗi/cảnh báo.
- Frontend Node tests: **49 passed**.
- TypeScript: pass.
- Backend location/memory/extraction: **26 passed**.
- Backend location API regression: **1 passed**, 15 test ngoài lựa chọn không chạy.
- Backend nearby API/privacy: **3 passed**.
- Next.js production build: pass.

`python3 -m unittest discover -s tests/test_scripts -p 'test_gps*.py' -v`: **14 passed**.

Lượt verify đầu bị timeout ở hai nhóm backend trong sandbox. Chạy lại ngoài sandbox, vẫn tắt LLM và tracing, các nhóm này qua; không coi lượt timeout ban đầu là pass. Chạy dev và build đồng thời từng làm `.next` không nhất quán; đã dừng server, build lại, rồi kiểm tra riêng bằng `next start`.

Chrome headless desktop, dùng hoàn toàn tọa độ giả lập:

- Không watch trước consent; consent tạo watch; cảnh báo sai số lớn hiện.
- Worker/bản đồ OSM render thật trên bản cuối, canvas 270 × 633 px; coordinator đã mở và xem ảnh với đủ ghim trong bounding box, không chỉ kiểm tra có canvas trong DOM. Không có exception mới trong luồng GPS sau hydration.
- Dừng/đóng gọi clearWatch, callback muộn không tạo lại map; chuyển nhập tay lúc chờ cũng clearWatch.
- Từ chối quyền và timeout có form nhập tay; chọn nhanh Đà Nẵng dùng tâm khu vực được ghi rõ là tham chiếu.
- Reload không tự lấy lại GPS hoặc consent.
- Request nhỏ dưới ngưỡng không bị abort; đổi filter abort request cũ; kết quả cũ không thay kết quả mới.
- Link chỉ đường có đúng origin/destination; chọn điểm đến điền đúng tên vào input chat.
- Nhập khu vực không nhận diện không tạo GPS/khoảng cách giả; lỗi WebGL vẫn còn danh sách.

Các harness và log browser nằm trong `/tmp/gps-browser*.py`, `/tmp/gps-browser*.log`; ảnh ở `/tmp/gps-browser.png`. Đây là artifact tạm, không chứa vị trí người dùng thật.

## Giới hạn và trạng thái bàn giao

- Dữ liệu điểm dịch vụ vẫn là **demo**, không xác minh hoạt động/trụ trống, không điều phối hoặc booking thực.
- Manual dùng tâm của một số khu vực được hỗ trợ, không phải geocoder cho mọi địa chỉ. Khoảng cách là đường chim bay; dẫn đường mở dịch vụ ngoài.
- Trang chat production có lúc ghi nhận lỗi hydration React #425/#423 lúc tải trang, trước khi bật GPS; đây là phần render chat ngoài các tệp GPS đã sửa. Các kiểm tra runtime GPS tách riêng sau hydration. Chưa sửa lỗi hydration tổng thể trong lượt này.
- Browser runtime được kiểm tra trên Chrome desktop với geolocation giả lập. Chưa xác minh GPS phần cứng, hộp thoại quyền thật trên mọi OS, hoặc chạy trực tiếp các trình duyệt desktop trong phạm vi kiểm thử.
- API/auth được kiểm thử qua ASGI và fixture; browser chủ yếu kiểm tra phía client, dùng fallback hoặc response giả lập để tạo race. Chưa chạy một phiên E2E đăng nhập trên môi trường backend triển khai thực.
- Cần HTTPS và nhà cung cấp tile/dữ liệu phù hợp trước production. Reverse proxy bên ngoài phải tự cấu hình tránh ghi query tọa độ; middleware hiện tại chỉ bảo vệ access log phía ứng dụng.
- Không tạo khóa API, không cài thêm dependency, không deploy production. **Chưa stage, commit hoặc push.** Next.js và Chrome do task khởi chạy đã được dừng sau kiểm thử.

Nguồn kỹ thuật đối chiếu: [MDN watchPosition](https://developer.mozilla.org/en-US/docs/Web/API/Geolocation/watchPosition), [MapLibre v5 → v6](https://maplibre.org/maplibre-gl-js/docs/guides/v5-to-v6-migration-guide/).
