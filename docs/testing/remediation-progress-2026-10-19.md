# Remediation: bằng chứng triển khai ngày 19/10/2026

## P0 đã kiểm chứng

- Routing/ngôn ngữ/correction:192 ca qua, gồm27 phiên dài. Bổ sung kiểm tra nội dung so sánh, trụ P02 và rút CC01:31 ca qua (27 phiên/540 lượt/36 replay và4 controls).
- Evidence:29 ca qua, giữ header/điều kiện và chặn ghép số giữa bộ phận hoặc phạm vi sử dụng.
- Prompt:37 ca qua. Giữ nguyên đoạn nguồn4.811 byte trong giới hạn8.000 byte, không tăng budget. System/policy nguyên vẹn; task instruction được rút gọn giữ các ràng buộc.
- Compound:94 ca qua, có trạng thái từng ý và tổng phản hồi; partial/error không mang sang lượt sau; replay không ghi trùng.
- Observability:đóng cả7 lỗi baseline,23 ca chuyên biệt qua. Không tạo observation gốc trùng, không ghi usage0 giả, không đổi HTTP lỗi nghiệp vụ.
- Full backend sau sửa tương thích enum của cập nhật hồ sơ: **1.999 passed,25 skipped,6 subtests passed**. Skips gồm audit opt-in, không được tính là chứng nhận các phép đo đó. Frontend: **177 passed** trước đợt bổ sung data.

## Phép đo provider

Output sau P0 ở `eval/results/remediation-quality-p0-2026-10-19.json`:63 lượt dùng provider cấu hình thật, DB/người dùng tổng hợp, bản sao index2.196 chunks, tracing cloud tắt. Chẩn đoán nội bộ:45 answered,17 needs_data,1 external_action_required;22 sự kiện model parse. Đây **không phải** tỷ lệ đúng factual đã review.

Các lỗi có nguồn còn phải phân tích gồm claim điều kiện được diễn đạt khác nguyên văn, model sinh số/điều kiện không khớp nguồn, mô tả tính năng bị yêu cầu thành quy trình, và claim loại ngoài whitelist. Các phần thiếu scope/dữ liệu gồm lịch theo mẫu/năm, màu VF7, capacity VF3, cấu hình VF8 chưa xác định, giá/khả dụng dịch vụ. Không nới bộ kiểm tra để cho các số không có nguồn vượt qua.

Holdout40 câu (20VI/20EN,30answerable/10boundary) hiện là **bản nháp chờ review**, không phải oracle. `load_reviewed_holdout` chặn sử dụng khi thiếu reviewer, evidence hoặc manifest freeze khớp hash. Gate factual và phát hành vẫn mở.

## Dữ liệu và memory

Inventory/gap register và các raw/candidate được giữ riêng; không đổi active index. P1/P2 cùng kết quả nghiệm thu, review, migration và blocker sẽ được bổ sung khi hoàn thành. Chưa merge/push hoặc deploy phần triển khai này.
