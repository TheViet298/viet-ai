# P-142 — Decision Memory

> Tóm tắt để định tuyến; văn bản ADR Accepted bên dưới mới là nguồn quyết định. Nếu scope hoặc code đã thay đổi, kiểm tra lịch sử/ADR mới hơn trước khi sửa.

| Quyết định | Tóm tắt | Nguồn |
|---|---|---|
| Định vị và intent | Intake/triage/Case Brief/handoff; 2 intent sâu, 2 intent gọn; không phải AI sửa xe | [ADR-001](../../docs/decisions/ADR-001-mvp-scope.md) |
| Safety và HITL | Hard safety rules; ticket kỹ thuật, khiếu nại, confidence thấp cần Staff review; lưu audit thay đổi | [ADR-002](../../docs/decisions/ADR-002-triage-and-hitl.md) |
| RAG, dữ liệu, đánh giá | Nguồn VinFast công khai; citation; dưới ngưỡng/thiếu nguồn thì fallback; dữ liệu giả lập, không PII thật | [ADR-003](../../docs/decisions/ADR-003-data-and-evaluation.md) |
| Web/auth/ảnh | Web-only MVP; Guest tối đa 5 lượt FAQ; Customer xem case của mình; ảnh/OCR chỉ nhận định sơ bộ | [ADR-004](../../docs/decisions/ADR-004-web-first-auth-and-image-triage.md) |
| Vai trò/vị trí/xác nhận | Guest/Customer/Staff; location cần consent; map seed chỉ gợi ý; Customer xác nhận đóng hoặc mở lại sau cập nhật | [ADR-005](../../docs/decisions/ADR-005-roles-location-and-customer-confirmation.md) |

## Quy tắc dùng quyết định

- Không biến tóm tắt này thành yêu cầu mới; mở ADR gốc trước thay đổi ảnh hưởng scope, safety, privacy, auth hoặc lifecycle.
- Ngưỡng và flow phải lấy đúng ADR/implementation hiện hành; không ghép số từ nhiều tài liệu cũ.
- Nếu ADR mâu thuẫn nhau hoặc với yêu cầu user mới, ghi nhận mâu thuẫn và kiểm tra nguồn mới nhất; không tự sửa quyết định âm thầm.
