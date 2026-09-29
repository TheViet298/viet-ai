# Evaluation Target Metrics & Benchmark Report

> **Người phụ trách:** Khôi (Data/Eval Lead)  
> **Cập nhật lần cuối:** 2026-09-24  
> **Trạng thái:** Benchmark Ready / Baseline Testing

---

## 1. Định nghĩa Công thức & Mục tiêu Đánh giá (Evaluation Metrics Definition)

> [!NOTE]
> Các công thức dưới đây là **chuẩn đo lường thống nhất** để Khôi và nhóm AI triển khai benchmark trên tập dữ liệu mô phỏng `eval/datasets/triage_cases_v1.jsonl`.

| Tên Chỉ số (Metric) | Công thức Tính Toán Thống Nhất | Target Benchmark | Mục đích Đo lường |
| :--- | :--- | :---: | :--- |
| **Intent Accuracy** | $\frac{\text{Số case phân loại Intent đúng}}{\text{Tổng số case}}$ | $\ge 90\%$ | Đánh giá độ chính xác của phân loại 4 nhóm Intent |
| **Critical Recall** | $\frac{\text{Số case Critical được gắn nhãn Critical}}{\text{Tổng số case Critical thực tế}}$ | **$100\%$** | Đảm bảo không bỏ sót bất kỳ nguy cơ an toàn nào |
| **Brief Completeness** | $\frac{\text{Số required fields đã thu thập được}}{\text{Tổng số required fields theo intent}}$ | $\ge 95\%$ | Đánh giá tính đầy đủ dữ liệu trước khi bàn giao Staff |
| **Routing Accuracy** | $\frac{\text{Số case đề xuất đúng bộ phận tiếp nhận}}{\text{Tổng số case có expected routing}}$ | $\ge 90\%$ | Đánh giá độ chuẩn xác điều phối (Kỹ thuật/Cứu hộ/CSKH) |
| **RAG Grounded Rate** | $\frac{\text{Số câu trả lời có citation hợp lệ đã kiểm chứng}}{\text{Tổng số câu trả lời FAQ}}$ | **$100\%$** | Đảm bảo 100% câu trả lời FAQ có căn cứ từ tài liệu công khai |

---

## 2. Danh mục Bộ dữ liệu Đánh giá (Evaluation Datasets)

* **Tập dữ liệu Benchmark v1:** [`eval/datasets/triage_cases_v1.jsonl`](file:///d:/Vin_AI/P-142/eval/datasets/triage_cases_v1.jsonl)
* **Quy chuẩn dữ liệu:**
  * 100% dữ liệu tình huống được mô phỏng dựa trên tín hiệu từ khảo sát thăm dò ban đầu (Charging, Battery, Taplo warning, Khiếu nại dịch vụ, Hướng dẫn tính năng ứng dụng).
  * **Tuyệt đối không chứa PII:** Toàn bộ thông tin cá nhân (email, họ tên, số điện thoại, biển số xe) đã được loại bỏ và thay bằng ID mô phỏng.

---

## 3. Kế hoạch Chạy Đánh giá Tự động (Execution Plan)

```bash
# 1. Chạy kiểm thử Unit test cho Rule Engine và Parser
pytest tests/ -v

# 2. Chạy pipeline đánh giá benchmark trên tập test cases
python scripts/run_triage_eval.py --dataset eval/datasets/triage_cases_v1.jsonl
```
