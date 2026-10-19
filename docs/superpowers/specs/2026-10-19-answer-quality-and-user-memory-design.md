# Thiết kế đề xuất: chất lượng trả lời, dữ liệu và memory xuyên phiên

Trạng thái: bản đề xuất để review; chưa triển khai thay đổi runtime/schema.
Mốc audit: P-142 `99119c7`, viet-ai `e6882bb`, backend tương đương.
Nguồn: `docs/testing/answer-gaps-and-cross-session-memory-2026-10-19.md`.

## Mục tiêu và phạm vi

Khách hỏi đúng ý, nhận câu trả lời đúng ngôn ngữ, có bằng chứng phù hợp và biết
rõ ý nào chưa được trả lời. Trong cùng phiên, đính chính thông tin phải cập nhật
đúng hồ sơ và phản hồi. Giữa nhiều phiên, thông tin người dùng chủ động cho phép
ghi nhớ được đọc lại, sửa và xóa đúng chủ sở hữu.

Tách thành ba phần có thể nghiệm thu riêng:

1. Xử lý câu trả lời và đo chất lượng: routing, bằng chứng, budget, partial.
2. Dữ liệu: thu thập/xác minh các ô thực sự thiếu, xây index ứng viên.
3. Memory theo người dùng: fact có cấu trúc trong app DB; memory theo phiên giữ
   vai trò quản lý hội thoại hiện tại.

Ưu tiên 1 trước khi phát hành 3, vì thêm memory vào truy vấn hiện tại có thể làm
nặng lỗi kế thừa model và budget. Việc thu thập nguồn ở phần 2 có thể làm song song.

## Phương án

| Phương án | Lợi ích | Giới hạn |
| --- | --- | --- |
| Fact có cấu trúc trong SQL + session memory hiện có — đề xuất | Dễ xác định chủ sở hữu, nguồn, giá trị mới nhất; sửa/xóa theo key; dùng hạ tầng hiện có | Cần khai báo loại fact; giai đoạn đầu tập trung xe chính và thành phố |
| Tìm kiếm ngữ nghĩa toàn bộ lịch sử nhiều phiên | Có thể tìm thông tin tự do | Phải xử lý chống nhớ nhầm, xóa dữ liệu trong index, cảnh báo cũ và nguồn sai; chưa cần cho các lỗi hiện tại |
| Chỉ dùng `User.vehicle_model` | Ít thay đổi | Không đủ phiên bản, thành phố, provenance, sửa/xóa và điều khiển việc ghi nhớ |

## A. Hợp đồng chất lượng câu trả lời

- Phân biệt `answered`, `partial`, `needs_clarification`, `needs_data`,
  `refused`, `external_action_required`, `error` trong diagnostics nội bộ.
  Giữ tương thích enum `response_type` công khai hiện có.
- Một câu nhiều ý: mỗi ý có trạng thái và nguồn riêng. Chỉ `answered` nếu tất
  cả ý hợp lệ đã được đáp ứng; có ý trả lời và ý thiếu nguồn là `partial`.
- Phân rã theo ý thực sự được hỏi: “đặt lịch bảo dưỡng qua app” không tự thành
  yêu cầu giới thiệu các tính năng sạc của app chỉ vì có chữ ứng dụng.
- Giữ tiêu đề, chủ thể, điều kiện và con số trong cùng đơn vị bằng chứng.
  Không nối số của phiên bản/bộ phận này với điều kiện của phiên bản/bộ phận khác.
- Claim ngoài nguồn, sai phủ định, sai phạm vi model/năm, mất điều kiện vẫn phải
  bị từ chối. Sửa false rejection không nới lỏng toàn bộ validator.
- Truy vấn chung về app/sạc/bảo hành không tự bị ép theo chiếc xe vừa tư vấn.
  Câu có “xe tôi”, tham chiếu thật sự hoặc model nêu rõ mới dùng phạm vi liên quan.
- Cấu hình chưa rõ: hỏi Eco/Plus/đời xe thay vì báo thiếu toàn bộ tài liệu.
- Correct/supply_info/retraction trong sự cố: cập nhật/xác nhận và bước tiếp theo;
  không tìm cẩm nang cho chính câu sửa mã trụ hoặc phủ định mã lỗi.
- “Mẫu xe” và “màu xe”, “bao gồm” và “báo lỗi” được phân biệt trước khi bỏ dấu.
  VI/EN theo câu nhập; UI locale chỉ hỗ trợ câu trung tính.
- Prompt giữ bằng chứng tối thiểu cần thiết trước lịch sử ít liên quan, trong
  ngân sách cấu hình hiện có. Không cắt rời điều kiện chính sách để vừa budget.
- Không xác nhận đã đặt/hủy lịch hoặc gửi cứu hộ nếu thiếu biên nhận hành động.

## B. Hợp đồng dữ liệu

Giữ nguồn chính thức, model/phiên bản/đời xe, hạng mục, điều kiện, tiêu chuẩn đo,
ngày xác minh và evidence span/section. `unknown` được thể hiện đúng nghĩa;
không thay bằng số suy diễn hoặc tự gia hạn ngày xác minh.

Thứ tự bổ sung:

1. Bảng bảo dưỡng km/tháng theo mẫu/đời xe, hạng mục và điều kiện sử dụng.
   Kiểm tra bảng/ảnh trong PDF để phân biệt thiếu nguồn với thiếu trích xuất.
2. Màu ngoại thất/nội thất ngoài VF8; tách thông tin mẫu xe với phiên bản/tồn kho.
3. Dung lượng VF3/VF5, e34 và phạm vi năm/cấu hình; điều kiện SOC/công suất sạc.
4. Hướng dẫn app cập nhật; nguồn giá/khả dụng dịch vụ theo địa bàn nếu được tiếp cận.

Tài liệu đã có nhưng xử lý sai như bảo hành được sửa pipeline trước. Mỗi ô dữ
liệu chưa lấy/xác minh được giữ trạng thái thiếu, kèm nguồn cần tìm và blocker.
Index ứng viên nằm riêng; active index chỉ đổi sau gate và có đường quay lại.

## C. Hợp đồng memory xuyên phiên

### Fact giai đoạn đầu

Sáu key: `owned_vehicle.model`, `owned_vehicle.version`,
`owned_vehicle.model_year`, `owned_vehicle.battery_plan`, `home_city`,
`registration_city`. Một xe chính; khi nhiều xe không xác định được xe muốn
lưu, hỏi xác nhận. Nơi đang đứng/GPS không tự trở thành địa chỉ sinh sống.

- Khởi tạo từ “hãy nhớ”/“remember” hoặc xác nhận lưu rõ ràng. Profile được nhập
  bởi người dùng là một nguồn riêng. Tư vấn VF8 không có nghĩa sở hữu VF8.
- Sửa fact đã được đồng ý ghi nhớ khi câu đính chính chỉ rõ thông tin sở hữu/
  thông tin đang lưu. Câu mơ hồ hoặc mục đích khác cần xác nhận.
- Chỉ nội dung người dùng hiện tại được dùng làm nguồn ghi; không tự ghi từ
  câu trả lời model, nguồn RAG, ảnh/tài liệu đính kèm hay instruction trong đó.
- Đổi model xóa phiên bản/năm/phương án pin cũ nếu không có giá trị mới được
  xác nhận. `home_city` và `registration_city` không ghi đè lẫn nhau.
- Thứ tự dùng trong câu trả lời: thông tin khách nêu ở lượt hiện tại, ngữ cảnh
  đúng phạm vi của phiên, fact người dùng đã xác nhận, profile tương thích.
  Memory không tự đặt `active_goal` hoặc subject cho mọi câu hỏi chung.
- Recall trả “Quý khách từng cho biết…” và các fact có nguồn. Không tự gọi xe
  sở hữu là xe đang gặp sự cố; không tự coi thành phố đã lưu là GPS hiện tại.
- Người dùng chưa đăng nhập giữ memory phiên hiện có; không tạo memory xuyên
  phiên bằng guest ID hoặc nhận owner ID từ nội dung chat.

### Lưu trữ và giao dịch

Đề xuất thêm `users.memory_revision` mặc định 0 và bảng `user_memory_facts`:
khóa `(user_id, key)`, `value` nullable, `status` confirmed/unknown/retracted,
`source_kind` chat/profile, `source_session_id`, `source_message_id`, `updated_at`.
Không lưu bản sao raw transcript trong bảng fact.

Snapshot có revision. Ghi/xóa dùng compare-and-swap theo revision trong cùng
transaction với lượt chat đã chấp nhận. Request cũ không được ghi lại dữ liệu
sau thao tác quên ở phiên khác. Conflict không phát ra câu “đã ghi nhớ”; khách
được báo chưa lưu thay đổi và có thể gửi lại. Request ID trùng không tạo ghi lặp.

`User.vehicle_model` là projection tương thích của model đã xác nhận; cập nhật
profile, ghi nhớ và quên model phải đồng bộ, tránh profile cũ lấn fact mới.
Không backfill từ toàn bộ chat cũ. Legacy profile được đọc đúng nguồn; thao tác
nhập/sửa profile mới đi qua cùng logic revision/invalidation.

### Xem, quên, xóa

- `GET /api/v1/customer/memory`: fact của principal hiện tại, trạng thái, nguồn
  và revision. Không nhận tham số owner tùy ý.
- `DELETE /api/v1/customer/memory/{key}`: xóa value và vô hiệu các key phụ thuộc;
  quên model cũng xóa projection `User.vehicle_model`.
- `DELETE /api/v1/customer/memory`: xóa value của sáu key, tăng revision, xóa
  projection model; không được khôi phục từ snapshot/cache cũ.
- Câu “quên…” dùng cùng service với API xóa. Không gọi quên thành công trước commit.
- Xóa một phiên: vô hiệu/xóa value của fact chat có nguồn từ phiên đó. Xóa toàn
  bộ lịch sử: xử lý mọi fact nguồn chat; profile nhập riêng vẫn có thể được quản
  lý qua profile hoặc xóa memory. Hồ sơ sự cố thuộc domain riêng, không bị xóa
  gián tiếp bởi lệnh quên sở thích.
- Kiểm tra sở hữu tại service và API; không lộ fact qua cache, trace hoặc lỗi.

## Nghiệm thu và phát hành

1. Toàn bộ ca lỗi xác định trong audit được gắn expectation: trả đúng đủ khi có
   nguồn, hỏi lại khi thiếu cấu hình, partial khi thiếu một ý, hoặc needs_data
   đúng lý do. Không coi HTTP 200/pytest đo lường PASS là chất lượng đạt.
2. 27 phiên 10/20/30 lượt, 540 lượt và 36 replay vẫn đạt; bổ sung assertion nội
   dung bên cạnh state. Mỗi câu nhiều ý đối chiếu riêng từng ý và citations.
3. 11 khả năng memory trong audit phải đạt sau khi triển khai đúng feature;
   bổ sung quên/xóa, concurrent update, rollback và guest/cross-user controls.
4. Holdout đề xuất 40 câu mới, 20 VI/20 EN: 30 câu đủ nguồn và 10 câu thiếu
   nguồn/ngoài phạm vi/ranh giới. Người review khác xác nhận nhãn và evidence
   trước khi freeze. Mục tiêu ít nhất 29/30 câu đủ nguồn đúng đủ; 10/10 câu
   ranh giới xử lý đúng. Không có claim nguy hiểm hoặc xác nhận hành động sai.
5. Full backend/frontend xanh; 7 lỗi observability cũ được đóng riêng, không
   cộng vào thành công của bộ business. Provider bị lỗi/rate-limit được ghi
   BLOCKED và đo lại, không tính thành answer PASS.
6. Migration thử SQLite và PostgreSQL riêng. Production DDL chạy trước app;
   feature flag `user_memory_enabled` mặc định false. Rollback app/flag giữ
   schema bổ sung; không drop bảng production để quay lui.
7. Chỉ tích hợp theo phạm vi được chấp thuận: P-142 `feature/agent-long` và
   viet-ai `test/agent-long`. Triển khai môi trường chạy thật là bước riêng.
