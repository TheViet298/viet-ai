# P-142 — Semantic Memory

Nguồn chuẩn: `docs/product/problem-and-mvp-scope.md`, ADR-001 đến ADR-005. Đây là định vị/thiết kế, không chứng minh runtime.

## Objective

VinFast ServiceFlow AI là Web Support Hub để tiếp nhận yêu cầu xe điện VinFast, làm rõ dữ kiện, sàng lọc an toàn, tra cứu nguồn công khai và tạo Case Brief cho nhân viên dịch vụ. Đây là lớp **intake, triage, handoff**; không tự chẩn đoán/sửa xe hoặc điều cứu hộ.

## MVP

- 4 intent: `Charging/Battery` + `Service/Incident` sâu; `Sales/General Info` + `Complaint/Feedback` gọn.
- Sạc/dịch vụ: làm rõ tối đa 2 lượt; vẫn thiếu thì tạo `Needs Information` cho Staff.
- Hard safety rules xử lý nguy cơ. Case kỹ thuật, khiếu nại và confidence thấp cần Staff review; Staff quyết định duyệt/chỉnh/điều phối.
- RAG chỉ dùng tài liệu VinFast công khai có nguồn. Thiếu bằng chứng thì nói chưa đủ dữ liệu, không suy đoán.
- Web-only MVP. Vision/OCR chỉ là tín hiệu sơ bộ, không chẩn đoán, xác nhận an toàn hay dispatch.
- Vị trí cần consent hoặc do khách nhập; điểm seed chỉ để gợi ý.

## Ranh giới dữ liệu và tích hợp

- Không VinFast CRM/API, xác minh chủ xe, CAN/OBD, booking riêng, Voice AI hay cứu hộ thực.
- Demo/eval/memory không chứa PII thật (VIN, biển số, điện thoại, danh tính); chỉ dùng ID giả lập.
- Customer chỉ xem case của mình; thư viện tình huống phải ẩn danh, không lộ case thô.

## Không suy diễn

- `UNKNOWN`/thiếu nguồn là hợp lệ. Diễn giải cảnh báo theo xe cần model/năm/phiên bản và owner manual khớp.
- KPI là mục tiêu, không phải kết quả. Report là snapshot; kiểm tra code/test/evidence hiện tại trước khi nói “đang chạy/đã đạt”.
