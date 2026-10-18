# GPS runtime snapshot

`service_points.snapshot.csv.gz` là bản nén xác định (`mtime=0`) của CSV staging đã chuẩn hóa: 68.637 bản ghi, không mang CRM/Salesforce, hotline, URL hoặc object nhúng. `service_points.snapshot.metadata.json` giữ SHA-256 nguồn và nội dung chuẩn hóa, ngày nhập 15/10/2026; ngày cập nhật/export nguồn chưa biết. Mọi địa điểm là UNVERIFIED, không phải dữ liệu sẵn sàng phục vụ trực tiếp.

Runtime mặc định dùng snapshot này. Loader kiểm tra checksum, validate schema và chỉ giữ ứng viên có tọa độ/loại xe/trạng thái phù hợp; cache theo file/revision. Gói runtime nằm trong `fixtures/` để được mang theo repository/Docker, không phụ thuộc thư mục `data/` đang bị ignore hoặc đường dẫn máy người cung cấp CSV.

Tái tạo từ root:

```bash
python3 scripts/eda_gps_catalog.py --input-dir /home/palm/Desktop/vin_ai20k/data_gps --output-dir data/gps --runtime-dir fixtures/gps
```

Nên kiểm tra EDA/checksum/count trước khi thay snapshot. `GPS_CATALOG_MODE=demo` chuyển rõ ràng sang fixture demo để regression/rollback; không tự trộn hai nguồn hoặc fallback âm thầm khi snapshot lỗi. Mode không hợp lệ hoặc lỗi file trả 503 từ nearby API.

Trạm sạc chỉ lấy ACTIVE, Public, được publish; showroom không suy ra đang mở cửa. Tủ đổi pin giữ lại trong snapshot để truy vết nhưng chưa đưa vào tìm kiếm vì thiếu loại xe/trạng thái. Chưa có mapping đủ tin cậy để tạo xưởng từ mã showroom. Không gộp chỉ vì cùng tên/địa chỉ/tọa độ.

Báo cáo: [update_gps_Oct_15.md](../../docs/gps_plans/update_gps_Oct_15.md).
