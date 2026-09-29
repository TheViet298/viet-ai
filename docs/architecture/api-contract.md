# API Contract Specification (Customer & Staff)

> **Người phụ trách chính:** Triển (Backend Lead)  
> **Cập nhật lần cuối:** 2026-09-24  
> **Trạng thái:** In Review (Đã chuẩn hóa No-PII Schema, Distinct State Rules và Safe Guidance)

---

## 1. Chuẩn Quy ước Chung (General Conventions)

* **Base URL:** `/api/v1`
* **Content-Type:** `application/json; charset=utf-8`
* **Response Envelope Format:**
```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": {
    "timestamp": "2026-09-24T10:00:00Z"
  }
}
```
* **Bảo mật & Quyền riêng tư (Privacy Guardrail):**
  * Tuyệt đối không yêu cầu khách hàng nhập thông tin định danh cá nhân (PII) thật (Họ tên, SĐT thật, CCCD, Biển số thật).
  * Sử dụng định danh phiên: `session_id`, `mock_customer_id` (nếu có profile giả lập), `vehicle_model`, `vehicle_code_mock`.
* **Quy tắc An toàn:** Tuyệt đối không trả về Chain-of-Thought (suy luận nội bộ của LLM) trong response của Customer API.

---

## 2. Customer APIs

### 2.1. Gửi tin nhắn Chat & Triage
* **Endpoint:** `POST /api/v1/customer/chat`
* **Mô tả:** Tiếp nhận tin nhắn của khách hàng, thực hiện Triage, Clarification (tối đa 2 lượt) hoặc trả lời FAQ kèm nguồn.

#### Request Body:
```json
{
  "session_id": "sess_vf_98234",
  "case_id": "CASE-20260924-001", // null nếu là tin nhắn đầu tiên
  "message": "Xe VF8 của tôi không nhận sạc ở trạm Metropolis, trụ báo đèn đỏ.",
  "client_context": {
    "mock_customer_id": "CUST_MOCK_01",
    "vehicle_model": "VF8",
    "vehicle_code_mock": "VF-SF-00231"
  }
}
```

#### Response (Trường hợp Cần hỏi làm rõ - `Clarification` - Tối đa 2 lượt):
```json
{
  "success": true,
  "data": {
    "response_type": "CLARIFICATION",
    "clarification_turn": 1,
    "max_clarification_turns": 2,
    "message": "Dạ em ghi nhận xe VF8 đang không nhận sạc tại trạm Metropolis. Màn hình xe có hiển thị mã lỗi (ví dụ: CC01, BMS_012) hoặc anh/chị có mã trụ sạc không ạ?",
    "suggested_replies": [
      "Mã lỗi CC01, trụ P02",
      "Đèn trụ nháy đỏ, không hiện mã",
      "Không thấy mã lỗi"
    ],
    "case_id": null
  },
  "error": null
}
```

#### Response (Trường hợp FAQ có Trích dẫn Nguồn kiểm chứng):
```json
{
  "success": true,
  "data": {
    "response_type": "FAQ_ANSWER",
    "message": "Theo Hướng dẫn sử dụng Ứng dụng VinFast, anh/chị có thể theo dõi tình trạng pin, tiếp nhận thông báo cảnh báo và chủ động đặt lịch dịch vụ bảo dưỡng/kiểm tra xe trực tiếp trên ứng dụng.",
    "citations": [
      {
        "source_id": "SRC-APP-001",
        "title": "Hướng dẫn sử dụng Ứng dụng VinFast",
        "url": "https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast",
        "verified_at": "2026-09-24",
        "status_code": 200,
        "applicable_models": ["VF3", "VF5", "VF6", "VF7", "VF8", "VF9", "e34"],
        "source_type": "OFFICIAL_APP_GUIDE"
      }
    ],
    "service_handoff": {
      "has_app_feature": true,
      "app_feature_name": "Đặt lịch dịch vụ / Theo dõi xe",
      "guide_url": "https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast"
    },
    "case_id": null
  },
  "error": null
}
```

#### Response (Trường hợp Đủ dữ kiện $\rightarrow$ Tạo Case Brief thành công $\rightarrow$ Chuyển Staff Review):
```json
{
  "success": true,
  "data": {
    "response_type": "CASE_CREATED",
    "case_id": "CASE-20260924-001",
    "status": "Staff Reviewing",
    "priority": "HIGH",
    "message": "Hệ thống đã ghi nhận sự cố và tạo hồ sơ hỗ trợ. Thông tin sẽ được hiển thị cho nhân viên xử lý trên môi trường demo; vui lòng theo dõi cập nhật trên giao diện này.",
    "safe_guidance": "Anh/chị vui lòng giữ xe ở vị trí đỗ an toàn và theo dõi cập nhật trên giao diện này."
  },
  "error": null
}
```

#### Response (Trường hợp Sau 2 lượt vẫn thiếu dữ kiện $\rightarrow$ Tạo Case `Needs Information`):
```json
{
  "success": true,
  "data": {
    "response_type": "CASE_CREATED",
    "case_id": "CASE-20260924-003",
    "status": "Needs Information",
    "priority": "MEDIUM",
    "message": "Hệ thống đã tạo hồ sơ ghi nhận. Do chưa đủ một số dữ kiện kỹ thuật, hồ sơ được chuyển sang hàng đợi nhân viên hỗ trợ; nhân viên sẽ kiểm tra hoặc yêu cầu bổ sung thông tin.",
    "safe_guidance": "Vui lòng giữ kết nối và theo dõi cập nhật trên giao diện này."
  },
  "error": null
}
```

---

### 2.2. Tra cứu Trạng thái Case của Khách hàng
* **Endpoint:** `GET /api/v1/customer/cases/{case_id}/status`
* **Response Body:**
```json
{
  "success": true,
  "data": {
    "case_id": "CASE-20260924-001",
    "status": "In Progress",
    "status_description": "Chuyên viên kỹ thuật đang kiểm tra trạng thái kết nối trụ sạc từ xa.",
    "created_at": "2026-09-24T08:30:00Z",
    "updated_at": "2026-09-24T08:35:00Z"
  },
  "error": null
}
```

---

## 3. Staff APIs (Service Agent Console)

### 3.1. Lấy danh sách Ticket Queue
* **Endpoint:** `GET /api/v1/staff/tickets?status=Staff+Reviewing&priority=HIGH`
* **Response Body:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "CASE-20260924-001",
        "mock_customer_id": "CUST_MOCK_01",
        "vehicle_model": "VF8",
        "intent": "Charging/Battery",
        "priority": "HIGH",
        "status": "Staff Reviewing",
        "missing_info_flag": false,
        "created_at": "2026-09-24T08:30:00Z",
        "confidence_score": 0.92
      },
      {
        "id": "CASE-20260924-003",
        "mock_customer_id": "CUST_MOCK_02",
        "vehicle_model": "VF5",
        "intent": "Service/Incident",
        "priority": "MEDIUM",
        "status": "Needs Information",
        "missing_info_flag": true,
        "created_at": "2026-09-24T08:40:00Z",
        "confidence_score": 0.65
      }
    ],
    "total": 2
  },
  "error": null
}
```

---

### 3.2. Lấy Chi tiết Ticket & Case Brief
* **Endpoint:** `GET /api/v1/staff/tickets/{case_id}`
* **Response Body:**
```json
{
  "success": true,
  "data": {
    "case": {
      "id": "CASE-20260924-001",
      "mock_customer_id": "CUST_MOCK_01",
      "vehicle_code_mock": "VF-SF-00231",
      "vehicle_model": "VF8",
      "intent": "Charging/Battery",
      "priority": "HIGH",
      "status": "Staff Reviewing"
    },
    "case_brief": {
      "summary": "Xe VF8 không nhận sạc DC tại trạm Metropolis, màn hình báo lỗi CC01.",
      "captured_fields": {
        "vehicle_model": "VF8",
        "station_location": "Vincom Metropolis",
        "charger_id": "VN-CS-HN042-P02",
        "error_code": "CC01"
      },
      "suggested_action": "Kiểm tra tín hiệu giao tiếp trụ sạc P02 hoặc cử nhân viên trạm hỗ trợ khách hàng.",
      "confidence_score": 0.92,
      "is_edited_by_staff": false
    },
    "conversation_history": [
      { "sender": "CUSTOMER", "content": "Xe VF8 của tôi không nhận sạc...", "created_at": "..." },
      { "sender": "AGENT", "content": "Dạ em ghi nhận...", "created_at": "..." }
    ]
  },
  "error": null
}
```

---

### 3.3. Thực hiện Hành động Xử lý Ticket (HITL Action)
* **Endpoint:** `POST /api/v1/staff/tickets/{case_id}/actions`
#### Request Body:
```json
{
  "action": "APPROVE", // "APPROVE" | "EDIT_BRIEF" | "REROUTE" | "CLOSE" | "REOPEN" | "REQUEST_INFO"
  "staff_id": "STAFF_007",
  "updated_status": "In Progress",
  "edited_brief": null, // Nếu action = EDIT_BRIEF thì gửi object brief đã sửa
  "notes": "Đã tiếp nhận yêu cầu và điều phối kỹ thuật viên kiểm tra trụ sạc."
}
```
