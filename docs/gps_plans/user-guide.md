# Thử GPS theo câu hỏi trong chat

Dành cho Customer đăng nhập. Địa điểm lấy từ snapshot CSV chưa xác minh hoạt động hiện tại; không có booking/điều phối thật.

## Chạy bản thử

Dừng server thử cũ bằng `Ctrl+C` để giải phóng cổng `18000/13000`. Mở hai terminal tại root repository, chạy `clear` hoặc `Ctrl+L`, rồi:

```bash
# Terminal 1 — backend, database tạm
python3 scripts/gps-e2e-server.py backend

# Terminal 2 — frontend production
python3 scripts/gps-e2e-server.py frontend
```

Mở `http://127.0.0.1:13000/register`, tạo tài khoản bằng thông tin giả và vào `/chat`. Database bị xóa khi dừng backend. Demo này tắt LLM online.

## Tìm và chỉ đường

1. Chat **“Tìm trạm sạc gần đây”** hoặc **“Tìm showroom gần tôi”**. Login/FAQ không tự hỏi GPS.
2. Popup giải thích lý do: chọn **Dùng vị trí hiện tại** rồi Allow, hoặc **Nhập khu vực**. Có thể **Bỏ qua**; nếu Block/timeout thì nhập tay.
3. Có vị trí thì tự hiện tối đa **5 kết quả**, đúng loại xe. Chạm **Chỉ đường Google Maps** ngay ở địa điểm muốn đến; không cần gửi thêm câu chat.
4. Có thể hỏi tiếp **“còn showroom thì sao”**. Vị trí đã chọn được dùng lại trong phiên tối đa 15 phút, không xin lại ở mỗi lượt.
5. **“Showroom ở Huế”** dùng điểm tham chiếu khu vực, không hỏi GPS. Địa chỉ chưa nhận diện không được gán khoảng cách giả.
6. **Xem bản đồ** mở map gọn; **Đổi vị trí/Dừng chia sẻ** thay hoặc xóa vị trí trong phiên. Reload không tự mở popup. GPS tra cứu không tự gửi vào case; **Chia sẻ vị trí với hồ sơ** là lựa chọn riêng khi có hồ sơ.

Nói rõ **xe máy** nếu tìm địa điểm cho xe máy; mặc định là ô tô. Xưởng chưa có mapping từ hai CSV; tủ đổi pin chưa đủ dữ liệu tương thích để gợi ý.

Khoảng cách là **đường chim bay**, không phải quãng đường lái xe/ETA. Google Maps nhận tọa độ khi bạn nhấn chỉ đường. Không đảm bảo trạm đang mở hoặc có cổng trống.

## Kiểm thử

Dừng đúng server thử trước khi chạy E2E để runner tự khởi động server riêng:

```bash
./scripts/verify-gps.sh
GPS_E2E_BACKEND_PORT=18020 GPS_E2E_FRONTEND_PORT=13020 npm --prefix frontend run test:e2e
```

Cần dependencies và Playwright Chromium/Firefox đã cài. E2E dùng GPS giả lập, không chứng minh GPS phần cứng hoặc khả năng tải raster map trên mọi mạng.

Chi tiết: [báo cáo cập nhật](update_gps_Oct_15.md), [EDA](gps-data-eda-2026-10-15.md), [HTTPS thử nghiệm](https-test-environment.md).
