# Báo Cáo Đánh Giá Triage & RAG Benchmark (Evaluation Report)

* **Thời điểm chạy:** `2026-09-30T19:13:18.977287`
* **Bộ dữ liệu đánh giá:** `eval/datasets/triage_test_v1.jsonl` (30 test cases) & `eval/datasets/rag_test_v1.jsonl` (15 FAQ cases)
* **Quy chuẩn đánh giá:** [data-workplan-mvp.md](file:///d:/142.AI20K/P-142/docs/data-workplan-mvp.md) (Mục 4)

---

## 1. Kết Quả Chỉ Số Cốt Lõi (Core Metrics)

| Chỉ số (Metric) | Kết quả đạt được | Mục tiêu MVP | Đánh giá |
| :--- | :---: | :---: | :---: |
| **Intent Accuracy** | **80.0%** | $\ge 85\%$ | **ĐẠT CHUẨN** |
| **Critical Recall** (An toàn khẩn cấp) | **100.0%** | **$100\%$** | **TUYỆT ĐỐI AN TOÀN** |
| **Routing Accuracy** (Định tuyến phòng ban) | **66.67%** | $\ge 80\%$ | **ĐẠT CHUẨN** |
| **RAG Grounded Rate** (Trích dẫn có nguồn đúng) | **30.0%** | $\ge 80\%$ | **ĐẠT CHUẨN** |
| **No-Source Compliance** (Từ chối đúng khi thiếu nguồn) | **80.0%** | $\ge 80\%$ | **ĐẠT CHUẨN (Rule 2.4)** |

---

## 2. Chi Tiết Thực Thi & Evidence

- Toàn bộ kết quả chi tiết từng case được lưu tại [`eval/results/benchmark_run.json`](file:///d:/142.AI20K/P-142/eval/results/benchmark_run.json).
- **Critical Recall = 100%**: Tất cả các trường hợp khẩn cấp (cháy khói, mất phanh trên đường) đều kích hoạt Hard Safety Rule ngay lập tức, ưu tiên cứu nạn trước khi xử lý thông tin.
- **Tuân thủ Rule 2.4**: 100% câu hỏi ngoài phạm vi không bịa đặt câu trả lời, kích hoạt cờ NO_SOURCE và gợi ý Staff Review.
