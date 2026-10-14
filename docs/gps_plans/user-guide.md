# Hướng dẫn thử GPS trên desktop

Hướng dẫn này dành cho Customer đã đăng nhập. Điểm dịch vụ hiện là dữ liệu demo, chưa xác minh; không có booking hoặc điều phối thật.

## Chạy bản thử

Trước khi bắt đầu, dừng các server GPS cũ bằng `Ctrl+C` trong từng terminal để giải phóng cổng `18000` và `13000`. Mở hai terminal mới tại thư mục repository và chạy `clear` (hoặc `Ctrl+L`) để bắt đầu với màn hình terminal sạch.

Terminal 1 — backend, dùng database tạm:

```bash
python3 scripts/gps-e2e-server.py backend
```

Terminal 2 — frontend:

```bash
python3 scripts/gps-e2e-server.py frontend
```

Đợi cả hai server sẵn sàng. Mở `http://127.0.0.1:13000/register`, tạo tài khoản thử bằng thông tin giả, rồi vào `/chat`. Database tạm bị xóa khi dừng backend. Chat chạy chế độ không có LLM nên phản hồi có thể đơn giản.

## Thử tìm địa điểm

1. Chọn **Tìm điểm gần đây**. Chỉ chọn **Dùng vị trí hiện tại** nếu muốn trình duyệt xin quyền GPS; chọn Allow để chia sẻ vị trí.
2. Nếu từ chối quyền hoặc GPS lỗi, chọn **Nhập khu vực** để tìm/chọn khu vực thủ công. Địa chỉ chưa nhận diện vẫn có thể nhập nhưng không được gán tọa độ hay khoảng cách giả.
3. Lọc loại điểm và chọn một địa điểm. Khoảng cách là đường chim bay.
4. Dùng link Google Maps hoặc OpenStreetMap để xem chỉ đường bên ngoài. Bản đồ trong trang chưa vẽ tuyến đường.
5. **Chọn làm điểm đến** chỉ điền nội dung vào chat; kiểm tra rồi tự gửi. Đây không phải thao tác đặt lịch.
6. Thử **Dừng chia sẻ**, **Đổi lại vị trí** hoặc **Bỏ qua** để kiểm tra các lựa chọn riêng tư. Reload trang không tự xin lại quyền GPS.

## Chạy kiểm thử

Dừng hai server ở trên bằng `Ctrl+C` trước khi chạy E2E để Playwright tự khởi động backend/frontend trên các cổng `18000` và `13000`.

```bash
npm --prefix frontend ci
cd frontend
npx playwright install chromium firefox
cd ..
npm --prefix frontend run test:e2e
./scripts/verify-gps.sh
```

E2E chạy Chromium và Firefox với GPS giả lập; đây không phải kiểm tra GPS phần cứng. Nếu cổng bận, dừng đúng server thử nghiệm trước rồi chạy lại.

## Giới hạn

Danh mục địa điểm là demo, chưa xác minh trạng thái hoạt động. Raster map có thể không tải được tùy kết nối; GPS thật và quyền Allow/Block trên mọi hệ điều hành chưa được kiểm tra. Link chỉ đường mở dịch vụ ngoài. Không dùng dữ liệu cá nhân thật trong demo, ảnh hoặc log.

Chi tiết cấu hình HTTPS thử nghiệm: [https-test-environment.md](https-test-environment.md). Tổng quan thay đổi và bằng chứng kiểm thử: [gps-feature-report-latest-version.md](gps-feature-report-latest-version.md).
