# 📘 VinFast ServiceFlow AI - Backend Changelog & Architecture Guide (`src/`)

Tài liệu này ghi nhận toàn bộ quá trình chuẩn hóa Backend, cơ sở dữ liệu SQLite, hệ thống Migration Alembic và bộ API theo đúng **Nguồn Chân Lý (Single Source of Truth - Cập nhật 2026-09-30)** tại thư mục `docs/`.

---

## 📍 Vị trí tài liệu
File được đặt trực tiếp tại: **`src/BACKEND_CHANGELOG.md`**

---

## 1. Lịch sử cập nhật chuẩn hóa

### 1.1. Cập nhật ngày 2026-09-30 (ADR-004, Auth & RBAC, Image Triage, Knowledge Hub)
Bổ sung các tính năng cốt lõi theo đặc tả mới nhất trong `docs/` (`auth-and-rbac.md`, `ADR-004-web-first-auth-and-image-triage.md`, `api-contract.md`):

1. **Hệ thống Xác thực & Phân quyền (Auth & RBAC):**
   - Vai trò: `Guest`, `Customer`, `Staff`.
   - `Guest`: Xem Landing, FAQ, Policy qua Knowledge Hub công khai (`/api/v1/public/articles`); không chat, không xem case.
   - `Customer`: Chat (text + ảnh), xem danh sách case của chính mình (`/api/v1/customer/cases`), mở lại case (`reopen`), đánh giá dịch vụ (`feedback`).
   - `Staff`: Quản trị hàng đợi (`/api/v1/staff/tickets`), xem chi tiết ticket kèm ảnh đính kèm và tín hiệu OCR/Vision sơ bộ, thực hiện hành động HITL (duyệt `APPROVE`, sửa brief `EDIT_BRIEF`, điều chuyển `REROUTE`, yêu cầu bổ sung `REQUEST_INFO`, giải quyết `RESOLVE`, đóng `CLOSE`, mở lại `REOPEN`).
   - Kiểm soát quyền chặt chẽ tại Backend: Trả `401` khi chưa đăng nhập và `403` khi sai vai trò hoặc truy cập case của người khác.

2. **Tiếp nhận & Phân tích ảnh sơ bộ (Image Triage & Private Attachments):**
   - API `POST /api/v1/customer/attachments`: Khách hàng tải ảnh táp-lô, đèn báo hoặc trụ sạc.
   - Lưu trữ tại thư mục riêng tư `data/attachments/` (không công khai ra ngoài web).
   - Module OCR/Vision trích xuất tín hiệu sơ bộ (`ocr_text`, `detected_signals`, `vision_confidence`). Kết quả là căn cứ sơ bộ để AI Agent đặt câu hỏi làm rõ ngữ cảnh, tuyệt đối không tự ý chẩn đoán nguyên nhân hoặc đóng case.
   - Cảnh báo bảo mật: Khách hàng được khuyến nghị không gửi ảnh chứa số VIN, biển số thật, CCCD hay khuôn mặt.

3. **Mở rộng Database Schema & Migration Alembic:**
   - Bảng mới `users`: Quản lý tài khoản, mật khẩu băm, vai trò `CUSTOMER`/`STAFF`.
   - Bảng mới `attachments`: Lưu trữ metadata ảnh tải lên, trạng thái phân tích (`analysis_status`), tín hiệu nhận diện sơ bộ.
   - Bảng mới `customer_feedback`: Lưu điểm đánh giá (1-5 sao) và nhận xét của khách hàng.
   - Bảng `cases`: Bổ sung `user_id` liên kết với tài khoản chủ sở hữu, cập nhật trạng thái mặc định ban đầu là `New`.
   - Tạo migration mới `9f03985a11a8_web_auth_and_attachments.py` nâng cấp mượt mà từ `84802fff010b`.

---

## 2. Bản đồ cấu trúc thư mục Backend

```text
E:\P-142\
├── alembic.ini                   # Cấu hình Migration Alembic trỏ vào migrations/ và data/app.db
├── migrations/                   # Hệ thống Alembic Database Migrations
│   ├── env.py                   # Cấu hình SQLAlchemy metadata & render_as_batch=True cho SQLite
│   ├── script.py.mako           # Template sinh mã migration
│   └── versions/
│       ├── c9952f7d6ac7_init_schema.py             # Migration khởi tạo cũ (base)
│       ├── 84802fff010b_align_spec_schema.py       # Revision: chuyển đổi sang 4 bảng chuẩn hóa
│       └── 9f03985a11a8_web_auth_and_attachments.py # Revision: bổ sung users, attachments, feedback
├── data/
│   ├── app.db                   # Database SQLite chính thức của dự án
│   └── attachments/             # Private Attachment Storage (lưu trữ ảnh táp-lô riêng tư)
├── src/
│   ├── main.py                  # FastAPI app, nạp Router, CORS, Lifespan tạo thư mục
│   ├── config.py                # Pydantic Settings
│   ├── db.py                    # SQLite engine, foreign keys PRAGMA, SessionLocal
│   ├── seed.py                  # Script nạp 4 kịch bản demo chuẩn hóa & tài khoản test
│   ├── BACKEND_CHANGELOG.md     # Tài liệu kiến trúc và hướng dẫn này
│   ├── services/
│   │   ├── auth.py              # Xử lý băm mật khẩu, tạo token session, dependency RBAC
│   │   └── llm.py               # Tích hợp Google Gemini LLM
│   ├── models/
│   │   ├── db_models.py         # SQLAlchemy ORM (User, Case, Message, CaseBrief, StaffAuditLog, Attachment, CustomerFeedback)
│   │   └── schemas.py           # Pydantic models với ApiResponse envelope
│   ├── api/
│   │   ├── auth.py              # Auth APIs: /login, /register, /me
│   │   ├── public.py            # Public Knowledge Hub: /public/articles
│   │   ├── customer.py          # Customer APIs: /chat, /attachments, /cases, /status, /reopen, /feedback
│   │   ├── staff.py             # Staff Console APIs: /tickets, /tickets/{id}, /actions
│   │   ├── cases.py             # Cases APIs tương thích ngược
│   │   └── routes.py            # API cơ bản của template (/chat, /status)
│   └── agents/                  # AI LangGraph Agent (giữ nguyên không đổi)
└── tests/
    ├── conftest.py              # Test fixtures (async client, mock LLM)
    ├── test_agents/             # Kiểm tra LangGraph flow
    └── test_api/
        ├── test_routes.py       # Kiểm tra các routes cơ bản
        └── test_aligned_spec.py # [MỚI] Bộ kiểm thử 14 kịch bản toàn diện chuẩn hóa theo Docs
```

---

## 3. Danh mục API Endpoints chi tiết

Toàn bộ response API bắt buộc trả về chuẩn Response Envelope:
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": {
    "timestamp": "2026-09-30T09:00:00.000000Z"
  }
}
```

### 3.1. Public & Auth APIs
- `GET /api/v1/public/articles`: Danh sách bài viết Knowledge Hub công khai (FAQ, hướng dẫn app, chính sách biểu phí, bảo hành). Cho phép Guest truy cập.
- `POST /api/v1/auth/register`: Đăng ký tài khoản Customer mới (không cho phép đăng ký Staff công khai).
- `POST /api/v1/auth/login`: Đăng nhập lấy access token và thông tin profile vai trò (`CUSTOMER` hoặc `STAFF`).
- `GET /api/v1/auth/me`: Lấy thông tin cá nhân của phiên đăng nhập hiện tại.

### 3.2. Customer APIs (Yêu cầu đăng nhập Customer)
- `POST /api/v1/customer/attachments`: Tải ảnh táp-lô, đèn báo hoặc trụ sạc. Lưu trữ private, trích xuất tín hiệu sơ bộ (`ocr_text`, `detected_signals`, `vision_confidence`).
- `POST /api/v1/customer/chat`: Nhận tin nhắn chat kèm danh sách `attachment_ids`. Áp dụng Hard Safety Rules (CRITICAL), RAG FAQ có citations, tối đa 2 lượt hỏi làm rõ kèm suggested replies.
- `GET /api/v1/customer/cases`: Lấy danh sách hồ sơ sự cố của chính khách hàng đang đăng nhập.
- `GET /api/v1/customer/cases/{case_id}/status`: Tra cứu tiến độ hồ sơ (kiểm tra quyền sở hữu).
- `POST /api/v1/customer/cases/{case_id}/reopen`: Mở lại hồ sơ đã được xử lý (Resolved/Closed).
- `POST /api/v1/customer/cases/{case_id}/feedback`: Gửi đánh giá dịch vụ (1 đến 5 sao) và nhận xét.

### 3.3. Staff APIs (Yêu cầu vai trò Staff)
- `GET /api/v1/staff/tickets?status={status}&priority={priority}`: Hàng đợi ticket cần xử lý của nhân viên điều phối.
- `GET /api/v1/staff/tickets/{case_id}`: Chi tiết hồ sơ, tóm tắt sự cố `case_brief`, lịch sử trao đổi và các ảnh táp-lô đính kèm.
- `POST /api/v1/staff/tickets/{case_id}/actions`: Xử lý hành động HITL:
  - `APPROVE`: Duyệt chuyển `In Progress`.
  - `EDIT_BRIEF`: Hiệu chỉnh tóm tắt sự cố kỹ thuật.
  - `REROUTE`: Điều chuyển bộ phận tiếp nhận.
  - `REQUEST_INFO`: Yêu cầu bổ sung dữ kiện (chuyển `Needs Information`).
  - `RESOLVE`: Hoàn tất xử lý (chuyển `Resolved`).
  - `CLOSE`: Đóng hồ sơ (`Closed`).
  - `REOPEN`: Mở lại hồ sơ (`Reopened`).
  Tự động ghi nhận lịch sử vào bảng `staff_audit_logs`.

---

## 4. Tài khoản Demo có sẵn (Seed Data)

Khi chạy lệnh nạp dữ liệu mẫu, hệ thống sẽ tự động tạo các tài khoản:

| Tên đăng nhập | Mật khẩu | Vai trò | Mục đích sử dụng |
| :--- | :--- | :--- | :--- |
| `staff@vinfast.vn` | `staff123` | **STAFF** | Truy cập Console nhân viên điều phối, xem ticket queue, duyệt action |
| `customer@vinfast.vn` | `customer123` | **CUSTOMER** | Đóng vai khách hàng Demo 01 (`CUST_MOCK_01`), sở hữu Case 001, 002, 003 |
| `customer2@vinfast.vn` | `customer123` | **CUSTOMER** | Đóng vai khách hàng Demo 02 (`CUST_MOCK_02`), sở hữu Case 004 đã giải quyết |

---

## 5. Hướng dẫn chạy và kiểm thử

### 5.1. Nâng cấp Database Migration
```powershell
& ".\.venv\Scripts\alembic.exe" upgrade head
```

### 5.2. Reset và Nạp dữ liệu mẫu (Seed Data)
```powershell
& ".\.venv\Scripts\python.exe" -m src.seed --reset
```

### 5.3. Chạy kiểm thử tự động (Pytest)
```powershell
& ".\.venv\Scripts\pytest.exe" -v
```
*(Hiện tại 14/14 bài kiểm thử tự động đã pass 100%).*

### 5.4. Khởi động Backend Server
```powershell
& ".\.venv\Scripts\uvicorn.exe" src.main:app --reload --port 8000
```
- Swagger UI tài liệu API: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)
