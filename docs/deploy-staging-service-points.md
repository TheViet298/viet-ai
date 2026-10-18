# Hướng Dẫn & Checklist Triển Khai Service Points Lên Môi Trường Staging

Tài liệu này quy định quy trình chuẩn để deploy và kiểm thử tính năng Tích hợp Điểm dịch vụ / Trạm sạc (GPS Catalog & Bản đồ Vietmap) lên môi trường Staging.

---

## 1. Biến Môi Trường Cần Thiết Trên Staging

Trước khi tiến hành deploy, cấu hình các biến môi trường sau trong file cấu hình staging (`.env.staging`):

```bash
# ---- Database & Environment ----
APP_ENV=staging
DATABASE_URL=postgresql://staging_user:staging_pass@staging-db:5432/vinfast_serviceflow_staging

# ---- GPS Catalog Mode ----
# 'auto': Ưu tiên đọc từ bảng service_points; nếu bảng rỗng sẽ fallback an toàn sang snapshot.
# 'db': Bắt buộc đọc từ bảng service_points trong Database (khuyến nghị trên Staging).
GPS_CATALOG_MODE=auto

# ---- Frontend Vietmap Configuration ----
# Khóa API để hiển thị raster tile bản đồ Vietmap.
# Nếu để trống hoặc khóa không hợp lệ: Mini map tự động ẩn, card danh sách vẫn hoạt động bình thường.
NEXT_PUBLIC_VIETMAP_API_KEY=your_staging_vietmap_api_key_here

# ---- CORS & Frontend URL ----
CORS_ORIGINS=https://staging.serviceflow.vinfast.vn,http://localhost:3000
```

---

## 2. Thứ Tự Chạy Migration & Import Dữ Liệu

Thực hiện tuần tự các bước sau từ thư mục gốc của repository:

### Bước 2.1: Chạy Alembic Migration
Đảm bảo cấu trúc bảng `service_points` và các trường bổ sung của `case_locations` được cập nhật đầy đủ:
```bash
# Kiểm tra migration hiện tại
alembic current

# Nâng cấp database lên phiên bản mới nhất
alembic upgrade head
```

### Bước 2.2: Import Dữ Liệu Crawler Kèm Bộ Lọc Tọa Độ Lệch
Chạy lệnh import dữ liệu trạm sạc và xưởng dịch vụ với cờ `--suspect-hide` (mặc định bật):
```bash
python -m src.cli.import_service_points \
  --input data/crawl/service_points_latest.json \
  --suspect-hide
```
*Lưu ý:*
- Thuật toán KNN-5 consensus sẽ tự động phát hiện các trạm có tọa độ lệch > 50 km so với đa số điểm cùng tỉnh/thành.
- Các bản ghi nghi ngờ sẽ được gắn cờ `is_suspect_coordinate = True` và ẩn khỏi kết quả tìm kiếm (`is_active = False`).

### Bước 2.3: (Tùy chọn) Nạp Dữ Liệu Demo Trên Staging
Nếu cần thiết lập các kịch bản demo cho kiểm thử viên:
```bash
python -m src.seed --reset --yes
```

---

## 3. Quy Tắc Cô Lập Môi Trường (Isolating Staging from Production)

1. **Tuyệt đối không trỏ `DATABASE_URL` vào cơ sở dữ liệu Production:**
   - Môi trường Staging bắt buộc phải sử dụng database riêng (`vinfast_serviceflow_staging`).
2. **Không tự động seed dữ liệu:**
   - Script `src/seed.py` chỉ chạy khi được gọi tường minh bằng lệnh CLI và bị chặn hoàn toàn nếu `APP_ENV=production`.
3. **Bảo mật API Key:**
   - Khóa `NEXT_PUBLIC_VIETMAP_API_KEY` chỉ được nạp qua biến môi trường của hệ thống CI/CD hoặc `.env.local` của máy chủ Staging; không bao giờ commit vào Git.

---

## 4. Checklist Kiểm Thử Thủ Công (Manual QA Checklist)

Sau khi deploy lên Staging, kiểm thử viên (QA) thực hiện xác minh 5 kịch bản sau:

| STT | Kịch Bản Kiểm Thử | Các Bước Thực Hiện | Kết Quả Mong Đợi |
|:---:|:---|:---|:---|
| **1** | **Fallback Area Reference (Quận Ninh Kiều, Cần Thơ)** | 1. Mở case `CASE-20260924-003` trên `/track-case` hoặc chat chọn vị trí Ninh Kiều.<br>2. Xem danh sách điểm hỗ trợ. | - Không crash khi không có tọa độ GPS.<br>- Card hiển thị: `Khoảng N km từ Cần Thơ (đường chim bay, không phải khoảng cách từ vị trí của bạn)`.<br>- Khoảng cách được làm tròn bội số 5 km (ví dụ: `dưới 5 km` hoặc `khoảng 10 km`). |
| **2** | **Sự Cố Nặng Trên Cao Tốc (VF9 mất nguồn)** | 1. Mở case `CASE-20260924-002` (Priority: CRITICAL).<br>2. Quan sát thứ tự hiển thị của cột phải. | - **Banner Cứu hộ đỏ xuất hiện TRƯỚC mọi card** (trước Card thông tin xe và Card điểm hỗ trợ).<br>- Hotline `1900-232389` là link `tel:` bấm gọi trực tiếp được. |
| **3** | **Xưởng Dịch Vụ 2S Đầy Đủ Thông Tin** | 1. Mở case `CASE-20260924-005` (có GPS gần xưởng Dương Nội) hoặc tìm xưởng 2S trên `/chat`. | - Card xưởng hiển thị giờ mở cửa (VD: `08:00 - 21:00`).<br>- Hotline dịch vụ hiển thị link `tel:` gọi được.<br>- Có badge `Đồng sơn`.<br>- Có nút `Đặt lịch dịch vụ` mở link VinFast Auto. |
| **4** | **Vùng Thưa Điểm Dịch Vụ (> 150 km)** | 1. Chọn vị trí ở vùng hải đảo/biên giới xa điểm dịch vụ (hoặc test với tọa độ đặc biệt). | - Trả về cờ `no_points_nearby: true`.<br>- Ẩn nút "Chia sẻ lại vị trí".<br>- Hiển thị thông báo hướng dẫn gọi hotline tổng đài 1900-232389. |
| **5** | **Khả Năng Chống Chịu Khi Thiếu Vietmap API Key** | 1. Xóa hoặc làm sai `NEXT_PUBLIC_VIETMAP_API_KEY` trên staging.<br>2. Tải lại trang `/track-case` và `/chat`. | - Mini map tự động ẩn nhẹ nhàng, không gây lỗi console nghiêm trọng.<br>- Toàn bộ danh sách card điểm dịch vụ vẫn hiển thị và tương tác 100% bình thường. |

---

## 5. Kế Hoạch Rollback Khi Có Sự Cố

Nếu phát hiện sự cố nghiêm trọng trên Staging (lỗi schema, crash ứng dụng, dữ liệu sai lệch):

### Rollback Database Schema
```bash
# Quay lại revision migration trước đó
alembic downgrade -1
```

### Rollback Dữ Liệu Import Bị Lỗi
Nếu cần vô hiệu hóa toàn bộ dữ liệu vừa import mà không xóa bảng:
```sql
-- Chuyển trạng thái hoạt động về 0 cho các điểm được import trong ngày
UPDATE service_points
SET is_active = 0
WHERE updated_at >= CURRENT_DATE;
```

### Rollback Frontend & Backend Application
- CI/CD tự động deploy lại container image của commit trước đó (`HEAD~1`).
- Đặt `GPS_CATALOG_MODE=demo` tạm thời trong `.env` nếu cần cô lập hoàn toàn truy vấn cơ sở dữ liệu và phục vụ snapshot cố định trong thời gian điều tra lỗi.
