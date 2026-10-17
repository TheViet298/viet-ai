# ADR-005 — Roles, Location Consent & Customer Confirmation

**Trạng thái:** Accepted  
**Ngày:** 2026-10-02

## Quyết định

* Có 3 role: `Guest`, `Customer`, `Staff`.
* Guest được chat FAQ/tư vấn tối đa 5 lượt/phiên; phải login để tải ảnh và tạo/theo dõi case.
* Customer đăng ký/đăng nhập bằng Username + Password (mật khẩu băm Argon2id, xác thực JWT Bearer Token). Không khẳng định đã xác minh chủ xe VinFast thật qua CRM.
* Staff account seed/invite, không public register; Staff dùng public/chat ở preview mode.
* Vị trí chỉ được lấy khi Customer chọn consent hoặc tự nhập; không đọc GPS từ ảnh/EXIF.
* Map chỉ gợi ý điểm hỗ trợ phù hợp theo intent. P0 dùng 3–5 điểm seed, không điều phối thật.
* Critical tạo Case Brief tối thiểu + cảnh báo/hotline ngay; location là dữ kiện bổ sung, không được chặn case.
* Khi Staff Resolve, Customer nhận update và chọn `Đã được hỗ trợ` (Closed) hoặc `Vẫn chưa giải quyết` (Reopened).
* Customer Support Center cho phép tìm kiếm/xem timeline, Customer Update và chat history của **case thuộc Customer đó**. Tình huống thường gặp là thư viện đã biên soạn/ẩn danh.
* Staff Console là console nghiệp vụ: dashboard, queue, ticket detail, case history, routing directory demo, Knowledge Hub và Customer Preview; không phải Admin system.

## Không thuộc MVP

* Xác minh VinFast CRM/chủ xe thật.
* Browser GPS bắt buộc, map live hay điều cứu hộ/booking thật.
* Tự chia sẻ vị trí nền hoặc hiển thị case của khách khác.
* Hiển thị raw ticket, chat, visual evidence, location hoặc Customer Update của khách khác.
* User management hoặc phân quyền Staff động trong MVP.
