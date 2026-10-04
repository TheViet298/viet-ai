# Báo cáo đánh giá StateGraph

Thời điểm UTC: 2026-10-03T17:22:28.543845+00:00
Chế độ: online; real local Chroma. Đo đầu ra thực; thiếu mẫu ghi N/A.

| Chỉ số | Kết quả | Ngưỡng MVP | Trạng thái |
|---|---:|---:|---|
| critical_safety_recall | 1.0 | 1.0 | PASS |
| intent_accuracy | 1.0 | 0.85 | PASS |
| routing_accuracy | 0.9333 | 0.8 | PASS |
| top_k_grounded_citation_rate | 0.85 | 0.85 | PASS |
| no_source_compliance | 1.0 | 0.8 | PASS |
| avg_latency_s | 0.136 | 2.5 | PASS |
| staff_review_compliance | 0.9333 | 0.85 | PASS |

Mẫu số: `{"critical": 10, "sourced": 20, "no_source": 10, "review": 60}`.
Grounding kiểm tra mã nguồn, ranh giới số/từ và dữ kiện bắt buộc trong câu trả lời; chưa chứng minh đúng ngữ nghĩa toàn bộ.
Nhãn có thể mâu thuẫn chính sách HITL; cần duyệt từng ca trước khi nghiệm thu.

Nhãn: pending_independent_review. Kết quả chẩn đoán; chưa phê duyệt nghiệm thu.
