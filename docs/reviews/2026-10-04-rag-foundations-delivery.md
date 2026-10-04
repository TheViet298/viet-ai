# Bàn giao nâng cấp nền tảng RAG

Đã triển khai local trên `feature/agent-long`, baseline `e7e2852`. Giữ thay đổi trong working tree để review; chưa commit/merge/push/deploy production. `.env` chọn `data/chroma-rag-foundations-candidate`; không có listener backend cổng 8000 khi kiểm tra, cấu hình dùng khi khởi động backend tiếp theo. Rollback về `data/chroma-quality-v4` rồi restart. Không xóa kho cũ.

## Thay đổi và bằng chứng

- Budget evidence 6.000 UTF-8 byte, prompt 8.000 byte; giữ câu hỏi/pinned và toàn bộ điều kiện. Prompt overflow chuyển review cùng category riêng, kể cả mode offline.
- Retrieval phân biệt missing index/collection, empty collection, lỗi xử lý và timeout; không xuất exception payload.
- Index child–parent: 2.163 parent, 2.168 child, tối đa 256 E5 token kể cả prefix/special. Manifest và parent hashes được kiểm; child ID/content hash và parent hash phải khớp trước expansion. Nguồn/model/variant/an toàn/distance kiểm trên parent.
- Evidence metrics trước/sau budget; nhãn thiếu là unavailable. Gate kiểm version/provenance/coverage/finite metrics và cấu hình. CI engineering public fixture tách acceptance và upload report.
- Eval có partition selection development/holdout và report riêng. Partition từ bộ cũ chưa tạo được holdout độc lập.

Kiểm chứng cuối: **176/176 test pass**, Ruff trên `src`, `tests`, scripts/eval thay đổi đạt; `git diff --check` không có lỗi whitespace. Review độc lập tìm ba lỗi integration và holdout gap; các lỗi có regression RED→GREEN. Config gate bypass được nâng mức Important và sửa/test.

| Offline diagnostic, 90 ca draft | Baseline trước sửa | Code mới/kho cũ | Code mới/candidate |
|---|---:|---:|---:|
| Grounded citation + required facts | 85% | 90% | 90% |
| Critical safety recall | 100% | 100% | 100% |
| No-source compliance | 100% | 100% | 100% |

Kho cũ/candidate không đổi kết quả từng ca grounded/no-source/safety/routing/review. Candidate final mean khoảng 52ms warm local offline; không phải SLA tải hoặc thời gian provider thật. Reports tại `eval/results/rag-foundations/`: `comparison.json`, `candidate-final/agent_results.json`, `engineering.json`, `acceptance-gate.json`.

Acceptance **fail đúng**: labels chưa approved, thiếu coverage expected evidence IDs, Evidence Recall/Precision unavailable. Không tự sửa draft thành approved, không tạo số RAGAS. Cần nhãn được review và tập holdout mới độc lập trước nghiệm thu production.

## Quyết định thực hiện và giới hạn

1. Thực hiện trong checkout hiện tại theo người dùng duyệt; lưu baseline và giữ thay đổi chưa commit. Rủi ro nếu tích hợp sai: cần stage đúng phạm vi.
2. Dùng bookkeeping PowerShell/Python tương đương skill wrappers Bash trên Windows, giữ ledger/evidence. Rủi ro: cần đối chiếu ledger thủ công khi tiếp tục.
3. Holdout cũ được chia ổn định và CLI lọc trước execution, nhưng tính độc lập chưa được thiết lập. Không dùng nó cho acceptance hoặc tune; cần tập mới/review. Rủi ro nếu bỏ qua: đánh giá lạc quan.
4. Khả năng production và Faithfulness ngữ nghĩa chưa được xác nhận từ draft/offline. Rủi ro nếu coi là nghiệm thu: lỗi chưa đo lọt qua.
5. Provider thật chưa gọi trong đợt này; kết quả deterministic không chứng minh hành vi online. Rủi ro: cần eval online sau duyệt nhãn/ngân sách.
6. Tài liệu vận hành đã hoàn tất với build/audit/eval/rollback. Source lifecycle, auth và load testing giữ backlog đúng đặc tả; chưa đủ điều kiện public production.

Minor còn lại: adapter judge mới có raw IDs/response, chưa xuất riêng sanitized generation context và final citation records. Rủi ro: chưa đánh giá Faithfulness từ adapter đó; không ảnh hưởng engineering gate hiện tại.
