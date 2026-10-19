# Kết quả triển khai và kiểm thử — 19/10/2026

## Trạng thái

Đã triển khai code trong nhánh `codex/agent-quality-remediation`, checkout audit riêng. P0 và candidate P1 đã có kiểm thử; memory SQL đã triển khai và kiểm chứng SQLite. **Gate PostgreSQL bị chặn** vì chưa có database kiểm thử riêng, theo xác nhận của người dùng. Feature mặc định tắt. Chưa tích hợp hai repo hoặc triển khai môi trường thật khi gate release còn mở.

## Kết quả

| Phép kiểm tra | Kết quả |
| --- | --- |
| Full backend cuối | 2145 passed, 47 skipped, 9 warnings, 6 subtests passed in 276.76s (0:04:36) |
| Frontend | 177 passed, 0 failed |
| Holdout đã review độc lập và freeze | 30/30 có dữ liệu; 10/10 câu biên |
| Phiên dài | 27 phiên, 540 lượt, 36 replay; nội dung/state/nguồn/ngôn ngữ/mã hồ sơ |
| Memory xuyên process | 11 capability đạt; mỗi request process mới |
| Hai user xen kẽ | 120 lượt ở độ dài 10/20/30; replay và cách ly owner |
| Memory với provider thật đã cấu hình | 2 process recall VI/EN đạt; dữ kiện đọc SQL, không cần model sinh |
| Review độc lập | 4 lỗi memory + 2 lỗi scope đã tái hiện đỏ và sửa; 149 regression liên quan đạt |

Holdout SHA256: `1dd4d42c5f00f302315738758b1361fb703496321d01bccd1a93e86db96f6a81`. Dataset giữ nguyên sau freeze cuối. Mỗi câu kiểm tra nội dung, trạng thái, ngôn ngữ và nguồn. Model parse 7 sự kiện, lỗi provider 0. Latency median 109,5 ms, p95 1.797 ms. Bộ này đã được chạy lại để sửa lỗi, nên kết quả là regression, không phải accuracy trên câu hỏi production chưa thấy.

63 probe riêng: 48 answered, 14 needs_data, 1 external_action_required; 22 model parsed, 0 provider errors. Đây là trạng thái nội bộ; không suy thành 48 câu đúng factual. Output nguyên văn và nguồn được lưu trong `eval/results/remediation-final/provider-release.json`.

## Các thay đổi chính

- Hỏi VI/EN trả theo ngôn ngữ câu hỏi; nhận diện câu nhiều ý, giữ phần có nguồn và trạng thái từng phần.
- Giữ header/điều kiện nguồn; không lấy số của bộ phận, phiên bản hay chuẩn đo khác. Giữ budget hiện tại; sửa observation gốc trùng.
- Câu hỏi English kỹ thuật được gắn intent xác định, giữ toàn bộ câu gốc/model/trim/year/qualifier; không nhờ model dịch lại ý hỏi đã nhận diện.
- Snapshot chặn thiếu phiên bản/năm, nhiều model chưa tách rõ, chuẩn đo/SOC/công suất trụ hoặc điều kiện vận hành chưa có nguồn. Không biến câu hỏi nhiều model thành thông số của một model.
- Sáu key memory SQL có consent, provenance, revision/CAS, correction/forget, profile sync, auth và transaction chung với accepted turn. Không nhớ nhầm xe quan tâm, vị trí trạm hiện tại hay nội dung tài liệu.
- Quên theo đúng thuộc tính; phủ định sở hữu xóa model và thuộc tính phụ; nhiều xe mâu thuẫn yêu cầu làm rõ; sửa profile khi flag tắt vẫn giữ facts/revision hiện có nhất quán.
- Xóa phiên nguồn/clear history vô hiệu dữ kiện chat; replay cũ không phục hồi dữ kiện đã quên. Không xóa hồ sơ nghiệp vụ chỉ vì quên dữ kiện cá nhân.

## Data và candidate

Đã xác minh VF5 capacity khả dụng 37,23 kWh và 6 màu ở mức model; VF3 lịch bảo dưỡng 15.000 km/12 tháng ở mức chưa phân năm/trim. Giữ caveat về năm/trim/tồn kho/điều kiện sử dụng. VF3 capacity vẫn null. Các lịch model khác cần đọc ảnh/header/footnote chính thức; một số nguồn trả403. Không dùng số từ thị trường khác để lấp ô trống.

Candidate 2.200 children, embedding E5/L2, token bound 256 và parent/provenance hash nằm trong `eval/results/knowledge-remediation/candidate-v1-report.json`. Không đổi active index. Builder hoàn tất rồi gặp lỗi in Unicode ở CLI; lỗi in đã sửa, manifest/parent-map/token bound đã kiểm chứng lại, không build đè thư mục.

## Câu chưa trả lời đủ trong 63 probe cuối

Không coi toàn bộ là thiếu data: unsupported_numeric/textual có thể do model sinh nội dung không khớp nguồn hoặc điều kiện được kiểm tra nghiêm. Giữ từ chối xác nhận thay vì nới validator cho số/tính năng không có nguồn.

| Câu hỏi | Lý do kỹ thuật quan sát được |
| --- | --- |
| Thời hạn bảo hành xe VinFast VF 8 tiêu chuẩn là bao nhiêu năm hoặc bao nhiêu km? | `unsupported_numeric_claim` |
| Thời hạn bảo hành xe VinFast VF 5 là bao nhiêu năm? | `unsupported_numeric_claim` |
| Chu kỳ bảo dưỡng định kỳ đầu tiên của xe ô tô điện VinFast là ở mốc nào? | `unsupported_numeric_claim` |
| Hệ thống hỗ trợ người lái ADAS trên xe VF 8 bao gồm những tính năng cơ bản nào? | `unsupported_textual_claim` |
| VF7 Plus có màu gì? | `no_eligible_evidence` |
| Bảo hành pin cao áp VF8 bao lâu? | `unsupported_numeric_claim` |
| Bảo hành ắc quy 12V VF8 bao lâu? | `unsupported_numeric_claim` |
| VF8 chạy dịch vụ thương mại được bảo hành thế nào? | `unsupported_numeric_claim` |
| Xe bị ngập nước có được bảo hành không? | `unsupported_textual_claim` |
| Lịch bảo dưỡng định kỳ VF8 là gì? | `no_eligible_evidence` |
| VF5 bảo dưỡng mỗi bao nhiêu km? | `unsupported_numeric_claim` |
| VF8 đi được bao xa một lần sạc? | `unresolved_catalog_scope` |
| Dung lượng pin VF8 là bao nhiêu? | `unresolved_catalog_scope` |
| Dung lượng pin VF3 là bao nhiêu? | `unresolved_catalog_scope` |

Các câu kỹ thuật nhiều model chưa tách rõ hiện được giữ lại để làm rõ, chưa cam kết trả đủ từng model. Lịch chính xác theo model/year, màu chưa được review, giá/khả dụng dịch vụ và booking thực tế vẫn cần nguồn/kết nối tương ứng.

## Gate còn mở

1. PostgreSQL: migration/CAS/concurrency chưa được chạy trên DB riêng; không dùng SQLite thay chứng nhận PostgreSQL.
2. Chưa bật memory hoặc đổi index ở môi trường thật; chạy DDL trước app rồi mới bật flag sau smoke/gate. Quay lui flag/app trước, giữ schema cộng thêm.
3. Tích hợp P-142 feature/agent-long và viet-ai test/agent-long chỉ sau quyết định gate/release; không force-push hoặc đưa thay đổi vào main.

Chi tiết triển khai/quay lui: `docs/testing/user-memory-deployment-2026-10-19.md`. Review và giới hạn: `docs/testing/holdout-independent-review-2026-10-19.md`.
