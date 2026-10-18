# Hướng Dẫn & Checklist Triển Khai Service Points Lên Môi Trường Staging (Railway)

Tài liệu này quy định quy trình chuẩn để deploy và kiểm thử tính năng Tích hợp Điểm dịch vụ / Trạm sạc (GPS Catalog & Bản đồ Vietmap) lên môi trường Staging (Railway / Docker).

---

## 1. Biến Môi Trường Cần Thiết Trên Staging

Cấu hình các biến môi trường sau trên dashboard Railway / Staging environment:

```bash
# ---- Database & Environment ----
APP_ENV=staging
DATABASE_URL=postgresql://staging_user:staging_pass@staging-db:5432/vinfast_serviceflow_staging

# ---- GPS Catalog Mode ----
# 'auto': Ưu tiên đọc từ bảng service_points; nếu bảng rỗng ghi log WARNING và fallback an toàn sang snapshot.
# 'db': Đọc từ bảng service_points trong Database.
GPS_CATALOG_MODE=auto

# ---- Demo Seed Password ----
DEMO_SEED_PASSWORD=your_staging_secure_demo_password

# ---- Frontend Vietmap Configuration ----
# Khóa API để hiển thị raster tile bản đồ Vietmap.
# Không commit key thật vào kho mã nguồn; cấu hình qua biến môi trường.
NEXT_PUBLIC_VIETMAP_API_KEY=your_staging_vietmap_api_key_here

# ---- CORS & Frontend URL ----
CORS_ORIGINS=https://staging.serviceflow.vinfast.vn,http://localhost:3000
```

---

## 2. Thứ Tự Triển Khai Chuẩn Trên Staging (Railway)

Thực hiện tuần tự các bước sau:

### Bước 2.1: Deploy Backend & Khởi Động Server
- Khi ứng dụng backend khởi chạy, hàm `ensure_schema()` trong `lifespan` (`src/main.py`) sẽ tự động kiểm tra và đảm bảo các bảng, cột cần thiết.
- **Lưu ý:** Bảng `service_points` tự sinh khi khởi động nhưng sẽ **RỖNG** (0 bản ghi) cho tới khi hoàn tất lệnh import. Hệ thống sẽ ghi log INFO về số bản ghi và log WARNING rõ ràng:
  `"service_points trống, đang dùng snapshot — chạy import_service_points"`.

### Bước 2.2: Chạy Alembic Upgrade Head
Đảm bảo revision tracking của Alembic đồng bộ với database:
```bash
alembic upgrade head
alembic current
```

### Bước 2.3: Chạy Import Dry-Run
Kiểm tra tính hợp lệ của dữ liệu trước khi nạp vào database:
```bash
python -m src.cli.import_service_points \
  --path data/crawl \
  --dry-run \
  --allow-remote
```
Xác nhận log trả về: `[DRY-RUN] Xác nhận hợp lệ: 25228 bản ghi (18111 hiển thị). Không ghi vào DB.`

### Bước 2.4: Chạy Import Thật
Nạp chính thức dữ liệu vào bảng `service_points`:
```bash
python -m src.cli.import_service_points \
  --path data/crawl \
  --crawled-at "2026-10-15T00:00:00Z" \
  --allow-remote
```
Kiểm tra số lượng bản ghi:
- Tổng số nạp: 25.228 bản ghi (xưởng 2S: 181, showroom: 352, trạm sạc: 24.695).
- Tổng số hiển thị (`is_visible=True`): 18.111 bản ghi (đã ẩn 78 trạm sạc nghi ngờ lệch tọa độ > 50km theo KNN-5).

### Bước 2.5: Kiểm Tra API Endpoint
Kiểm tra endpoint gợi ý điểm dịch vụ theo case:
- `GET /api/v1/customer/cases/{id}/service-points` (yêu cầu token khách hàng hoặc token demo).
- `GET /api/v1/customer/service-points/nearby` (public nearby search).
- Kiểm tra response có `meta.catalog_source = "db"` khi bảng đã có dữ liệu.

### Bước 2.6: Seed Dữ Liệu Demo Cho Staging (Tùy Chọn)
> [!CAUTION]
> **CẢNH BÁO QUAN TRỌNG:** Cờ `--demo --reset --yes` CHỈ được dùng trên môi trường Development và Staging. Tuyệt đối **KHÔNG** chạy lệnh này trên Production hoặc database chứa dữ liệu khách hàng thật.
> Lệnh reset chỉ xóa các bản ghi có `is_demo=True` và **KHÔNG** xóa bảng `service_points` hay dữ liệu `is_demo=False`.

```bash
python -m src.seed --demo --reset --yes --allow-remote
```

---

## 3. Checklist Sau Triển Khai
- [ ] Backend khởi động không có lỗi schema/driver (`psycopg`).
- [ ] Endpoint `/api/v1/customer/service-points/nearby` phản hồi 200 kèm `meta.catalog_source = "db"`.
- [ ] Endpoint `/api/v1/customer/cases/{id}/service-points` trả về xưởng gần nhất và hotline cứu hộ `1900-232389` đối với ca nặng.
- [ ] Giao diện Frontend hiển thị đúng các xưởng dịch vụ kèm hotline và nhãn khoảng cách ("Cách Quý khách...").
