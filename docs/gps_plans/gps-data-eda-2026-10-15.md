# EDA dữ liệu GPS — 15/10/2026

## Nguồn và kết quả xử lý

Đã đọc trọn hai CSV người dùng cung cấp tại `/home/palm/Desktop/vin_ai20k/data_gps` bằng `csv.DictReader`, encoding UTF-8 BOM. Mỗi file có 37 cột; không phát hiện bản ghi lệch cấu trúc, dòng trùng toàn bộ hoặc thiếu tên/địa chỉ/ID/tọa độ dạng chuỗi. Tọa độ có giá trị không đồng nghĩa tọa độ hợp lệ.

| Nguồn | Bản ghi | Nhóm dữ liệu |
| --- | ---: | --- |
| `vinfast_showrooms.csv` | 1.138 | 352 showroom ô tô; 786 showroom xe máy điện |
| `vinfast_tramsac.csv` | 67.499 | 24.695 trạm sạc ô tô; 540 trạm sạc xe máy; 42.264 tủ đổi pin |
| Tổng | **68.637** | 5 nhóm nguồn |

SHA-256 từng CSV được ghi trong [eda-summary.json](../../data/gps/eda-summary.json). Chưa có ngày export, ngày kiểm chứng, tài liệu thu thập hoặc bằng chứng cập nhật trực tiếp. Không gắn nhãn “danh mục chính thức đã xác minh” chỉ từ tên file và link nguồn trong dữ liệu.

## Chất lượng tọa độ và định danh

| Kiểm tra | Showroom | Trạm sạc/tủ đổi pin |
| --- | ---: | ---: |
| Tọa độ không phải số hữu hạn hoặc ngoài phạm vi thế giới | 1 | 0 |
| Ngoài bounding box sàng lọc 8–24°N, 102–110°E | 0 | 5 |
| ID/code/store_id trùng trong từng nguồn | 0 | 0 |
| Số bản ghi tên lặp dư sau lần đầu | 22 | 6.848 |
| Số bản ghi địa chỉ lặp dư sau lần đầu | 8 | 8.231 |

Sáu bản ghi bị cách ly khỏi bộ ứng viên mặc định:

| File | `source_row` | Vấn đề |
| --- | ---: | --- |
| showroom | 1120 | Không chuyển đổi được tọa độ hợp lệ |
| tramsac | 536, 537 | `(lat,lng)=(1,1)` |
| tramsac | 24673 | `(10.018075,10.573833)` |
| tramsac | 24813 | `(11.548326,10.778867)` |
| tramsac | 24949 | `(21.628088,21.628088)` |

Không tự hoán đổi hoặc sửa tọa độ. Bounding box là heuristic, không chứng minh điểm nằm trong biên giới Việt Nam. Cần xác nhận lại nguồn đối với các điểm đáng ngờ.

Trên toàn bộ dữ liệu có **4.511 nhóm dùng chung tọa độ**, tương ứng **5.276 bản ghi dư** nếu chỉ đếm theo tọa độ. Đây không phải bằng chứng bản ghi trùng: cùng nơi có thể có showroom, trạm sạc hoặc nhiều dịch vụ. Không deduplicate chỉ theo tên, địa chỉ hay tọa độ. ID staging là `bundle:entity_id`, không trùng trên 68.637 bản ghi.

## Trạng thái và khả năng sử dụng

| Trạng thái nguồn | Trạm sạc ô tô | Trạm sạc xe máy |
| --- | ---: | ---: |
| ACTIVE | 16.679 | 327 |
| INACTIVE | 3.979 | 158 |
| UNAVAILABLE | 2.987 | 49 |
| BUSY | 997 | 6 |
| OUTOFSERVICE | 53 | 0 |
| Tổng | 24.695 | 540 |

- **8.229** trạm sạc không có trạng thái ACTIVE. Không gợi ý như thể đang sẵn sàng sạc.
- **24** bản ghi `charging_publish=False`, **24** bản ghi `access_type=Restricted`. Các nhóm cờ có thể giao nhau; không cộng số cờ để suy ra số điểm duy nhất.
- **42.264 tủ đổi pin** thiếu cả charging_status, charging_publish và access_type. Không chuyển thiếu thành ACTIVE hoặc mặc định tương thích ô tô.
- `status` của mọi bản ghi là `True` hoặc `1`, nên chỉ lọc trường này sẽ giữ cả trạm INACTIVE/OUTOFSERVICE. Đây là trường bật bản ghi, không phải trạng thái sạc trực tiếp.
- `parking_fee=True` có ở 25.142 trạm sạc; không có mức phí. Không suy ra số tiền hay rằng phí đang áp dụng thực tế.

Bộ lọc ứng viên **đề xuất cho trải nghiệm ô tô**: loại phương tiện CAR, tọa độ vượt kiểm tra, bản ghi bật; riêng trạm sạc phải ACTIVE, không bị ẩn/hạn chế truy cập. Kết quả là **16.657 trạm sạc ô tô + 351 showroom ô tô = 17.008 ứng viên**. Đây là số ứng viên từ snapshot, chưa phải điểm được xác minh đang mở cửa. Chưa áp dụng bộ lọc này vào runtime.

## Thiếu dữ liệu ảnh hưởng sản phẩm

| Trường/nhóm | Thiếu | Hệ quả |
| --- | ---: | --- |
| Showroom: giờ mở/đóng dịch vụ | 45 / 1.138 mỗi cột | Không mặc định 24/7; format giờ cần chuẩn hóa riêng |
| Showroom: giờ mở/đóng bán hàng | 83 / 84 trên 1.138 | Không khẳng định “đang mở cửa” |
| Showroom: district_id | 12 / 1.138 | Không bắt buộc quận/huyện để tìm bằng tọa độ |
| Tramsac: province_id | 4.152 / 67.499 | Không dùng province_id làm điều kiện bắt buộc |
| Tramsac: district_id | 25.235 / 67.499 | Trùng với kích thước nhóm sạc; không tự điền tỉnh/quận |
| Tramsac: bốn cột giờ mở/đóng | 67.499 mỗi cột | Không có bằng chứng về giờ hoạt động |
| Tramsac: charging_avaiable_date | 67.081 / 67.499 | Không dùng làm thời điểm cập nhật chung |

Không có trường chuẩn hóa về công suất kW, loại đầu nối, số cổng trống, hàng đợi, khả năng tương thích từng xe, đường đi hoặc thời gian di chuyển. Không suy ra từ marker icon hoặc để LLM tự bổ sung.

`multiple_type` có các tổ hợp mã `2471/2473`, `2472/2474` ở showroom; chưa có từ điển mã được xác nhận. Vì thế chưa tự tạo nhóm xưởng dịch vụ từ 1.138 showroom. Các địa điểm dịch vụ khác giữ nguồn riêng cho đến khi mapping được xác minh.

## Chuẩn hóa đã thực hiện

Đã tạo [service_points.normalized.csv](../../data/gps/service_points.normalized.csv) giữ đủ 68.637 bản ghi với tên/địa chỉ, lat/lng số, category, vehicle_type, trạng thái gốc, giờ nguồn, provenance và quality_flags. Tủ đổi pin dùng `BATTERY_SWAP`, phương tiện `UNKNOWN`; chưa tương thích schema runtime nên không thể thay file fixture trực tiếp.

Đã tạo [quality_issues.csv](../../data/gps/quality_issues.csv) để truy vết các cờ theo file/bản ghi nguồn và thống kê toàn bộ 37 cột trong JSON. Không mang theo CRM/Salesforce, hotline hoặc URL/object nhúng sang staging. Không xóa/sửa hai CSV gốc; không đổi danh mục demo đang được ứng dụng sử dụng.

## Kết luận cho workflow

1. Intent phải chọn cả **loại địa điểm + loại phương tiện**; tìm “trạm sạc” cho ô tô không được trộn trạm xe máy/tủ đổi pin.
2. Backend lấy top 5 sau lọc, tính Haversine từ tọa độ thật; LLM chỉ diễn giải kết quả có cấu trúc.
3. Ghi “khoảng cách đường chim bay, tham khảo”; chưa có nhãn quãng đường/ETA để huấn luyện mô hình dự đoán. Không nhân hệ số tùy ý để gọi là khoảng cách đường bộ.
4. Snapshot trạng thái phải có nhãn chưa xác minh hiện tại; nút Google Maps là hành động chính. Không hứa trạm đang trống hoặc nhận khách.
5. Với 68k bản ghi, benchmark tải/cache/lọc trước khi thêm spatial index. Tránh parse CSV và tính lại toàn bộ trong mỗi lần token/chat cập nhật.

## Tái lập và kiểm chứng

```bash
python3 scripts/eda_gps_catalog.py --input-dir /home/palm/Desktop/vin_ai20k/data_gps --output-dir data/gps
```

Đã chạy EDA trên toàn bộ hai file. Kết quả được đối chiếu độc lập theo tổng dòng, ID duy nhất, SHA-256 nguồn và bộ lọc ứng viên. Đây là kiểm chứng dữ liệu; chưa kiểm chứng địa điểm trên thực địa hoặc luồng UI mới. Kế hoạch tích hợp ở [contextual-nearby-workflow-plan.md](contextual-nearby-workflow-plan.md).

### Bổ sung sau triển khai

Snapshot chuẩn hóa đã được đóng gói ở `fixtures/gps` và dùng bởi runtime; staging ở `data/gps` không phải đường dẫn deploy. Huế dùng tọa độ một showroom trong nguồn làm **điểm tham chiếu khu vực**, không phải centroid hành chính hoặc GPS khách. Xem [báo cáo triển khai](update_gps_Oct_15.md).
