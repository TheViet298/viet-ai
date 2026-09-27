# Báo cáo chỉnh sửa metadata RAG và liên kết đánh giá

**Ngày:** 2026-09-27

**Phạm vi:** Tài liệu nguồn RAG, ví dụ API/demo và báo cáo đánh giá. Không thay đổi mã nguồn ứng dụng.

## Đã chỉnh sửa

| File | Nội dung |
| --- | --- |
| [Đặc tả nguồn RAG](architecture/rag-and-data-sources.md) | Đồng bộ tên tài liệu `SRC-APP-001` với tiêu đề trên trang VinFast; thay lỗi `2020 OK (200)` bằng trạng thái HTTP chưa xác nhận (`null`); bỏ danh sách model chưa được trang nguồn xác nhận; cập nhật ngày kiểm tra nội dung và ghi rõ giới hạn kiểm tra. Bổ sung thứ tự triển khai: Flow 1 trước, FAQ/RAG hoàn chỉnh sau. |
| [API contract](architecture/api-contract.md) | Đồng bộ ví dụ citation với metadata nguồn mới. |
| [Kịch bản demo](product/demo-scenarios.md) | Đồng bộ tên nguồn và ngày kiểm tra nội dung trong Flow 3. |
| [Báo cáo đánh giá](../eval/results/report.md) | Sửa link dataset từ đường dẫn `file:///` trên máy cá nhân thành đường dẫn tương đối trong repo. Ghi đúng trạng thái chưa chạy baseline và đặt đánh giá FAQ/RAG sau Flow 1. |

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
