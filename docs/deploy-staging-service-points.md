# Hướng Dẫn & Quy Trình Nạp Dữ Liệu Service Points Lên Môi Trường Staging (Railway)

Tài liệu này quy định quy trình chuẩn để deploy và nạp dữ liệu Điểm dịch vụ / Trạm sạc (Service Points) lên môi trường Staging (Railway / Docker PostgreSQL).

> [!IMPORTANT]
> **Đặc điểm dữ liệu và môi trường:**
> - Thư mục dữ liệu nguồn `data/crawl/` nằm trên máy local của lập trình viên và nằm trong `.gitignore` (môi trường Railway Staging không có thư mục này).
> - Quá trình import dữ liệu lên DB Staging được thực hiện trực tiếp từ máy local kết nối tới DATABASE_URL public của DB STAGING (tuyệt đối không chạy trên Production).
> - Để đảm bảo an toàn, công cụ CLI yêu cầu kiểm tra `--dry-run` trước, sau đó chạy lệnh chính thức kèm `--allow-remote` và `--crawled-at`.

---

## 1. Biến Môi Trường Cần Thiết Trên Staging

Cấu hình các biến môi trường sau trên dashboard Railway / Staging environment:

```bash
# ---- Database & Environment ----
APP_ENV=staging
DATABASE_URL=postgresql://staging_user:staging_pass@staging-db.railway.internal:5432/railway

# ---- GPS Catalog Mode ----
# 'auto': Ưu tiên đọc từ bảng service_points trong Database; nếu bảng rỗng ghi log WARNING.
# 'db': Bắt buộc đọc từ bảng service_points trong Database.
GPS_CATALOG_MODE=auto

# ---- Demo Seed Password ----
DEMO_SEED_PASSWORD=your_staging_secure_demo_password

# ---- Frontend Vietmap Configuration ----
# Khóa API để hiển thị raster tile bản đồ Vietmap (không commit key thật vào kho mã nguồn).
NEXT_PUBLIC_VIETMAP_API_KEY=your_staging_vietmap_api_key_here

# ---- CORS & Frontend URL ----
CORS_ORIGINS=https://staging.serviceflow.vinfast.vn,http://localhost:3000
```

---

## 2. Quy Trình Nạp Dữ Liệu Service Points Từ Máy Local Lên Staging

Thực hiện tuần tự các bước sau từ terminal máy local (nơi có thư mục `data/crawl`):

### Bước 2.1: Chạy Alembic Upgrade Head Trên DB Staging
Đồng bộ schema bảng `service_points` và các trường liên quan trên DB Staging:
```bash
DATABASE_URL="postgresql://staging_user:staging_pass@autorack.proxy.rlwy.net:12345/railway" alembic upgrade head
```

### Bước 2.2: Chạy Import Dry-Run Từ Máy Local
Kiểm tra tính hợp lệ của dữ liệu trước khi nạp:
```bash
python -m src.cli.import_service_points \
  --path data/crawl \
  --db-url "postgresql://staging_user:staging_pass@autorack.proxy.rlwy.net:12345/railway" \
  --dry-run
```
> [!NOTE]
> Lệnh dry-run cho phép kiểm tra cấu trúc dữ liệu mà không ghi bản ghi nào vào DB.

### Bước 2.3: Chạy Import Chính Thức Với Cờ `--allow-remote` Và `--crawled-at`
Nạp chính thức dữ liệu vào bảng `service_points` của Staging:
```bash
python -m src.cli.import_service_points \
  --path data/crawl \
  --db-url "postgresql://staging_user:staging_pass@autorack.proxy.rlwy.net:12345/railway" \
  --crawled-at "2026-10-15T00:00:00Z" \
  --allow-remote
```
Xác nhận số lượng bản ghi:
- Tổng số nạp: 25.228 bản ghi (xưởng 2S: 181, showroom: 352, trạm sạc: 24.695).
- Tổng số hiển thị (`is_visible=True`): 18.189 bản ghi (ẩn các trạm sạc nghi ngờ lệch tọa độ).

### Bước 2.4: Kiểm Tra Sau Import & Xác Nhận `meta.catalog_source = "db"`
Kiểm tra endpoint gợi ý điểm dịch vụ và nearby:
- `GET https://staging.serviceflow.vinfast.vn/api/v1/customer/service-points/nearby?lat=21.0285&lng=105.8542`
- Xác nhận trong JSON response có:
  ```json
  "meta": {
    "catalog_source": "db"
  }
  ```
- Kiểm tra số lượng bản ghi trong database:
  ```sql
  SELECT count(*), count(*) FILTER (WHERE is_visible) FROM service_points;
  ```

---

## 3. Checklist Sau Triển Khai
- [ ] Backend khởi động không có lỗi schema/driver (`psycopg`).
- [ ] Dữ liệu `data/crawl/` đã được nạp thành công từ local lên DB Staging.
- [ ] Endpoint `/api/v1/customer/service-points/nearby` phản hồi 200 kèm `meta.catalog_source = "db"`.
- [ ] Endpoint `/api/v1/customer/cases/{id}/service-points` trả về xưởng gần nhất và hotline cứu hộ `1900-232389` đối với ca nặng.
- [ ] Giao diện Frontend hiển thị đúng các xưởng dịch vụ kèm hotline và nhãn khoảng cách.
