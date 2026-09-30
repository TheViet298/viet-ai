# ADR-004 — Web-first, Role Access & Image Triage

**Trạng thái:** Accepted  
**Ngày:** 2026-09-30

## Quyết định

* MVP chỉ có Web Support Hub. Đa kênh là Future Scope.
* Guest xem Landing/FAQ/Policy; phải đăng nhập mới chat.
* Customer chat và chỉ xem case của mình. Staff dùng account seed/invite; không đăng ký Staff công khai.
* Customer gửi text, ảnh cảnh báo/táp-lô hoặc cả hai.
* OCR/Vision trích xuất cảnh báo, mã lỗi hoặc dấu hiệu phổ biến để Agent hỏi thêm context.
* Kết quả Vision là nhận định sơ bộ; không chẩn đoán nguyên nhân, sửa xe, điều cứu hộ thật hoặc auto-close case.
* Không tích hợp VinFast CRM/API; không xác minh VinFast ID/mã khách hàng thật.

## Hệ quả MVP

* Ảnh được lưu riêng tư và hiển thị trong Ticket Detail cho Staff.
* Ảnh không rõ/confidence thấp: Agent yêu cầu ảnh rõ hơn hoặc chuyển Staff Review.
* Public Knowledge Hub chỉ dùng nội dung/link nguồn VinFast đã kiểm chứng; không làm CMS.
