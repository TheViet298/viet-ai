# Báo Cáo Triển Khai Hoàn Thành: API Contract Kết Nối Backend & Frontend (AI Chatbot)

* **Ngày thực hiện:** 2026-09-30
* **Người thực hiện:** AI / RAG Engineer
* **Tài liệu tham chiếu:** [`docs/architecture/api-contract.md`](file:///d:/142.AI20K/P-142/docs/architecture/api-contract.md) & [`docs/data-workplan-mvp.md`](file:///d:/142.AI20K/P-142/docs/data-workplan-mvp.md)
* **Trạng thái:** **Đã hoàn thành 100% & Đạt toàn bộ 30/30 unit tests (`pytest`)**

---

## 1. Mục Đích & Bối Cảnh Thực Hiện

Để đội ngũ phát triển Frontend (Giao diện người dùng) và Backend (Dịch vụ máy chủ/Database) có thể kết nối ngay lập tức với "Hạt nhân AI Chatbot" mà không gặp lỗi xung đột kiểu dữ liệu hoặc thiếu trường dữ liệu, module AI đã được đóng gói thành các API Endpoint chuẩn RESTful JSON kèm bản đặc tả hợp đồng dữ liệu (API Contract).

Hệ thống hỗ trợ đồng thời cả 2 phương thức kết nối:
1. **Endpoint Rút gọn (`POST /api/v1/chat`)**: Dạng phản hồi phẳng, tối giản, cực kỳ thuận tiện cho bạn Frontend dựng nhanh giao diện demo trực tiếp.
2. **Endpoint Chính thức theo Chuẩn Kiến trúc (`POST /api/v1/customer/chat`)**: Định dạng Response Envelope chuẩn (`success`, `data`, `error`, `meta`) theo đúng quy định tại [`docs/architecture/api-contract.md`](file:///d:/142.AI20K/P-142/docs/architecture/api-contract.md).

---

## 2. Chi Tiết Các File Đã Tạo Mới & Chỉnh Sửa

> **Cam kết**: Tuyệt đối không xoá bất kỳ file nào trong hệ thống; toàn bộ dữ liệu raw, processed chunks, vector store ChromaDB và các bài kiểm thử trước đó đều được bảo toàn nguyên vẹn.

### A. Các File Tạo Mới:
| STT | Tên File | Thư mục Lưu Trữ | Vai Trò & Chức Năng |
| :---: | :--- | :--- | :--- |
| 1 | `rag_service.py` | `src/services/` | Kết nối ChromaDB tại `data/chroma`, truy vấn vector tri thức và thực thi **Rule 2.4 / ADR-003** (ngưỡng tương đồng 0.70). |
| 2 | `chatbot_agent.py` | `src/agents/` | "Hạt nhân AI" tổng hợp: Chạy Hard Safety Guardrails $\rightarrow$ PII Sanitizer $\rightarrow$ RAG Retrieval $\rightarrow$ Grounded Answer Synthesis kèm Citation URL $\rightarrow$ Đánh giá cờ Staff Review (HITL). Hỗ trợ cả online (khi có LLM key) và offline fallback trích xuất thông minh. |
| 3 | `test_chatbot_demo.py` | `scripts/` | Script chạy thử nghiệm độc lập 4 kịch bản hội thoại thực tế (Bảo hành, Bốc khói khẩn cấp, Đặt lịch App, và Hỏi ngoài phạm vi). |
| 4 | `create_api_contract.md` | `docs/` | Báo cáo chi tiết này. |

### B. Các File Được Chỉnh Sửa:
| STT | Tên File | Thư mục Lưu Trữ | Nội Dung Chỉnh Sửa |
| :---: | :--- | :--- | :--- |
| 1 | `schemas.py` | `src/models/` | Bổ sung các trường phân loại vào `ChatResponse` (`intent`, `priority`, `needs_staff_review`, `is_safety_trigger`, `citations`) và định nghĩa thêm `CustomerChatRequest`, `ApiResponseEnvelope` chuẩn Envelope. |
| 2 | `routes.py` | `src/api/` | Kết nối trực tiếp hàm `process_chat_message` vào `POST /api/v1/chat` và bổ sung mới endpoint `POST /api/v1/customer/chat` cùng `GET /api/v1/status`. |
| 3 | `test_routes.py` | `tests/test_api/` | Mở rộng bộ kiểm thử API từ 3 tests lên 6 tests, bao quát kiểm tra endpoint chat thường, endpoint envelope contract, kiểm tra an toàn khẩn cấp và mã lỗi validation 422. |

---

## 3. Đặc Tả Chi Tiết API Contract (Dành Cho Backend & Frontend)

* **Base URL:** `http://localhost:8000/api/v1`
* **Format:** `application/json; charset=utf-8`

### 3.1. Endpoint Khách Hàng Chuẩn Envelope: `POST /customer/chat`
* **URL:** `/api/v1/customer/chat`
* **Method:** `POST`

#### Request Body:
```json
{
  "session_id": "sess_demo_001",
  "case_id": null,
  "message": "Thời hạn bảo hành pin xe VinFast VF 8 là bao lâu?",
  "attachment_ids": [],
  "client_context": {
    "vehicle_model": "VF 8"
  }
}
```

#### Response Body (`200 OK`):
```json
{
  "success": true,
  "data": {
    "response_type": "FAQ_ANSWER",
    "message": "Dạ theo thông tin chính thức từ **Chính sách bảo hành xe ô tô VinFast** (Mục: *Tổng quan*):\n\nThời hạn bảo hành pin xe VinFast VF 8 mua mới theo xe là **10 năm hoặc 200.000 km** tùy điều kiện nào đến trước.\n\n📎 **Nguồn tài liệu chính thức:** [Chính sách bảo hành xe ô tô VinFast](https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-oto)",
    "intent": "charging_battery",
    "priority": "medium",
    "is_safety_trigger": false,
    "needs_staff_review": false,
    "citations": [
      {
        "source_id": "SRC-002",
        "title": "Chính sách bảo hành xe ô tô VinFast",
        "url": "https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-oto",
        "section": "Tổng quan",
        "distance": 0.6523
      }
    ],
    "case_id": null,
    "session_id": "sess_demo_001"
  },
  "error": null,
  "meta": {
    "timestamp": "2026-09-30T19:45:00.000000Z"
  }
}
```

### 3.2. Endpoint Rút Gọn Phục Vụ Demo Trực Tiếp: `POST /chat`
* **URL:** `/api/v1/chat`
* **Method:** `POST`

#### Request Body:
```json
{
  "message": "Thời hạn bảo hành pin xe VinFast VF 8 là bao lâu?"
}
```

#### Response Body (`200 OK`):
```json
{
  "response": "Nội dung câu trả lời của Bot kèm định dạng Markdown và link trích dẫn...",
  "analysis": "Intent: charging_battery | Priority: medium | Needs Review: False | Citations: 1",
  "intent": "charging_battery",
  "priority": "medium",
  "needs_staff_review": false,
  "is_safety_trigger": false,
  "citations": [
    {
      "source_id": "SRC-002",
      "title": "Chính sách bảo hành xe ô tô VinFast",
      "url": "https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-oto",
      "section": "Tổng quan"
    }
  ]
}
```

### 3.3. Các Trạng Thái Phản Hồi Đặc Biệt Của AI Agent

1. **Phát Hiện Nguy Cơ An Toàn Khẩn Cấp (`is_safety_trigger: true`)**:
   - Khi tin nhắn chứa tín hiệu cháy, bốc khói, mất phanh khẩn cấp trên đường.
   - `response_type`: `"SAFETY_ALERT"`, `priority`: `"critical"`, `needs_staff_review`: `true`.
   - Bot ngay lập tức trả hướng dẫn tấp xe vào lề, bật hazard, sơ tán và cấp hotline cứu hộ `1900-232389` (24/7).
   - Frontend hiển thị: Banner viền đỏ nhấp nháy hoặc nút gọi khẩn cấp.

2. **Câu Hỏi Thiếu Nguồn / Ngoài Phạm Vi (Rule 2.4 Fallback)**:
   - Khi khoảng cách vector $> 0.70$ hoặc không tìm thấy bài viết xác thực.
   - `response_type`: `"NO_SOURCE"`, `citations`: `[]`, `needs_staff_review`: `true`.
   - Bot tuyệt đối không suy đoán hay bịa đặt, thông báo rõ ràng và tự động chuyển câu hỏi vào hàng đợi Staff Review của nhân viên.

3. **Kiểm Tra Trạng Thái Sẵn Sàng: `GET /api/v1/status`**:
   - Trả về: `{"status": "ready", "agent": "VinFast RAG Chatbot Agent v1.0", "knowledge_base": "vinfast_knowledge_base"}`.

---

## 4. Bằng Chứng Kiểm Định & Kết Quả Chạy Thực Tế

Toàn bộ hệ sinh thái kiểm thử tự động của dự án P-142 đã được thực thi bằng Python Virtualenv (`.venv`):

```bash
d:\142.AI20K\P-142\.venv\Scripts\pytest.exe
```

**Kết quả kiểm thử:**
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\142.AI20K\P-142
collected 30 items

tests\test_agents\test_graph.py ..                                       [  6%]
tests\test_agents\test_guardrails.py ...................                 [ 70%]
tests\test_api\test_routes.py ......                                     [ 90%]
tests\test_eval\test_benchmark_dataset.py ...                            [100%]

======================= 30 passed, 2 warnings in 4.60s ========================
```

---

## 5. Hướng Dẫn Khởi Chạy Cho Đội Ngũ Phát Triển

1. **Khởi động Backend API Server**:
   ```bash
   cd d:\142.AI20K\P-142
   .\.venv\Scripts\python.exe -m uvicorn src.main:app --reload --port 8000
   ```
2. **Kiểm tra trực quan bằng Swagger UI**:
   Mở trình duyệt truy cập: **`http://localhost:8000/docs`**
   - Chọn `POST /api/v1/chat` hoặc `POST /api/v1/customer/chat`.
   - Nhấn **Try it out** và gửi các câu hỏi mẫu để kiểm tra dữ liệu trả về ngay lập tức.
