# Báo cáo chỉnh sửa metadata RAG, liên kết đánh giá và tiến độ WORKLOG

**Ngày:** 2026-09-27

**Phạm vi:** Tài liệu nguồn RAG, ví dụ API/demo, báo cáo đánh giá và đối chiếu tiến độ trước 26/09/2026. Không thay đổi mã nguồn ứng dụng.

## Đã chỉnh sửa

| File | Nội dung |
| --- | --- |
| [Đặc tả nguồn RAG](architecture/rag-and-data-sources.md) | Đồng bộ tên tài liệu `SRC-APP-001` với tiêu đề trên trang VinFast; thay lỗi `2020 OK (200)` bằng trạng thái HTTP chưa xác nhận (`null`); bỏ danh sách model chưa được trang nguồn xác nhận; cập nhật ngày kiểm tra nội dung và ghi rõ giới hạn kiểm tra. Bổ sung thứ tự triển khai: Flow 1 trước, FAQ/RAG hoàn chỉnh sau. |
| [API contract](architecture/api-contract.md) | Đồng bộ ví dụ citation với metadata nguồn mới. |
| [Kịch bản demo](product/demo-scenarios.md) | Đồng bộ tên nguồn và ngày kiểm tra nội dung trong Flow 3. |
| [Báo cáo đánh giá](../eval/results/report.md) | Sửa link dataset từ đường dẫn `file:///` trên máy cá nhân thành đường dẫn tương đối trong repo. Ghi đúng trạng thái chưa chạy baseline và đặt đánh giá FAQ/RAG sau Flow 1. |
| [WORKLOG](../WORKLOG.md) | Đối chiếu đủ 16 đầu việc ngày 20, 23, 24/09 với bằng chứng, giới hạn xác minh và trạng thái đề xuất; điều chỉnh các nhãn `Done` quá rộng, đặc biệt Mentor Duty và form khảo sát. |
| [JOURNAL](../JOURNAL.md) | Đồng bộ các checklist và nhận định tuần với kết quả kiểm tra: đầu ra tài liệu khác tính năng triển khai, các việc ngoài repo chưa được xác minh, các mục còn mở được giữ ở trạng thái chưa xong. |

## Đã tạo mới

- File báo cáo này: `docs/change-report-2026-09-27-rag-metadata.md`.

## Căn cứ và giới hạn

- [Trang hướng dẫn ứng dụng VinFast cho ô tô điện (Phần 2)](https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast) đọc được qua trình duyệt và có các mục về trạng thái sạc, đặt lịch dịch vụ và theo dõi sửa chữa. Trang chưa xác nhận rõ phạm vi cho từng model trong danh sách cũ.
- Lệnh kiểm tra HTTP trực tiếp từ môi trường phát triển trả `403`; vì thế không khẳng định mã HTTP hiện tại là `200`. Trường `status_code` được để `null` cho đến khi pipeline nạp nguồn kiểm tra được mã HTTP trong chính môi trường chạy của nó.
- Metadata nguồn đã được chuẩn bị; ứng dụng chưa có pipeline FAQ/RAG hoàn chỉnh. Flow 1 (`Charging/Battery` từ tiếp nhận đến Staff Review và cập nhật trạng thái) vẫn là ưu tiên triển khai trước.

## Kết quả kiểm tra

- Đường dẫn tương đối từ `eval/results/report.md` đến `eval/datasets/triage_cases_v1.jsonl` tồn tại.
- Các ví dụ `SRC-APP-001` được chỉnh sửa thống nhất tiêu đề, ngày kiểm tra, `status_code` và `applicable_models`.
- Hai ví dụ JSON trong đặc tả nguồn và ví dụ citation trong API contract parse được; `git diff --check` không phát hiện lỗi khoảng trắng.

## Bổ sung Task 1: đối chiếu tiến độ và bằng chứng

Bảng trong [WORKLOG](../WORKLOG.md) có một dòng cho mỗi đầu việc trước 26/09/2026: **16 mục**, gồm 7 mục có bản thảo/tài liệu/quyết định kiểm tra được, 4 mục chỉ hoàn thành một phần hoặc cần đồng bộ, 3 mục WIP và 2 mục chưa thể xác minh bằng repo. Những nhãn này phản ánh đầu ra trong repo, không xác nhận khảo sát gốc, thời gian làm việc hoặc việc nộp bài trên hệ thống khác.

Hai mục chưa xác minh là bản form khảo sát và Mentor Duty. Không thêm bản khảo sát, dữ liệu người tham gia hoặc biên nhận nộp bài vào repo. Nếu nhóm muốn lưu các tài liệu đó, cần xin phép trước và kiểm tra, loại bỏ dữ liệu cá nhân phù hợp.

Các phần chất lượng còn mở: README chính vẫn là template, chưa thấy backlog/checklist Gate G1 riêng; screen spec còn `name`/`phone` trái với quy tắc không PII thật; dataset mới có 12/40 ca mục tiêu; agent guardrails và Case lifecycle API chưa triển khai. Việc viết scope, rule matrix và API contract được ghi nhận là hoàn thành bản thảo, không phải Flow 1 E2E đã chạy.
