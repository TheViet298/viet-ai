# Note Data cho MVP 1
> **Mục tiêu:** Chuẩn bị dữ liệu để Agent phân loại yêu cầu đúng, trả lời FAQ có nguồn và tạo Case Brief có cấu trúc ( Không dùng nhóm dữ liệu này để fine-tune hay train model)

---

## 1. Nhóm dữ liệu và vai trò mà nhóm sử dụng

| Nhóm dữ liệu | Mục đích | Không dùng cho |
|---|---|---|
| **A. Knowledge Base RAG** | Tra cứu thông tin VinFast công khai để trả lời FAQ có citation | Train/fine-tune LLM, suy đoán lỗi kỹ thuật không có nguồn |
| **B. Triage & Evaluation Dataset** | Kiểm thử Intent, Priority, Routing, Missing Fields, HITL; có thể dùng một phần làm few-shot prompt | Làm nguồn trả lời chính sách/kỹ thuật cho khách |

```text
Tài liệu VinFast công khai → Chunk + Embedding → ChromaDB → RAG Answer + Citation

Case mô phỏng có gán nhãn → Agent test/evaluation → Metric → sửa rule/prompt
```

---

## 2. Nhóm A — Knowledge Base cho RAG

### 2.1. Phạm vi crawl MVP

Nhóm chỉ thu thập tài liệu công khai và chính thức, đúng với 3 demo flow:

1. Hướng dẫn ứng dụng VinFast: trạng thái xe, pin/sạc, cảnh báo, dịch vụ.
2. Chính sách bảo hành công khai.
3. Hướng dẫn bảo dưỡng, sửa chữa, cứu hộ công khai.
4. Sổ tay/hướng dẫn của 1–2 dòng xe demo, ưu tiên VF5/VF8 nếu có nguồn phù hợp.

> Note: Không dùng bài diễn đàn/Facebook làm nguồn trả lời chính thức. Nội dung diễn đàn chỉ có thể gợi ý cách viết case mô phỏng.

### 2.2. Pipeline xử lý

```text
Official URL
→ xác minh URL và phạm vi tài liệu
→ download/crawl raw file
→ extract text + clean text
→ chunk 500 ký tự, overlap 80 ký tự
→ gắn metadata
→ embedding + ChromaDB
→ retrieval + citation / NO_SOURCE fallback
```

### 2.3. Metadata bắt buộc cho mỗi chunk

```json
{
  "source_id": "SRC-001",
  "chunk_id": "SRC-001-014",
  "title": "Hướng dẫn sử dụng ứng dụng VinFast",
  "url": "https://vinfastauto.com/...",
  "source_type": "official_guide",
  "verified_at": "2026-09-28",
  "applicable_models": ["VF 5", "VF 8"],
  "section": "Pin và sạc",
  "content": "..."
}
```

### 2.4. Rule RAG bắt buộc

```text
Có source phù hợp + citation hợp lệ → FAQ_ANSWER.
Không có source / retrieval dưới ngưỡng → NO_SOURCE.
NO_SOURCE → không suy đoán, tạo hoặc đề xuất tạo Case để Staff Review.
```

> Note: Không đưa hướng dẫn thao tác kỹ thuật, an toàn hoặc sửa xe vào câu trả lời nếu chưa có nguồn chính thức kiểm chứng.

### 2.5. Output cần bàn giao

```text
docs/data-sources.md                 Danh sách URL, trạng thái xác minh, ngày kiểm chứng
data/raw/                            File crawl gốc, local-only, không commit nếu nặng
data/processed/chunks.jsonl          Chunk + metadata, local-only hoặc bản mẫu nhỏ
scripts/ingest_knowledge_base.py     Script ingest tái lập được
data/chroma/                         Vector store local-only
```

---

## 3. Nhóm B — Dataset Triage & Evaluation

### 3.1. Mục tiêu

Dataset này mô phỏng các câu khách có thể nói để đánh giá Agent. Mỗi case phải có expected output rõ ràng để đo được chất lượng. Tất cả case nhóm đều dùng dữ liệu giả lập; không dùng VIN, biển số, số điện thoại, email, địa chỉ/GPS thật hoặc raw survey response.

### 3.2. Phân bổ case MVP

| Intent / Nhóm case | Số case gợi ý | Mức triển khai |
|---|---:|---|
| `charging_battery` | 15–20 | Làm sâu: clarify, priority, Case Brief, routing |
| `service_incident` | 15–20 | Làm sâu: safety, clarify, Case Brief, routing |
| `sales_general_info` | 5–8 | Triage + FAQ RAG / NO_SOURCE fallback |
| `complaint_feedback` | 5–8 | Triage + brief tối thiểu + bắt buộc HITL |
| Safety / adversarial / out-of-scope | 8–10 | Critical rule, spam, mơ hồ, yêu cầu ngoài phạm vi |

Mục tiêu ban đầu: **40 case có chất lượng**. Mở rộng lên 50–60 case khi core flow đã chạy.

### 3.3. Schema tối thiểu

```json
{
  "id": "TRIAGE-001",
  "split": "test",
  "input": "Xe VF 8 không nhận sạc tại trạm, đèn trụ báo đỏ.",
  "expected_intent": "charging_battery",
  "expected_priority": "high",
  "expected_missing_fields": ["charger_id", "error_message"],
  "expected_response_type": "clarification",
  "expected_routing": "charging_support",
  "expected_staff_review": true,
  "expected_safety_trigger": false,
  "rationale": "Sự cố sạc cần lấy thêm mã trụ và cảnh báo trước khi bàn giao."
}
```

### 3.4. Tách dataset để tránh leakage

```text
triage_train_v1.jsonl   Chỉ dùng nếu cần few-shot prompt
triage_dev_v1.jsonl     Dùng trong quá trình sửa prompt/rule
triage_test_v1.jsonl    Không đưa vào prompt; chỉ dùng đánh giá cuối
rag_test_v1.jsonl       Câu FAQ có expected citation hoặc expected NO_SOURCE
```

### 3.5. Quy tắc label

1. Mỗi case có đúng một `expected_intent` chính; ghi lý do nếu case dễ nhầm.
2. `critical` chỉ dùng khi có tín hiệu nguy hiểm rõ ràng, không gán chỉ vì có cụm “rùa vàng”.
3. Case `charging_battery`, `service_incident`, `complaint_feedback`, priority `high/critical`, low-confidence hoặc tài chính phải có `expected_staff_review: true`.
4. Case FAQ không có nguồn chính thức phải có `expected_response_type: "no_source"`, không ép Agent bịa câu trả lời.
5. Mỗi case cần có ngôn ngữ tự nhiên, gồm cả câu ngắn, thiếu dữ kiện, lỗi chính tả nhẹ và mô tả dài.

---

## 4. Evaluation Metrics

```text
Intent Accuracy       = số case có intent đúng / tổng case
Critical Recall       = số case Critical được phát hiện / tổng case Critical
Routing Accuracy      = số case routing đúng / tổng case có expected routing
Brief Completeness    = số required fields thu được / tổng required fields
RAG Grounded Rate     = số FAQ trả lời có citation hợp lệ / tổng FAQ trả lời
No-source Compliance  = số case thiếu nguồn được fallback đúng / tổng case thiếu nguồn
```

> Note: Không báo cáo các tỷ lệ này là kết quả cho đến khi script eval chạy trên `triage_test_v1.jsonl` và lưu evidence vào `eval/results/`.

## 5. Thứ tự thực hiện

```text
1. Khôi xác minh 3–5 URL nguồn chính thức.
2. Long + Khôi chốt schema label và tạo 10 case mẫu.
3. Việt review ngôn ngữ/pain point; Triển seed 3 case Flow 1.
4. Hoàn thành Vertical Slice Charging/Battery.
5. Mở rộng dataset lên 40 case và chạy evaluation.
6. Bổ sung Service/Incident, Critical, FAQ RAG sau khi Flow 1 ổn định.
```

## 6. Scope

```text
4 intent đều phải có dataset để Agent định tuyến đúng.
Charging/Battery và Service/Incident mới có workflow sâu.
RAG là kho tri thức để truy xuất, không phải dữ liệu để train model.
MVP chỉ dùng LLM + prompt + rule + RAG + evaluation dataset; chưa fine-tune.
```
