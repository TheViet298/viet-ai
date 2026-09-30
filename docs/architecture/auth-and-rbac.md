# Auth & RBAC (MVP)

| Role | Quyền |
|---|---|
| Guest | Xem Landing, FAQ, Policy; không chat, không xem case |
| Customer | Chat text/ảnh; xem case của chính mình; phản hồi/reopen case |
| Staff | Xem queue, ticket detail; Approve, Edit, Reroute, Request Info, Resolve, Close |

## Quy tắc

* Public register chỉ tạo `Customer`; Staff là account seed/invite.
* Backend bắt buộc kiểm tra role và ownership, không chỉ ẩn nút ở frontend.
* MVP không xác thực mã khách hàng/VinFast ID thật và không tích hợp CRM.
* Attachment không công khai; cảnh báo khách không tải VIN, biển số, khuôn mặt, giấy tờ cá nhân.
