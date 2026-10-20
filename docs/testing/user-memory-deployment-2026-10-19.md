# Triển khai và quay lui user memory

## Trạng thái

Feature mặc định `USER_MEMORY_ENABLED=false`. SQLite đã kiểm thử bằng DB tổng hợp. PostgreSQL **BLOCKED**: người dùng xác nhận chưa có database riêng; không chạy lên DB thật thay thế. Candidate Chroma độc lập, chưa đổi active index.

## Hotfix đăng nhập database cũ (2026-10-20)

`User.memory_revision` được ORM đọc trong truy vấn đăng nhập ngay cả khi feature tắt. Trước hotfix, `ensure_schema()` tạo bảng memory nhưng không thêm cột này vào bảng `users` có sẵn, nên deployment chưa chạy migration có thể trả HTTP 500 khi đăng nhập. Startup nay bổ sung cột với default 0 và giữ nguyên tài khoản/mật khẩu. Migration `4e01_user_memory` kiểm tra các thành phần đã được startup tạo trước khi bổ sung, để vẫn chạy `alembic upgrade head` theo quy trình dưới đây mà không gặp lỗi trùng cột/bảng. Deployment đã chạy migration không cần chạy lại revision đó.

Regression SQLite kiểm tra startup hai lần trên schema cũ, đăng nhập hai vai trò demo, xác minh JWT và chạy tiếp Alembic; không backfill user memory. PostgreSQL vẫn bị chặn do thiếu `TEST_POSTGRES_URL`. Hai API demo production trước hotfix trả HTTP 500; chưa có log/database production để xác nhận cùng stack trace hoặc xác nhận sau deploy.

## Trình tự triển khai khi các gate đủ

1. Sao lưu database theo quy trình môi trường. Đối chiếu migration head đang chạy.
2. Giữ flag tắt; chạy `alembic upgrade head` (migration `4e01_user_memory` sau `3d01_service_points`) trước khi chạy code mới. ORM mới đọc revision cả khi flag tắt nên không được đảo thứ tự.
3. Chạy smoke đăng nhập/chat/incident với flag tắt. Không backfill transcript thành facts.
4. Trên môi trường thử, bật flag. Hai user khác nhau kiểm tra consent→recall phiên mới→correction→forget→replay, xóa nguồn và quyền API. Chỉ sau PostgreSQL gate đạt mới bật ở môi trường PostgreSQL.
5. Theo dõi lỗi transaction/CAS, latency, nguồn thiếu và các trạng thái partial/needs_data. Telemetry memory chỉ giữ key/revision/status, không lưu value.

## Quay lui

Tắt flag, quay lui ứng dụng nếu cần, giữ schema cộng thêm và dữ liệu SQL để rollback an toàn. Không chạy downgrade trong quy trình production. API quên/xóa nguồn và quyền truy cập phải được đối chiếu khi quay lui phiên bản; không bật lại bản cũ nếu làm dữ liệu bị quên xuất hiện lại từ profile. Candidate index có đường dẫn riêng; quay về giá trị CHROMA_PERSIST_DIR trước đó và restart, không ghi đè index cũ.

## Phạm vi dữ liệu

Sáu key: owned_vehicle.model/version/model_year/battery_plan, home_city, registration_city. Chỉ human text trực tiếp với consent hoặc correction của fact đã consent. Không ghi goal, interest, hồ sơ sự cố, nguy cơ, GPS, SOC, trụ sạc hay booking thành user memory. Quên facts không xóa hồ sơ nghiệp vụ; xóa phiên nguồn sẽ vô hiệu facts nguồn chat và tăng revision fence. Mỗi thay đổi SQL cùng transaction với accepted turn; request lặp không ghi lần hai.
