# Auth & RBAC (MVP)

| Role | Quyền |
|---|---|
| Guest | Xem Landing, FAQ, Policy; chat FAQ/tư vấn tối đa 5 lượt/phiên; không theo dõi case |
| Customer | Chat text/ảnh; tạo/xem case của chính mình; chia sẻ vị trí theo consent; phản hồi/reopen case |
| Staff | Xem queue, ticket detail; Approve, Edit, Reroute, Request Info, Resolve, Close; dùng public/chat ở preview mode |

## Quy tắc

* Public register chỉ tạo `Customer` bằng SĐT + OTP demo; đây không phải xác minh chủ xe VinFast thật. Staff là account seed/invite.
* Backend bắt buộc kiểm tra role và ownership, không chỉ ẩn nút ở frontend.
* MVP không xác thực mã khách hàng/VinFast ID thật và không tích hợp CRM.
* Attachment không công khai; cảnh báo khách không tải VIN, biển số, khuôn mặt, giấy tờ cá nhân.
* Guest limit áp dụng theo `guest_session_id`; backend phải kiểm tra, không chỉ ẩn ở frontend.
