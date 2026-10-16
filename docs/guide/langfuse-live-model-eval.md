# Tự xem 10 ca gọi model trên Langfuse

Bộ dữ liệu: `eval/datasets/live_model_cases_v1.jsonl`. Có 6 ca hội thoại và 4 ca nhận diện ảnh; tách khỏi bộ golden 60 ca. Model dùng cấu hình hiện tại của hệ thống. Không dùng mock provider hoặc fault injection.

Ảnh mẫu đã có sẵn để xem trước: [LIVE-07 — áp suất thấp](../../eval/datasets/live_model_images_v1/LIVE-07.png), [LIVE-08 — lỗi cảm biến](../../eval/datasets/live_model_images_v1/LIVE-08.png), [LIVE-09 — xe mô phỏng](../../eval/datasets/live_model_images_v1/LIVE-09.png), [LIVE-10 — không có xe](../../eval/datasets/live_model_images_v1/LIVE-10.png).

Trạng thái lúc chuẩn bị ngày 2026-10-14: bộ ca và kiểm tra offline đã hoàn tất; lượt Cloud mới chưa chạy vì DNS máy thực thi không phân giải được `cloud.langfuse.com` (11001). Chưa có trace `p142.live.LIVE-*` từ lượt này. Các bước dưới đây áp dụng sau khi kết nối hoạt động và runner hoàn tất.

## 1. Chạy bộ test

Mở PowerShell tại thư mục gốc dự án:

```powershell
.\.venv\Scripts\python.exe scripts/run_live_model_eval.py --run
```

Runner đọc `.env`, kiểm tra Langfuse, tạo database test riêng rồi gọi API thật của app. Sáu câu hỏi được gửi tới provider chat, bốn PNG tổng hợp được gửi tới provider vision. Không cần đưa khóa lên trình duyệt. Không in hoặc chia sẻ nội dung `.env`.

Cuối lệnh có `output` là thư mục kết quả và `run_id` dạng `p142-live-models-...`. Mở `report.md` trong thư mục đó: mỗi ca có link **Mở trace**, kết quả, latency, token và chi phí. `metrics.md` có trung bình/P50/P95/max; `case-metrics.csv` có số liệu từng ca. Mỗi lần chạy tạo lượt mới và phát sinh usage provider.

Nếu preflight báo `transport_error`, lượt model chưa bắt đầu. Kiểm tra kết nối mạng tới Langfuse rồi chạy lại. Nếu đã thấy dòng `LIVE-xx` thì có thể đã phát sinh lượt model; xem `results.json` trước khi quyết định chạy lại toàn bộ.

## 2. Tìm ca trong giao diện

1. Mở [Tracing của project](https://cloud.langfuse.com/project/cmuzofl6c02a5ad0ixpvdmca1/traces).
2. Chọn khoảng thời gian phía trên là **Past 1 day**, rồi bấm **Refresh**.
3. Ô **Search** nhập `env:p142-live-models` và Enter. Có thể dùng **Show filters** để chọn Environment `p142-live-models`.
4. Tìm các root tên `p142.live.LIVE-01` đến `p142.live.LIVE-10`. Các dòng `LangGraph`, `general`, `vision.dashboard`… là observation con của cùng trace, không phải testcase riêng.
5. Nếu có nhiều lần chạy, mở root và đối chiếu `metadata.run_id` với run ID trong báo cáo. Link trực tiếp trong `report.md` là cách nhanh nhất để mở đúng lượt.

## 3. Bật cột cần xem

Ở góc phải bảng, mở **Columns**. Bật:

- **Latency (S)**.
- **Cost ($)**.
- **Provided Model Name**.
- Mở nhóm **Usage** rồi bật **Input Tokens**, **Output Tokens**, **Total Tokens**.

Đây là đúng tên cột trong giao diện project đang dùng. Muốn so chi phí model, chọn dòng **GENERATION** hoặc lọc Type thành GENERATION. Span cha/con có thể hiển thị số tổng hợp; không cộng token/cost của mọi dòng trong cây vì sẽ dễ tính trùng. Chi phí rất nhỏ có thể được UI làm tròn thành `$0.00`; dùng JSON/CSV để xem đủ chữ số.

## 4. Đọc một ca hội thoại

Mở `LIVE-01` đến `LIVE-06`:

1. Chọn root `p142.live.LIVE-xx`. **Input** chứa câu hỏi; **Output** chứa response API của app.
2. Mở cây observation, tìm node generation của model chat. Xem **Provided Model Name**, **Usage**, **Cost** và thời gian xử lý.
3. Tìm `llm.outcome`, kiểm tra `outcome = parsed`: provider trả dữ liệu và app đã đọc được kết quả.
4. Xem score `live_model_pass`: 1 là đạt hợp đồng tích hợp của ca; 0 là chưa đạt. Score `agent_latency_s` là thời gian API của riêng ca, không gồm thời gian gửi/đọc Cloud.

HTTP 200 hoặc câu trả lời fallback không đủ chứng minh đã gọi model. Runner chỉ tính thành công khi có generation hoàn tất, usage thực và bằng chứng parse của app. Đây chưa phải đánh giá toàn diện chất lượng nội dung bằng LLM-as-judge.

## 5. Đọc một ca nhận diện ảnh

| Ca | Ảnh đầu vào | Kiểm tra |
| --- | --- | --- |
| LIVE-07 | Táp-lô mô phỏng có chữ `Tire pressure low` | OCR và nhãn `low_pressure` |
| LIVE-08 | Táp-lô mô phỏng có chữ `Tire pressure sensor fault` | Phân biệt nhãn `sensor_fault` |
| LIVE-09 | Hình xe tổng hợp không có dấu hiệu xác thực dòng xe | Không tự khẳng định model VinFast; cần người dùng xác nhận |
| LIVE-10 | Hình tổng hợp không có xe | Không bịa dòng xe từ ảnh âm tính |

Mở PNG tương ứng trong thư mục kết quả để xem ảnh gốc. Trên Langfuse, mở root trace và tìm:

- `Output → data → analysis_status`: kỳ vọng `ANALYZED`.
- `Output → data → detected_signals → ocr_text` và `symptom_keys` cho ảnh táp-lô.
- `Output → data → detected_signals → vehicle_evidence` cho ảnh ngoại thất; đọc `status`, `model_label`, `requires_user_confirmation`.
- Generation **vision.dashboard** hoặc **vision.exterior**: kiểm tra model, token, cost và trạng thái hoàn tất.

Ảnh raw/base64 không được lưu trong telemetry Langfuse của hệ thống. Vì vậy không thấy ảnh trong generation không đồng nghĩa model chưa nhận ảnh; PNG local và generation/response là bằng chứng đi kèm. Ảnh tổng hợp chỉ kiểm tra luồng tích hợp và một số hành vi có kiểm soát, không chứng minh độ chính xác nhận diện ảnh xe thật.

## 6. Khi không thấy số liệu

- Kiểm tra khoảng thời gian, Environment và run ID trước.
- Span thông thường không có usage model: mở generation con.
- Usage hoặc cost trống là thiếu dữ liệu, không mặc định là 0.
- UI có thể hiển thị banner dữ liệu trễ với SDK cũ. Dùng **Refresh**, hoặc mở đúng trace từ báo cáo; runner còn đọc bằng chứng qua API Cloud hiện hành.
- Nếu ca là `BLOCKED`, đọc `reasons` trong `results.json`: có thể provider lỗi, không có generation thành công hoặc app không parse được. Không đổi nhãn thành PASS chỉ vì HTTP 200.
