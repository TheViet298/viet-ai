# Báo cáo triển khai cải thiện Agent — 04/10/2026

Đã triển khai cải thiện backend, cấu hình KB local và công cụ eval theo kế hoạch ngày 03/10. Chưa phê duyệt nghiệm thu hệ thống: nhãn/độ đúng ngữ nghĩa cần duyệt độc lập, RAG v1 còn thấp và Gemini online chưa đủ coverage.

## 1. Thay đổi và kiểm chứng

- Triage ưu tiên sự cố thực trước câu hỏi giá/hướng dẫn; giữ yêu cầu chuyên viên cho hợp đồng cá nhân và báo giá lăn bánh. Routing cứu hộ/mobile/refusal dùng chung với brief.
- RAG lọc dòng xe trước shortlist 20; kiểm tra URL, phiên bản Eco/Plus/năm và chủ đề; không dùng mục lục/tiêu đề link thay dữ kiện. Giữ hướng dẫn và điều kiện nguyên vẹn trong budget; thiếu bằng chứng chuyển NO_SOURCE/HITL.
- Candidate multilingual E5 ONNX v4 có 2.163 chunks, được chọn tại `.env` local. Kho gốc giữ nguyên. Dữ liệu/model bị ignore; hướng dẫn tái tạo và rollback trong [tài liệu vận hành](D:/142.AI20K/P-142/docs/agent-quality-v2.md).
- Giới hạn một model attempt/lượt, không retry foreground, circuit quota 60 giây. Sửa race success cũ và probe bị hủy; cache khởi tạo có khóa, corpus invalidation nhận biết thay đổi cùng số chunks.
- Gemini thực trả HTTP 400 vì transport deadline dưới 10 giây. Đã sửa transport tối thiểu 10 giây; asyncio vẫn giới hạn chờ model 1,2 giây, budget từ intake 2 giây. Chưa cam kết mọi request HTTP/SQLite luôn hoàn tất trong 2 giây.
- **142 tests đạt**, Ruff đạt và `git diff --check` không có lỗi. [Kết quả regression XML](D:/142.AI20K/P-142/eval/results/quality-v2/regression.xml). Runner riêng kiểm chứng **10/10 tình huống bridge/API**: 4 hội thoại sửa model mới và 6 regressions hiện hữu cho hỏi lại, quota/emergency, ownership, staff workflow, explicit case và lỗi lưu DB. [Kết quả nhiều lượt](D:/142.AI20K/P-142/eval/results/quality-v2/multiturn/multiturn_results.json).

## 2. So sánh trên cùng 45 ca v1

Giữ nguyên nhãn v1. Đây là regression đã được xem, không gọi là holdout mới. Trước dùng baseline offline đã lưu; sau dùng `delivery-v1` với KB v4.

| Chỉ số | Baseline | Sau cải thiện | Ngưỡng |
|---|---:|---:|---:|
| Phát hiện critical | 100.00% | 100.00% | 100% |
| Đúng intent | 76.67% | 96.67% | 85% |
| Đúng routing | 60.00% | 96.67% | 80% |
| Grounding theo rubric tự động | 20.00% | 20.00% | 85% |
| Tuân thủ NO_SOURCE | 100.00% | 100.00% | 80% |
| Latency trung bình (giây) | 0.201 | 0.149 | 2.5 |
| Khớp nhãn staff review | 70.00% | 83.33% | 85% |

Không bỏ sót ca có nhãn bắt buộc review trong run v1 cuối (0 false negatives); mức khớp nhãn review 83,33% vẫn dưới 85%. Critical v1 chỉ có một mẫu nên không đủ suy rộng an toàn.
[Bảng ca chuyển đúng/sai](D:/142.AI20K/P-142/eval/results/quality-v2/comparison-v1.json) giữ cả fail→pass và pass→fail. [Audit tám ca RAG chưa đạt](D:/142.AI20K/P-142/eval/results/quality-v2/rag-audit-v1.jsonl) có query, keyword kỳ vọng, chunk ID và lý do lọc.

## 3. Bộ 90 ca dự thảo — ba chế độ

60 triage + 30 RAG; 10 critical, 20 kỳ vọng có nguồn, 10 NO_SOURCE. Bộ này đã dùng chẩn đoán/tinh chỉnh; tất cả nhãn còn trạng thái draft. Không coi kết quả này là nghiệm thu độc lập.

| Chỉ số | Ngưỡng | Offline | Provider failure | Online có fallback |
|---|---:|---:|---:|---:|
| Phát hiện critical | 100% | 100.00% — PASS | 100.00% — PASS | 100.00% — PASS |
| Đúng intent | 85% | 100.00% — PASS | 100.00% — PASS | 100.00% — PASS |
| Đúng routing | 80% | 93.33% — PASS | 93.33% — PASS | 93.33% — PASS |
| Grounding theo rubric tự động | 85% | 85.00% — PASS | 85.00% — PASS | 85.00% — PASS |
| Tuân thủ NO_SOURCE | 80% | 100.00% — PASS | 100.00% — PASS | 100.00% — PASS |
| Latency trung bình (giây) | 2.5 | 0.116s — PASS | 0.114s — PASS | 0.136s — PASS |
| Khớp nhãn staff review | 85% | 93.33% — PASS | 93.33% — PASS | 93.33% — PASS |

Các ngưỡng tự động đều đạt trên bộ draft. Grounding là 17/20; không có false negative theo nhãn review draft. Rubric chỉ kiểm tra response type, source ID, ranh giới số/từ và dữ kiện bắt buộc trong phần trả lời; cần đánh giá ngữ nghĩa, điều kiện áp dụng và đúng loại linh kiện riêng.

| Chế độ | p50 / p95 (giây) | LLM outcomes |
|---|---:|---|
| delivery-offline | 0.060 / 0.112 | `{}` |
| delivery-provider-failure | 0.061 / 0.142 | `{"circuit_open": 22}` |
| delivery-online | 0.064 / 0.133 | `{"circuit_open": 21, "rate_limited": 1}` |

Online cuối có **1 rate_limited, 21 circuit_open, 0 parsed**. Điểm online phản ánh fallback extractive/NO_SOURCE; chất lượng generation Gemini chưa được xác nhận. Quota RPM/TPM và chi phí chưa có số liệu: N/A; không tự đặt pacing theo quota suy đoán. Provider-failure mở circuit chủ đích, không phải chạy provider trả lỗi HTTP thực.

[Offline](D:/142.AI20K/P-142/eval/results/quality-v2/delivery-offline/agent_report.md) · [Provider failure](D:/142.AI20K/P-142/eval/results/quality-v2/delivery-provider-failure/agent_report.md) · [Online](D:/142.AI20K/P-142/eval/results/quality-v2/delivery-online/agent_report.md). JSON mỗi run có hash dataset/prompt/KB, embedding version, latency theo node và provider outcomes.

Ba run cuối có cùng fingerprint logical KB `100028ac31524ff40942ab004a9b8e085cda4dad3242522c0a9a972309c8d24a`. Hash vật lý SQLite có thể thay đổi do housekeeping; không dùng khác biệt đó để suy ra tài liệu đã đổi. [Hash raw/model/tokenizer](D:/142.AI20K/P-142/eval/results/quality-v2/kb-fingerprint.json) đo riêng sau các run product trước; các run delivery đã ghi fingerprint logical ngay trong metadata.

## 4. Nguồn dữ liệu và các lỗi còn lại

HTTP trực tiếp của sáu URL refresh trả 403. Giữ ngày xác minh cũ 2026-09-30, không tạo HTTP 200 hoặc phê duyệt URL catalog mới. Bảng bảo hành xe bị crawler cũ bỏ sót; supplement có provenance từ [chính sách VinFast](https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-oto), phân biệt bảo hành xe với pin cao áp. Nội dung truy cập được qua web không tự chuyển thành bản xác minh HTTP mới.

| Nhóm ca | Vấn đề và xử lý |
|---|---|
| RAG-004/005 | URL VF6/VF7 trong chunk khác registry SRC-009; giữ NO_SOURCE cho đến khi exact URL được xác minh. |
| RAG-003; ACCEPT-R-008 | Quy trình đặt lịch dài vượt budget conservative. Không cắt mất bước hoặc lấy quy trình sạc thay quy trình dịch vụ; giữ fallback khi không có đoạn phù hợp. |
| RAG-006/008/010 | Hướng dẫn cứu hộ/ngập nước/ADAS cần nội dung đủ, đúng model và đủ điều kiện; current coverage/rubric chưa đạt. |
| RAG-007/009 | Chu kỳ bảo dưỡng cần model và dữ kiện nguồn; một số keyword quá cụ thể so với nguồn. Chưa tự đổi nhãn v1. |
| ACCEPT-R-017 | Nhãn hệ truyền động cần căn cứ riêng; không dùng thời hạn gỉ sét thay đáp án. |
| ACCEPT-R-019 | Nguồn SRC-005 snapshot hiện hữu thiếu dữ kiện Mobile Service; tiêu đề nguồn không được chấm như câu trả lời. |

Rà soát độc lập phát hiện bảy lỗi quan trọng và các repro đã được sửa: incident→FAQ, model/variant/year, quota race, canceled probe, mất bước, chấm sai số/chủ đề và model prefilter. Code review không thay thế người xác nhận chính sách hoặc kỹ thuật của hãng.

## 5. Điều kiện còn thiếu để nghiệm thu

1. Duyệt nhãn theo ADR và nguồn, nhất là FAQ thiếu nguồn, hợp đồng, và các câu hỏi kỹ thuật. Giữ danh sách đề xuất adjudication; chưa gắn approved tự động.
2. Hoàn thiện nguồn catalog/manual và trích được câu trả lời đúng, đầy đủ trong budget; RAG trên tập v1 vẫn 20%. Cần reviewer kiểm tra điều kiện, model/phiên bản/năm và đúng chủ đề từng đáp án.
3. Lập bộ holdout mới được review độc lập; bộ 90 ca hiện tại đã được dùng phát triển. Chạy lại đủ bảy KPI và nhóm bridge/API riêng.
4. Có quota cho một run đủ phản hồi Gemini parsed, đo generation/grounding/latency/chi phí thật trước khi xác nhận chế độ online.

Đã triển khai trong workspace local; chưa commit, push hay deploy hạ tầng. Production auth, danh bạ điểm dịch vụ thật, Vision/OCR và hạ tầng nằm ngoài phạm vi kế hoạch cải thiện chất lượng này.
