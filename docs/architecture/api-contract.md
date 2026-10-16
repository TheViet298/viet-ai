# API Contract Specification (Customer & Staff)

> **Người phụ trách chính:** Triển (Backend) - Việt
> **Cập nhật lần cuối:** 2026-10-11 (đồng bộ với Swagger `/docs` v1.2.0 — Session Lifecycle & Security Hardened)  
> **Trạng thái:** Approved & Implemented (Bảo vệ IDOR 404, Session Takeover Prevention, Quản lý Cuộc trò chuyện & Cascade Deletion)

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
    "timestamp": "2026-10-11T20:30:00Z"
  }
}
```
* **Bảo mật & Quyền riêng tư (Privacy Guardrail):**
  * Nhóm thiết kế theo chuẩn đề bài là **Không yêu cầu khách hàng nhập thông tin định danh cá nhân (PII) thật** (Họ tên, SĐT thật, CCCD, Biển số thật).
  * Sử dụng định danh phiên: `session_id` (UUID v4 ngẫu nhiên độ an toàn cao), `mock_customer_id` (mã khách hàng nội bộ do backend tự gán khi đăng ký, không phải dữ liệu thật), `vehicle_model`, `vehicle_code_mock`.
* **Quy tắc An toàn & Chống Dò Quét (Anti-Enumeration 404):**
  * Không trả về Chain-of-Thought (suy luận nội bộ của LLM) trong response của Customer API.
  * Mọi endpoint truy vấn/thao tác trên Chat Session (`/customer/sessions/*`) **bắt buộc trả về HTTP 404 Not Found** thay vì 403 Forbidden nếu session không tồn tại hoặc không thuộc quyền sở hữu của người gọi, ngăn ngừa hoàn toàn tấn công dò session hợp lệ.
* **RBAC & Guest Claim:**
  * Guest gọi được `/public/*`, `/customer/chat` và quản lý phiên của mình qua `guest_session_id` / header `X-Session-Id`.
  * Khi đăng nhập hoặc đăng ký tài khoản mới, client gửi `guest_session_id`. Backend thực thi gộp nguyên tử trong cùng 1 transaction: CHỈ gộp session có `owner == "guest:{id}"` sang `user:{user.id}`, loại bỏ hoàn toàn khả năng chiếm đoạt session (`Session Takeover`).

## 1.1. Auth, Public Content & Attachment APIs

| Endpoint | Mô tả |
| :--- | :--- |
| `POST /api/v1/auth/login` | Đăng nhập username/password, tự động gộp các phiên guest hợp lệ, trả token và `claimed_sessions` |
| `POST /api/v1/auth/register` | Đăng ký Customer mới, tự động gộp các phiên guest hợp lệ, trả token và `claimed_sessions` |
| `GET /api/v1/auth/me` | Xác thực bearer JWT, trả role/profile người dùng hiện tại |
| `PATCH /api/v1/auth/me` | Cập nhật thông tin hồ sơ người dùng (họ tên, SĐT, dòng xe) |
| `GET /api/v1/public/articles` | Landing/FAQ/Policy từ nguồn đã kiểm chứng |
| `POST /api/v1/customer/attachments` | Upload ảnh riêng tư, trả `attachment_id` |

### Auth request (kèm guest session claim)

```json
POST /api/v1/auth/login
{
  "username": "customer_demo_01",
  "password": "user-secure-password",
  "guest_session_id": "sess_vf_9f2b84cb-63df-4999-a419-5d26e1cb1db8"
}
```

Response trả về:
```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsIn...",
    "claimed_sessions": 1,
    "user": {
      "id": "usr-uuid-001",
      "username": "customer_demo_01",
      "role": "CUSTOMER"
    }
  },
  "error": null
}
```

---

## 1.2. Chat Session & Conversation Lifecycle APIs

Chuẩn hóa bộ endpoint quản lý lịch sử hội thoại cho Web UI Sidebar:

| Phương thức & Endpoint | Mô tả | Phân quyền & Bảo mật |
| :--- | :--- | :--- |
| `GET /api/v1/customer/sessions` | Lấy danh sách cuộc trò chuyện của User hoặc Guest | User: `owner == user:{id}`<br>Guest: `owner == guest:{guest_id}` |
| `GET /api/v1/customer/sessions/{session_id}/history` | Lấy toàn bộ lịch sử tin nhắn của phiên chat | Trả 404 nếu không khớp owner |
| `PATCH /api/v1/customer/sessions/{session_id}` | Đổi tên cuộc trò chuyện (tối đa 50 ký tự, bật `title_edited`) | Trả 404 nếu không khớp owner |
| `DELETE /api/v1/customer/sessions/{session_id}` | Xóa 1 cuộc trò chuyện và xóa triệt để `Message`, `ChatRequestRecord` | Trả 404 nếu không khớp owner |
| `DELETE /api/v1/customer/sessions` | Xóa toàn bộ lịch sử trò chuyện của tài khoản hiện tại | Xóa sạch messages và request records |

> **Lưu ý về Route Aliasing:** Đường dẫn cũ `/api/v1/customer/chat/sessions/*` được giữ làm **deprecated alias** (`deprecated=True, include_in_schema=False`) để bảo đảm backward compatibility và sẽ được loại bỏ ở các phiên bản tiếp theo.

### Cơ chế Auto-Title & Smart Caching
1. Khi hội thoại mới chỉ có lời chào ("xin chào", "chào em", v.v.), tiêu đề mặc định là `"Cuộc trò chuyện mới"` và **không bị đóng băng** vào cơ sở dữ liệu.
2. Khi người dùng gửi câu hỏi có nội dung thực đầu tiên ("Xe VF5 bảo hành bao lâu?"), tiêu đề được tự động trích xuất và lưu vào DB.
3. Khi người dùng đổi tên thủ công qua `PATCH`, cờ `title_edited: true` được ghi nhận qua `flag_modified` của SQLAlchemy, đảm bảo auto-title không bao giờ ghi đè lên tên người dùng đã đặt.

---

## 1.3. System & Case Endpoints khác

| Endpoint | Mô tả |
| :--- | :--- |
| `GET /health` | Health check (nằm ngoài prefix `/api/v1`) |
| `GET /api/v1/status` | Trạng thái AI Agent & Knowledge Base; frontend dùng để hiển thị chỉ báo trạng thái ở khung chat |
| `POST /api/v1/chat`, `POST /api/v1/public/chat` | Chat tương thích dùng `ChatRequest`/`ChatResponse` riêng (xem `src/api/routes.py`); frontend chính dùng `POST /customer/chat` |
| `POST /api/v1/agent/*`, `GET /api/v1/agent/*` | Bộ route song song dùng `session_store` thay vì DB; **không thuộc contract này** và frontend không gọi |
| `GET /api/v1/cases`, `GET /api/v1/cases/{case_id}` | Route cũ gắn tag `cases-legacy` trong Swagger |

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
  "attachment_ids": ["ATT-20260930-001"],
  "guest_session_id": "guest_abc", // dùng khi chưa login
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

### 2.3. Case của Customer
| Endpoint | Mô tả |
| :--- | :--- |
| `GET /api/v1/customer/cases` | Danh sách case của chính Customer |
| `GET /api/v1/customer/cases?query={query}&status={status}` | Tìm case của chính Customer theo Case ID/từ khóa/trạng thái |
| `GET /api/v1/customer/cases/{case_id}` | Case Detail: brief an toàn, timeline, Customer Update, attachment và lịch sử chat đã được ownership check |
| `POST /api/v1/customer/cases/{case_id}/reopen` | Mở lại case đã Resolved/Closed |
| `POST /api/v1/customer/cases/{case_id}/feedback` | Gửi hoặc cập nhật đánh giá CSAT sau xử lý (xem 2.4) |
| `POST /api/v1/customer/feedback` | Alias của endpoint trên, truyền `case_id` trong body |
| `POST /api/v1/customer/cases/{case_id}/confirmation` | Xác nhận đã được hỗ trợ hoặc mở lại case |
| `GET /api/v1/public/support-insights` | Thư viện tình huống thường gặp đã biên soạn/ẩn danh; không trả raw case của Customer |

### 2.4. Xác nhận, Mở lại, CSAT & Cảnh báo an toàn

**Xác nhận kết quả** — `POST /api/v1/customer/cases/{case_id}/confirmation` (cần đăng nhập Customer; case phải đang `Resolved`, nếu không trả `409`):
```json
{ "confirmation": "RESOLVED_CONFIRMED", "feedback_note": null }
```
`RESOLVED_CONFIRMED` $\rightarrow$ `Closed`; `STILL_UNRESOLVED` $\rightarrow$ `Reopened` (quay lại Staff Queue).

**Hành động của khách** — `POST /api/v1/customer/cases/{case_id}/actions` (đăng nhập Customer hoặc Guest qua `X-Session-Id`):
```json
{ "action": "CONFIRM_RESOLUTION", "reason": null, "feedback_note": null }
```
`action` là `CONFIRM_RESOLUTION` ($\rightarrow$ `Closed`) hoặc `REOPEN` ($\rightarrow$ `Reopened`). Response: `case_id`, `status`, `updated_at`, `customer_message`.

**Mở lại** — `POST /api/v1/customer/cases/{case_id}/reopen`: chỉ cho case `Resolved` hoặc `Closed` (trạng thái khác trả `400`); nếu case đã `Reopened` thì trả thành công (idempotent). Hệ thống ghi `staff_audit_logs` với `staff_id = CUSTOMER_<user_id>`.

**Đánh giá CSAT** — `POST /api/v1/customer/cases/{case_id}/feedback` (đăng nhập hoặc Guest qua `X-Session-Id`):
```json
{ "rating": 5, "comment": "Xử lý nhanh", "reason_tags": [] }
```
* `rating` từ 1 đến 5; `reason_tags` là các tag lý do nhanh, dùng khi đánh giá 1–2 sao.
* Chỉ gửi được khi case `Resolved` hoặc `Closed` (trạng thái khác trả `409`).
* Mỗi case chỉ có một đánh giá (`customer_feedback.case_id` UNIQUE); gửi lại sẽ cập nhật bản cũ, trong vòng 7 ngày kể từ lần gửi đầu (quá hạn trả `400`).
* Response: `feedback_id`, `case_id`, `rating`, `reason_tags`.

**Xác nhận an toàn** — `POST /api/v1/customer/cases/{case_id}/safety-acknowledgement`:
```json
{ "incident_version": 1 }
```
Chỉ áp dụng cho case `HIGH`/`CRITICAL` chưa `Resolved`/`Closed`. `incident_version` phải khớp phiên bản hiện tại, nếu không trả `409` để client tải lại. Thành công thì `safety_status` chuyển từ `unconfirmed` sang `customer_reported_safe`; xác nhận này **không** đóng hồ sơ.

**Lịch sử phiên** — `GET /api/v1/customer/sessions/{session_id}/history?guest_session_id=...`: trả `session_id`, `case_id` đang gắn với phiên, `messages[]` (kèm `response_type`, `citations`, `suggested_replies`, `safe_guidance`) và `total`. Phiên của user đăng nhập chỉ chính chủ xem được; phiên guest cần `guest_session_id` hoặc `X-Session-Id` khớp.

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

Mỗi item còn có thêm các trường: `issue_summary`, `suggested_action`, `has_location_consent`, `error_code_short`, `safety_status`, `safety_acknowledged_at`, `customer_feedback_score`, `customer_feedback_comment`, `customer_feedback_tags` và `is_auto_closed` (`true` khi case bị hệ thống tự đóng, xem mục 4).

---

### 3.1.1. Staff Dashboard, History & Routing Directory

| Endpoint | Mô tả |
| :--- | :--- |
| `GET /api/v1/staff/dashboard` | Counter: `critical_count`, `staff_reviewing_count`, `needs_information_count`, `resolved_today_count`, `total_cases_count` |
| `GET /api/v1/staff/tickets?status=Resolved,Closed,Reopened` | Lịch sử case, có filter intent/routing/staff/thời gian |
| `GET /api/v1/staff/routing-directory` | Danh sách bộ phận demo để Staff chọn khi Reroute |

Routing directory P0: `Charging Operations`, `Service Center`, `Customer Care`, `Sales Advisor`, `Emergency Support Demo`.

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
  "action": "APPROVE", // "APPROVE" | "EDIT_BRIEF" | "REROUTE" | "REQUEST_INFO" | "RESOLVE" | "CLOSE" | "REOPEN"
  "staff_id": "STAFF_007",
  "updated_status": "In Progress",
  "edited_brief": null, // Nếu action = EDIT_BRIEF thì gửi object brief đã sửa
  "notes": "Đã tiếp nhận yêu cầu và điều phối kỹ thuật viên kiểm tra trụ sạc."
}
```

Trạng thái mới của case được suy ra từ `action`; nếu client gửi `updated_status` thì giá trị này ghi đè trạng thái suy ra:

| `action` | Trạng thái sau thao tác | Ghi chú |
| :--- | :--- | :--- |
| `APPROVE` | `In Progress` | Tạo `case_updates` thông báo cho khách |
| `REROUTE` | `Staff Reviewing` | Điều phối lại; ghi vết vào audit log |
| `REQUEST_INFO` | `Needs Information` | Tạo `case_updates` yêu cầu khách bổ sung |
| `RESOLVE` | `Resolved` | Tạo `case_updates` với `awaiting_customer_confirmation = true`; `notes` là thông điệp gửi khách |
| `CLOSE` | `Closed` | |
| `REOPEN` | `Reopened` | |
| `EDIT_BRIEF` | Giữ nguyên | Cập nhật `summary`, `captured_fields`, `suggested_action` và đặt `is_edited_by_staff = true` |

Mọi thao tác ghi `staff_audit_logs` kèm `previous_state` và `new_state`.

---

## 4. Vòng đời sau xử lý & Tự động đóng

```
Resolved --(khách xác nhận)--> Closed --(CSAT 1-5 sao)
Resolved --(khách báo chưa xong / reopen)--> Reopened --> Staff Queue
Resolved --(quá 72 giờ không phản hồi)--> Closed (auto-close)
```

* Job nền (`src/services/case_lifecycle.py`, hằng số `AUTO_CLOSE_HOURS = 72`) quét mỗi 600 giây; hàm quét cũng được gọi mỗi lần Staff gọi `GET /staff/tickets`.
* Mỗi case bị tự đóng được ghi `staff_audit_logs` với `staff_id = SYSTEM_AUTO_CLOSE`, ghi chú bắt đầu bằng `[SYSTEM AUTO-CLOSE]`, và một `case_updates` có `author_type = SYSTEM`.
* Staff Console nhận biết case tự đóng qua `is_auto_closed = true` trong `GET /staff/tickets`.