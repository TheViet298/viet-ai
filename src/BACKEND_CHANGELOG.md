# 📘 VinFast ServiceFlow AI - Backend Changelog & Architecture Guide (`src/`)

Tài liệu này ghi nhận toàn bộ quá trình chuẩn hóa Backend, cơ sở dữ liệu SQLite, hệ thống Migration Alembic và bộ API theo đúng **Nguồn Chân Lý (Single Source of Truth - Cập nhật 2026-09-24)** tại thư mục `docs/`.

---

## 📍 Vị trí tài liệu
File được đặt trực tiếp tại: **`src/BACKEND_CHANGELOG.md`**

---

## 1. Tổng quan các thay đổi chuẩn hóa (2026-09-29)

Sau khi rà soát và đối chiếu toàn diện giữa mã nguồn hiện tại trong `src/` và tài liệu thiết kế đặc tả (`data-model.md`, `api-contract.md`, `triage-and-hitl-rules.md`, `ADR-002`, `ADR-003`, `demo-scenarios.md`), Backend đã được tái cấu trúc và đồng bộ 100%:

| Thành phần | Trước khi chuẩn hóa | Sau khi chuẩn hóa (Đúng đặc tả Docs) |
| :--- | :--- | :--- |
| **Cấu trúc Bảng DB** | 4 bảng nháp (`cases`, `messages`, `reviewer_feedback`, `tickets`) | **4 bảng chuẩn:** `cases`, `messages`, `case_briefs`, `staff_audit_logs` |
| **Định dạng ID Case** | Số nguyên tự tăng (`Integer`) | **Chuỗi chuẩn hóa:** `CASE-YYYYMMDD-XXX` (vd: `CASE-20260924-001`) |
| **Vòng đời Ticket** | Thiếu đồng nhất, lẫn lộn `ROUTED`, `WAITING_REVIEW` | **7 trạng thái chuẩn:** `New` → `Needs Information` → `Staff Reviewing` → `In Progress` → `Resolved` → `Closed` (& `Reopened`) |
| **Quy tắc No-PII (ADR-003)** | Dùng chung chung `customer_ref`, thiếu mã xe mock | **Tuyệt đối không lưu PII:** chỉ lưu `mock_customer_id`, `vehicle_code_mock` (`VF-SF-xxxxx`), `session_id` |
| **Mức độ ưu tiên** | Viết thường/hoa lẫn lộn | **Chuẩn hóa chữ HOA:** `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| **Tóm tắt sự cố** | Lưu JSON thô trong cột `brief_data` | **Bảng riêng `case_briefs`:** 1-1 với `cases`, gồm `summary`, `captured_fields` (JSON), `suggested_action`, `confidence_score`, `is_edited_by_staff` |
| **Audit Log HITL** | Bảng `reviewer_feedback` | **Bảng chuẩn `staff_audit_logs`:** ghi nhận `previous_state`, `new_state`, `action`, `notes`, `staff_id` |
| **Response Envelope** | Một số endpoint trả JSON phẳng | **Bắt buộc 100% envelope:** `{ "success": bool, "data": T, "error": null, "meta": { "timestamp": string } }` |
| **Alembic Migration** | Bị thất lạc khi xóa folder `backend/` cũ | **Đã khôi phục & tạo revision mới:** `84802fff010b_align_spec_schema.py` từ `c9952f7d6ac7` |
| **Seed Data** | Dữ liệu mock tùy ý | **Chuẩn hóa 4 kịch bản Demo** từ `docs/product/demo-scenarios.md` (`CASE-20260924-001` đến `004`) |

---

## 2. Bản đồ cấu trúc thư mục Backend

```text
E:\P-142\
├── alembic.ini                   # Cấu hình Migration Alembic trỏ vào migrations/ và data/app.db
├── migrations/                   # Hệ thống Alembic Database Migrations
│   ├── env.py                   # Cấu hình SQLAlchemy metadata & render_as_batch=True cho SQLite
│   ├── script.py.mako           # Template sinh mã migration
│   └── versions/
│       ├── c9952f7d6ac7_init_schema.py         # Migration khởi tạo cũ (base)
│       └── 84802fff010b_align_spec_schema.py   # Revision mới: chuyển đổi sang 4 bảng chuẩn hóa
├── data/
│   └── app.db                   # Database SQLite chính thức của dự án
├── src/
│   ├── main.py                  # FastAPI app, CORS, lifespan đảm bảo DB schema
│   ├── config.py                # Pydantic Settings
│   ├── db.py                    # SQLite engine, enable foreign keys, SessionLocal
│   ├── seed.py                  # Script nạp 4 kịch bản demo chuẩn hóa
│   ├── BACKEND_CHANGELOG.md     # Tài liệu kiến trúc và hướng dẫn này
│   ├── models/
│   │   ├── db_models.py         # SQLAlchemy ORM (Case, Message, CaseBrief, StaffAuditLog)
│   │   └── schemas.py           # Pydantic models với ApiResponse envelope
│   ├── api/
│   │   ├── customer.py          # Customer API: /customer/chat, /cases/{id}/status
│   │   ├── staff.py             # Staff Console API: /staff/tickets, /actions
│   │   ├── cases.py             # Cases API tương thích ngược
│   │   └── routes.py            # API cơ bản của template (/chat, /status)
│   ├── agents/                  # AI LangGraph Agent (giữ nguyên không đổi)
│   └── services/                # Các dịch vụ phụ trợ
└── tests/
    ├── conftest.py              # Test fixtures (async client, mock LLM)
    ├── test_agents/             # Kiểm tra LangGraph flow
    └── test_api/
        ├── test_routes.py       # Kiểm tra các routes cơ bản
        └── test_aligned_spec.py # [MỚI] Kiểm tra toàn diện API theo đúng chuẩn docs/
```

---

## 3. Chi tiết Database Schema (4 Bảng chuẩn hóa)

### 3.1. Bảng `cases` (Hồ sơ sự cố / yêu cầu)
* `id` (`VARCHAR(32)`, PK): Mã dạng `CASE-YYYYMMDD-XXX` (vd: `CASE-20260924-001`).
* `session_id` (`VARCHAR(64)`, indexed): Mã phiên chat khách hàng.
* `mock_customer_id` (`VARCHAR(50)`, nullable): Mã định danh khách hàng mock (vd: `CUST_MOCK_01`).
* `mock_customer_name` (`VARCHAR(100)`, nullable): Tên khách hàng mock (chỉ dùng cho kịch bản demo).
* `mock_customer_phone` (`VARCHAR(20)`, nullable): SĐT mock (chỉ dùng cho kịch bản demo).
* `vehicle_code_mock` (`VARCHAR(50)`, nullable): Mã xe nội bộ mock dạng `VF-SF-xxxxx` (vd: `VF-SF-00231`).
* `vehicle_model` (`VARCHAR(50)`, nullable): Dòng xe VinFast (`VF3`, `VF5`, `VF6`, `VF7`, `VF8`, `VF9`, `e34`).
* `intent` (`VARCHAR(50)`): `Charging/Battery`, `Service/Incident`, `Sales/General Info`, `Complaint/Feedback`.
* `priority` (`VARCHAR(20)`): `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
* `status` (`VARCHAR(30)`): `New`, `Needs Information`, `Staff Reviewing`, `In Progress`, `Resolved`, `Closed`, `Reopened`.
* `assigned_staff_id` (`VARCHAR(50)`, nullable): ID nhân viên tiếp nhận.
* `created_at`, `updated_at`: `DATETIME` UTC có timezone.

### 3.2. Bảng `messages` (Lịch sử hội thoại)
* `id` (`VARCHAR(36)`, PK): UUID string.
* `case_id` (`VARCHAR(32)`, FK `cases.id`, nullable, indexed): Liên kết với hồ sơ sự cố.
* `session_id` (`VARCHAR(64)`, indexed): Mã phiên chat.
* `sender_type` (`VARCHAR(20)`): `CUSTOMER`, `AGENT`, `STAFF`, `SYSTEM`.
* `content` (`TEXT`): Nội dung tin nhắn.
* `metadata` (`JSON`, nullable): Chứa citations, quick replies, safe guidance...
* `created_at`: `DATETIME` UTC.

### 3.3. Bảng `case_briefs` (Tóm tắt sự cố do AI Agent trích xuất - Quan hệ 1-1)
* `id` (`VARCHAR(36)`, PK): UUID string.
* `case_id` (`VARCHAR(32)`, FK `cases.id`, UNIQUE): Liên kết 1-1 với `cases`.
* `summary` (`TEXT`): Bản tóm tắt cô đọng sự cố kỹ thuật.
* `captured_fields` (`JSON`): Các trường kỹ thuật trích xuất (`charger_id`, `error_code`, `current_soc`, `station_location`...).
* `suggested_action` (`TEXT`, nullable): Đề xuất hướng xử lý kỹ thuật ban đầu.
* `confidence_score` (`FLOAT`): Điểm tin cậy (0.0 đến 1.0).
* `is_edited_by_staff` (`BOOLEAN`, default False): Đánh dấu nếu nhân viên đã sửa nội dung brief.
* `generated_at`: `DATETIME` UTC.

### 3.4. Bảng `staff_audit_logs` (Nhật ký hành động HITL - Quan hệ 1-N)
* `id` (`VARCHAR(36)`, PK): UUID string.
* `case_id` (`VARCHAR(32)`, FK `cases.id`, indexed): Liên kết với `cases`.
* `staff_id` (`VARCHAR(50)`): ID nhân viên thao tác trên Console.
* `action` (`VARCHAR(30)`): `APPROVE`, `EDIT_BRIEF`, `REROUTE`, `CLOSE`, `REOPEN`, `REQUEST_INFO`.
* `previous_state` (`JSON`, nullable): Trạng thái trước khi thao tác.
* `new_state` (`JSON`, nullable): Trạng thái sau khi thao tác.
* `notes` (`TEXT`, nullable): Ghi chú của nhân viên.
* `created_at`: `DATETIME` UTC.

---

## 4. Đặc tả API Endpoints

Toàn bộ response bắt buộc bọc trong chuẩn Envelope:
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": {
    "timestamp": "2026-09-29T10:00:00.000000Z"
  }
}
```

### 4.1. Customer APIs
- **`POST /api/v1/customer/chat`**:
  - Tự động kiểm tra **Hard Safety Rules**: Nếu phát hiện từ khóa nguy hiểm (`cháy`, `khói`, `mất phanh`, `nổ lốp`, `rùa vàng cao tốc`), hệ thống ngay lập tức tạo Case với mức ưu tiên `CRITICAL`, gán trạng thái `Staff Reviewing`, bỏ qua bước hỏi làm rõ và trả về hướng dẫn an toàn (`safe_guidance`).
  - Hỗ trợ **RAG FAQ**: Trả lời kèm trích dẫn nguồn kiểm chứng (`citations`) và liên kết tính năng ứng dụng VinFast (`service_handoff`).
  - Kiểm soát **Clarification Boundary**: Tối đa 2 lượt hỏi làm rõ kèm các nút bấm gợi ý (`suggested_replies`).
  - Đủ dữ kiện kỹ thuật $\rightarrow$ Tự động sinh `CaseBrief` và chuyển `Staff Reviewing`.
- **`GET /api/v1/customer/cases/{case_id}/status`**:
  - Tra cứu trạng thái hồ sơ của khách hàng và mô tả tiến độ thân thiện.

### 4.2. Staff APIs (Service Agent Console)
- **`GET /api/v1/staff/tickets?status={status}&priority={priority}`**:
  - Lấy danh sách hàng đợi xử lý.
  - Mỗi ticket gồm: `id`, `mock_customer_id`, `vehicle_model`, `intent`, `priority`, `status`, `missing_info_flag`, `created_at`, `confidence_score`.
- **`GET /api/v1/staff/tickets/{case_id}`**:
  - Lấy chi tiết hồ sơ `case`, bản tóm tắt kỹ thuật `case_brief` và toàn bộ lịch sử trao đổi `conversation_history`.
- **`POST /api/v1/staff/tickets/{case_id}/actions`**:
  - Xử lý các hành động HITL: `APPROVE`, `EDIT_BRIEF`, `REROUTE`, `CLOSE`, `REOPEN`, `REQUEST_INFO`.
  - Tự động ghi vết vào bảng `staff_audit_logs`.

---

## 5. Hướng dẫn chạy và kiểm thử

### 5.1. Kích hoạt môi trường ảo
```powershell
.\.venv\Scripts\Activate.ps1
```

### 5.2. Chạy Migration Alembic
```powershell
alembic current        # Kiểm tra revision hiện tại (84802fff010b)
alembic upgrade head   # Nâng cấp database lên phiên bản mới nhất
```

### 5.3. Nạp dữ liệu mẫu (Seed Data)
```powershell
python -m src.seed --reset  # Xóa sạch dữ liệu cũ và seed 4 kịch bản chuẩn hóa
```

### 5.4. Chạy kiểm thử tự động (Pytest)
```powershell
pytest -v
```
*(Hiện tại 12/12 bài kiểm thử đã pass hoàn toàn).*

### 5.5. Khởi động Backend Server
```powershell
uvicorn src.main:app --reload --port 8000
```
- Swagger UI tài liệu API: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)
