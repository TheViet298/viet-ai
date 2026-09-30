# Evaluation Target Metrics & Benchmark Report

> **Người phụ trách:** Khôi (Data/Eval Lead)  
> **Cập nhật lần cuối:** 2026-09-30
>
> **Trạng thái:** Đã định nghĩa mục tiêu và dataset mẫu; chưa chạy baseline

---

## 1. Định nghĩa Công thức & Mục tiêu Đánh giá (Evaluation Metrics Definition)

> [!NOTE]
> Các công thức dưới đây là **chuẩn đo lường thống nhất** để Khôi và nhóm AI triển khai benchmark. Tình huống Agent dùng `eval/datasets/triage_cases_v1.jsonl`; QA hậu mãi/CSKH cho RAG dùng `eval/datasets/after_sales_customer_care_v1.csv`.

| Tên Chỉ số (Metric) | Công thức Tính Toán Thống Nhất | Target Benchmark | Mục đích Đo lường |
| :--- | :--- | :---: | :--- |
| **Intent Accuracy** | $\frac{\text{Số case phân loại Intent đúng}}{\text{Tổng số case}}$ | $\ge 90\%$ | Đánh giá độ chính xác của phân loại 4 nhóm Intent |
| **Critical Recall** | $\frac{\text{Số case Critical được gắn nhãn Critical}}{\text{Tổng số case Critical thực tế}}$ | **$100\%$** | Đảm bảo không bỏ sót bất kỳ nguy cơ an toàn nào |
| **Brief Completeness** | $\frac{\text{Số required fields đã thu thập được}}{\text{Tổng số required fields theo intent}}$ | $\ge 95\%$ | Đánh giá tính đầy đủ dữ liệu trước khi bàn giao Staff |
| **Routing Accuracy** | $\frac{\text{Số case đề xuất đúng bộ phận tiếp nhận}}{\text{Tổng số case có expected routing}}$ | $\ge 90\%$ | Đánh giá độ chuẩn xác điều phối (Kỹ thuật/Cứu hộ/CSKH) |
| **RAG Grounded Rate** | $\frac{\text{Số câu trả lời có citation hợp lệ đã kiểm chứng}}{\text{Tổng số câu trả lời FAQ}}$ | **$100\%$** | Đảm bảo 100% câu trả lời FAQ có căn cứ từ tài liệu công khai |

---

## 2. Danh mục Bộ dữ liệu Đánh giá (Evaluation Datasets)

* **Hotline cứu hộ/hỗ trợ trên đường/cảnh báo:** [`triage_cases_v1.jsonl`](../datasets/triage_cases_v1.jsonl), 50 case (10 chuyển đổi, 40 mới), giữ nhãn đánh giá Agent. Bộ này là tập con theo chủ đề, chưa đo đầy đủ cả 4 intent của hệ thống.
* **Hậu mãi và chăm sóc khách hàng:** [`after_sales_customer_care_v1.csv`](../datasets/after_sales_customer_care_v1.csv), 61 case (21 chuyển đổi, 40 mới), QA kèm citation, không có nhãn triage. Dùng để đối chiếu câu trả lời/citation khi xây RAG sau này; cần harness đánh giá riêng.
* **Schema và cách tách:** [`datasets/README.md`](../datasets/README.md). Bộ hỗn hợp 52 case cũ được giữ trong archive để truy vết, không ghép vào hai bộ đang sử dụng khi benchmark.
* **Quy chuẩn dữ liệu:**
  * Dữ liệu tình huống được mô phỏng từ nguồn VinFast công khai và quy tắc dự án, bao gồm sạc/pin, cảnh báo, cứu hộ, phản ánh dịch vụ và hướng dẫn tính năng ứng dụng.
  * **Tuyệt đối không chứa PII:** Toàn bộ thông tin cá nhân (email, họ tên, số điện thoại, biển số xe) đã được loại bỏ và thay bằng ID mô phỏng.

---

## 3. Kế hoạch Chạy Đánh giá Tự động (Execution Plan)

Flow 1 (`Charging/Battery`) được triển khai và đánh giá trước. Các chỉ số FAQ/RAG trong bảng trên là mục tiêu cho giai đoạn sau Flow 1, chưa phải kết quả đạt được. Script `scripts/run_triage_eval.py` trong ví dụ dưới đây hiện chưa có trong repo; cần tạo script và ghi kết quả chạy thực tế trước khi công bố baseline.

```bash
# 1. Chạy kiểm thử Unit test cho Rule Engine và Parser
pytest tests/ -v

# 2. Chạy pipeline đánh giá benchmark trên tập test cases
python scripts/run_triage_eval.py --dataset eval/datasets/triage_cases_v1.jsonl
```
