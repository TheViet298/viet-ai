# Kế hoạch khắc phục giới hạn GPS desktop

Ngày lập: 13/10/2026.

Nguồn: [completion-report.md](completion-report.md), mã hiện tại và kế hoạch đã trao đổi với người dùng.

Trạng thái cập nhật 14/10/2026: **Đã triển khai các phần cục bộ; còn giới hạn kiểm chứng và phụ thuộc bên ngoài.** Xem [remediation-verification-report.md](remediation-verification-report.md) để biết phân công, tệp sửa, kiểm thử thực tế và phần chưa xác minh. Nội dung bên dưới giữ tiêu chí nghiệm thu ban đầu; không phải mọi tiêu chí đã đạt.

## 1. Mục tiêu và thứ tự thực hiện

Thứ tự đề xuất:

1. Sửa hydration của trang chat.
2. Bổ sung E2E có đăng nhập và backend thật cục bộ.
3. Kiểm tra đa trình duyệt, thiết bị thật, HTTPS và privacy qua proxy.
4. Mở rộng nhập địa chỉ thủ công.
5. Chuẩn bị nguồn điểm dịch vụ và tile cho sử dụng thực tế.
6. Review theo từng phần và cập nhật bằng chứng.

Giữ các ràng buộc hiện tại: chỉ lấy vị trí sau consent; luôn có nhập tay; không lưu lịch sử tọa độ mặc định; dữ liệu demo phải có nhãn. Không tự tạo API key hoặc triển khai production. Trạng thái trụ sạc trực tiếp, booking và điều phối cần scope và nguồn tích hợp riêng.

## 2. P0 — Sửa hydration của trang chat

### Hiện trạng

- `frontend/src/features/chat/components/ChatMessageItem.tsx` gọi `new Date()` trực tiếp khi render giờ hiển thị.
- `frontend/src/features/chat/hooks/useChat.ts` tạo timestamp lời chào riêng ở server và client.
- Đây là các nguồn nghi ngờ cụ thể; cần tái hiện để xác nhận toàn bộ nguyên nhân lỗi React #425/#423.

### Công việc

1. Hiển thị giờ từ `message.timestamp`, tránh dùng giờ render.
2. Với lời chào chưa có timestamp chung, giữ nội dung ban đầu giống nhau giữa server/client; chỉ bổ sung giờ sau mount hoặc truyền timestamp ổn định.
3. Kiểm tra thêm dữ liệu khởi tạo phụ thuộc môi trường nếu lỗi còn xuất hiện.
4. Thêm test hồi quy cho timestamp và hydration trên production build.

### Tệp dự kiến

- `frontend/src/features/chat/components/ChatMessageItem.tsx`
- `frontend/src/features/chat/hooks/useChat.ts`
- Test hồi quy trong `frontend/tests/` và bộ E2E ở bước tiếp theo.

### Nghiệm thu

- Production build không báo hydration khi tải/reload, kể cả khác múi giờ và thời điểm chuyển phút.
- Giờ tin nhắn không đổi khi gõ chat hoặc cập nhật GPS.
- Các luồng khôi phục chat, lời chào và GPS vẫn hoạt động.

Nguồn: [React hydrateRoot](https://react.dev/reference/react-dom/client/hydrateRoot) yêu cầu nội dung render ban đầu phía server và client khớp nhau.

## 3. P0 — Đưa kiểm thử browser vào repository

### Công việc

1. Đề xuất bổ sung Playwright và cấu hình E2E có thể chạy lại, thay cho harness chỉ nằm trong `/tmp`.
2. Chạy production build với backend thật cục bộ, DB tạm và tài khoản giả lập; tắt LLM/tracing.
3. Đăng nhập bằng luồng auth hiện có, tạo case và kiểm tra chia sẻ GPS trước/sau khi tạo case.
4. Kiểm tra chuỗi `GPS → MANUAL → NOT_SHARED`, dữ liệu lưu và quyền sở hữu case; khách A không thể cập nhật case của khách B.
5. Giữ nhóm test response giả lập riêng để kiểm tra race, timeout và mất mạng.
6. Chặn chạy dev/build cùng thư mục `.next` trong lúc E2E.

### Tệp dự kiến

- `frontend/package.json`, `frontend/package-lock.json`
- Tệp mới `frontend/playwright.config.ts`
- Test mới trong `frontend/tests/e2e/`
- Fixture/backend test liên quan
- `scripts/verify-gps.sh`

### Nghiệm thu

- Consent, cleanup, throttle, callback/request muộn, worker, bản đồ và chỉ đường được kiểm tra tự động.
- Test E2E xác nhận đồng bộ/xóa vị trí bằng backend thật cục bộ, không chỉ response giả lập.
- Kết quả phân biệt rõ test tích hợp thật và test giả lập lỗi.
- Test dùng dữ liệu giả lập, có teardown và không phụ thuộc tài khoản người dùng thật.

Nguồn: [Playwright geolocation emulation](https://playwright.dev/docs/emulation#geolocation).

## 4. P1 — Kiểm tra đa trình duyệt và thiết bị thật

### Công việc

1. Tự động hóa trên Chromium và Firefox.
2. Kiểm tra trực tiếp Chromium/Firefox desktop trên máy có sẵn.
3. Thử quyền Allow/Block thật, mạng dây/Wi-Fi, sai số lớn, mất mạng, đóng tính năng và điều hướng khỏi trang.
4. Kiểm tra consent trên HTTPS; không ghi tọa độ thật vào ảnh, log hoặc báo cáo.

### Tệp dự kiến

- `frontend/playwright.config.ts`
- `frontend/tests/e2e/`
- Tài liệu ma trận kiểm thử trong `docs/gps_plans/`

### Nghiệm thu

- Có ma trận kết quả theo browser/OS và ghi rõ ca chưa chạy.
- Phạm vi kiểm thử browser: Chromium và Firefox; kết quả headless không thay thế kiểm thử thiết bị thật.
- Không hứa bảo đảm độ chính xác GPS của desktop; hiển thị sai số và fallback vẫn phải hoạt động.

## 5. P1 — HTTPS, cấu hình API và privacy qua reverse proxy

### Hiện trạng

`chatApi.ts`, `AuthContext.tsx` và Docker Compose còn dùng mặc định `http://localhost:8000`; cần xử lý trước khi kiểm thử từ máy khác. Middleware hiện tại bảo vệ access log phía ứng dụng, chưa bao phủ proxy bên ngoài.

### Công việc

1. Chuẩn hóa cấu hình API; ưu tiên cùng origin qua `/api/v1`.
2. Chuẩn bị reverse proxy cho môi trường kiểm thử HTTPS.
3. Cấu hình access log không ghi query vị trí; kiểm tra cả log proxy, ứng dụng và tracing.
4. Dùng tọa độ giả lập dễ nhận diện để kiểm tra không xuất hiện trong log, kể cả response lỗi.
5. Kiểm tra worker MapLibre, tile và API không gặp mixed content.

### Tệp dự kiến

- `frontend/src/features/chat/api/chatApi.ts`
- `frontend/src/features/shared/context/AuthContext.tsx`
- `frontend/next.config.js`
- `docker-compose.yml`
- Cấu hình reverse proxy mới, xác định vị trí tệp khi chọn công cụ.
- `src/services/location_privacy.py` nếu kiểm thử phát hiện thiếu sót.
- Test privacy liên quan trong `tests/`.

### Nghiệm thu

- Đăng nhập và GPS chạy qua HTTPS trên môi trường kiểm thử từ máy khác.
- Không lộ tọa độ trong các lớp log đã kiểm tra.
- Không xuất hiện mixed content; request vẫn tới đúng backend.
- Chưa triển khai production trong bước này.

## 6. P1 — Mở rộng nhập địa chỉ thủ công

### Phần A: Không cần dịch vụ ngoài

1. Tách danh mục khu vực khỏi `ServiceMapPanel.tsx`.
2. Thêm alias, tìm kiếm/chọn khu vực và test địa danh mơ hồ.
3. Giữ nhãn tâm khu vực tham chiếu và khoảng cách ước lượng.

### Phần B: Geocoding

1. Chọn nhà cung cấp và kiểm tra điều khoản, chi phí, quyền sử dụng dữ liệu trước tích hợp.
2. Chỉ truy vấn khi người dùng gửi tìm kiếm; cho chọn kết quả và hiển thị nguồn/độ chính xác rõ ràng.
3. Khi lỗi, vẫn nhập chữ được.
4. Giữ contract hiện tại: tọa độ tham chiếu thủ công phục vụ bản đồ, không tự biến thành GPS hoặc được lưu như tọa độ đã consent.
5. Nếu muốn lưu tọa độ chọn trên bản đồ, thiết kế contract riêng trước khi triển khai.

### Tệp dự kiến

- `frontend/src/features/chat/components/ServiceMapPanel.tsx`
- `frontend/src/features/chat/components/LocationConsentCard.tsx`
- `frontend/src/features/chat/types.ts`
- Tiện ích/danh mục khu vực mới trong feature chat.
- Adapter/API geocoding nếu chọn nhà cung cấp.
- Test manual fallback và geocoding liên quan.

### Nghiệm thu

- Khu vực không nhận diện không tạo khoảng cách giả.
- Kết quả nhập tay không bị ghi nhãn GPS.
- Request cũ không ghi đè địa điểm mới; lỗi dịch vụ không chặn nhập tay.
- Không lưu lịch sử tìm kiếm địa chỉ hoặc tọa độ mặc định.

Nếu dùng Nominatim công cộng, phải tuân thủ giới hạn sử dụng và không dùng làm autocomplete phía client. Nguồn: [Chính sách Nominatim](https://operations.osmfoundation.org/policies/nominatim/).

## 7. P2 — Chuẩn bị nguồn trạm và tile cho sử dụng thực tế

### Công việc

1. Tách danh mục demo khỏi route `src/api/customer.py` thành service có adapter.
2. Xác định nguồn danh mục chuẩn cho nearby và kiểm tra tính đồng nhất giữa backend và fallback frontend; không thay fixture của agent một cách mặc định vì có contract riêng.
3. Bổ sung thông tin nguồn, ngày cập nhật, trạng thái xác minh và cờ demo.
4. Cho phép cấu hình tile provider; giữ attribution và kiểm tra worker tương ứng khi nâng MapLibre.
5. Chỉ tích hợp danh mục thật khi có nguồn được phép sử dụng.

### Tệp dự kiến

- `src/api/customer.py`
- Service/adapter danh mục điểm dịch vụ mới trong `src/services/`
- `src/models/schemas.py` nếu mở rộng response metadata.
- `frontend/src/features/chat/constants/servicePoints.ts`
- `frontend/src/features/chat/components/ServiceMapPanel.tsx`
- Fixture danh mục và test đồng nhất/backend/frontend liên quan.
- Cấu hình provider, không chứa API key trong tài liệu hoặc mã nguồn.

### Nghiệm thu

- Demo và dữ liệu được xác minh được phân biệt rõ.
- Metadata nguồn/cập nhật có thể kiểm tra; dữ liệu lỗi không bị giới thiệu là điểm hoạt động đã xác minh.
- Đổi provider không làm mất attribution, worker hoặc fallback danh sách.
- Chưa cung cấp trạng thái trụ trống/bận, booking hoặc điều phối nếu chưa có nguồn vận hành và scope được phê duyệt.

Danh mục địa điểm không đủ để suy ra trạng thái hoạt động trực tiếp. Tile OSM công cộng có chính sách sử dụng riêng: [Tile Usage Policy](https://operations.osmfoundation.org/policies/tiles/).

## 8. Review, bằng chứng và bàn giao

1. Chia thành các thay đổi độc lập theo các bước trên; chạy test phù hợp sau mỗi phần.
2. Review Antigravity theo từng phần nhỏ, gắn với đúng phiên bản mã và kết quả test.
3. Timeout được ghi là chưa có verdict, không tính PASS; không lặp review vô hạn.
4. Sau thay đổi mã, chạy `scripts/verify-gps.sh` và các test E2E liên quan; bổ sung bằng chứng render khi sửa bản đồ.
5. Cập nhật `completion-report.md`: giới hạn đã xử lý, bằng chứng mới và phần còn phụ thuộc bên ngoài.
6. Cập nhật trạng thái commit/push trong báo cáo: câu “chưa commit/push” hiện là snapshot cũ; phiên trước đã push commit `94e3879`.

## 9. Phụ thuộc và ranh giới thực hiện

| Phần | Phụ thuộc |
| --- | --- |
| Hydration | Có thể bắt đầu ngay bằng tái hiện trên production build cục bộ. |
| E2E | Bổ sung dependency/browser binaries và fixture backend cô lập; chạy đầy đủ sau khi xử lý hydration. |
| Đa trình duyệt/thiết bị thật | Bộ E2E và máy/browser tương ứng; HTTPS cho kiểm tra từ máy khác. |
| HTTPS/privacy | Chọn cấu hình proxy và quyền truy cập các lớp log của môi trường kiểm thử. |
| Manual mở rộng | Phần A độc lập dịch vụ ngoài; phần B cần chọn nguồn geocoding phù hợp. |
| Dữ liệu thật/tile | Nguồn dữ liệu được phép sử dụng, lựa chọn provider và quyết định scope tích hợp. |

Việc bổ sung dependency, chọn dịch vụ trả phí, tạo khóa hoặc triển khai production không được thực hiện chỉ từ tài liệu kế hoạch này. Mỗi thay đổi sau khi triển khai phải ghi rõ tệp sửa, kiểm thử thực tế và giới hạn còn lại.
