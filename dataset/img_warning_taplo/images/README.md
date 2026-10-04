# Thư Mục Quản Lý Ảnh Cảnh Báo Táp-lô (Dashboard Images Directory)

## 1. Nguyên Tắc Quản Lý Ảnh và Bảo Mật (Privacy & PII Policy)

Tuân thủ nghiêm ngặt quy định bảo mật tại mục 4 & 6 trong tài liệu kế hoạch `docs/plans/2026-10-04-dashboard-warning-vision.md`:

1. **Bảo mật dữ liệu cá nhân (PII):**
   - Mọi ảnh từ khách hàng gửi vào hệ thống chatbot PHẢI được tự động hoặc thủ công che mờ/loại bỏ:
     - Số khung xe (VIN).
     - Biển số xe.
     - Khuôn mặt người ngồi trên xe hoặc hình ảnh phản chiếu trên kính lái/màn hình.
     - Vị trí định vị GPS/tên đường hiển thị trên bản đồ (nếu có).
2. **Quyền sở hữu và bản quyền:**
   - Các ảnh tham chiếu từ cổng website VinFast (`static-cms-prod.vinfastauto.com`) được lập danh mục trong file `image_catalog.json` dưới dạng liên kết nguồn (source link).
   - Không commit các file ảnh nặng hoặc ảnh có bản quyền chưa được cấp phép trực tiếp vào kho lưu trữ git công khai.
3. **Ảnh phục vụ kiểm thử (Benchmark Dataset):**
   - Bộ ảnh benchmark thực tế sẽ được lưu trữ tại storage riêng biệt có phân quyền (private object storage) và liên kết qua ID ẩn danh.

## 2. Danh Mục Tệp
- `image_catalog.json`: Danh mục các ảnh tham chiếu chính thức từ VinFast, bao gồm ID, liên kết URL, loại ảnh và các triệu chứng cảnh báo liên quan.
