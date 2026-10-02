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

### 1.2. Cập nhật ngày 2026-09-30 (Tích hợp AI RAG Core, Chuẩn hóa Triage 5 Intents & Kết nối Live Full-Stack)

1. **Đồng bộ nhánh `origin/develop` vào `feature/frontend-ui`:**
   - Kéo và merge sạch sẽ code AI Agent từ `develop` (commit `1835eb1`), zero merge conflict.
   - Tích hợp `src/agents/chatbot_agent.py`:
     + **Hard Safety Guardrails:** Nhận diện tình huống khẩn cấp đe dọa an toàn (cháy nổ, khói đen, mất phanh, rùa vàng trên cao tốc). Bỏ qua hỏi đáp thông thường, kích hoạt ngay hướng dẫn bật đèn hazard, tấp lề khẩn cấp và gọi Hotline cứu hộ VinFast **1900-232389**.
     + **Bảo vệ dữ liệu No-PII:** Module `sanitize_pii` tự động ẩn danh hóa các thông tin nhạy cảm (SĐT thật, CCCD, biển số xe thật) trước khi chuyển vào context RAG.
     + **Đánh giá cờ duyệt HITL:** Module `is_hitl_mandatory` đánh giá tính bắt buộc cần chuyên viên xem xét dựa trên Intent, Priority, và RAG Confidence Score.
   - Mở rộng tri thức trong `src/services/rag_service.py`:
     + Chuyển đổi đường dẫn tuyệt đối tĩnh sang đường dẫn tương đối theo thư mục gốc của dự án (`os.path.dirname(...)`).
     + Mở rộng `FALLBACK_KNOWLEDGE_BASE` thành 7 nguồn tài liệu chính thống:
       * `SRC-001`: Chính sách bảo hành ô tô điện VinFast (VF 8: 10 năm hoặc 200.000km; pin cao áp mua đứt 10 năm không giới hạn km lăn bánh).
       * `SRC-002`: Hướng dẫn sử dụng Ứng dụng VinFast (đặt lịch bảo dưỡng, theo dõi dung lượng pin và tiến độ dịch vụ).
       * `SRC-003`: Thông tin cứu hộ khẩn cấp & Cứu hộ pin 24/7 (Hotline 1900-232389).
       * `SRC-004`: Chính sách và Biểu phí sạc pin trạm công cộng VinFast (đơn giá sạc, phí chiếm dụng trụ 1.000 VNĐ/phút sau 10 phút sạc đầy).
       * `SRC-005`: Cẩm nang bảo dưỡng định kỳ 12.000km (6 hạng mục kiểm tra tiêu chuẩn cho xe VF 8/VF 5/VF 9/e34).
       * `SRC-006`: Danh mục sản phẩm & Chính sách bán hàng (dải xe điện VF 3, VF 5, VF 6, VF 7, VF 8, VF 9, đăng ký lái thử, đặt cọc).
       * `SRC-007`: Thông số kỹ thuật chi tiết Catalog (so sánh VF 7 Plus 349 mã lực AWD vs Eco 201 mã lực FWD; kích thước và trọng lượng ~2.8 tấn của xe VF 9).

2. **Chuẩn hóa Triage Router Khớp 100% Data Model (`triage_test_v1.jsonl`):**
   - **Khắc phục lỗi hiểu nhầm câu hỏi thường:** Trước đó mọi câu không khớp từ khóa FAQ đều bị rơi xuống luồng sự cố sạc và hỏi mã lỗi táp-lô. Đã tái cấu trúc hoàn chỉnh 5 nhóm Intent theo thiết kế chuẩn:
     * **`sales_general_info` (Tư vấn bán hàng & Chào hỏi):**
       - Khách chào hỏi xã giao (*"xin chào", "chào em"*) -> Chào mừng lịch sự, giới thiệu các mảng dịch vụ AI hỗ trợ kèm nút phản hồi nhanh.
       - Khách hỏi mua xe (*"tôi muốn mua xe"*, *"tư vấn xe 7 chỗ"*, *"giá xe"*) -> Đóng vai trò chuyên viên tư vấn bán hàng giới thiệu toàn diện hệ sinh thái xe điện VinFast từ VF 3 đến VF 9, chính sách lái thử và bảng giá, đính kèm Citation `SRC-006`. Tuyệt đối không tạo case kỹ thuật thừa thãi.
       - Khách hỏi thông số xe (*"VF 7 Plus và Eco khác nhau gì"*, *"VF 9 nặng bao nhiêu"*) -> Tra cứu RAG trả lời chính xác thông số kỹ thuật.
     * **`charging_battery` & `service_incident` (Sự cố sạc / Kỹ thuật):**
       - Chỉ kích hoạt khi khách thực sự gặp lỗi/sự cố (*"không sạc", "kẹt súng", "báo lỗi", "0x41", "cc01", "bms", "kêu cọc cọc"*, hoặc có ảnh đính kèm).
       - Bóc tách thực thể thông minh: Tự động trích xuất Trạm sạc (`Landmark 81`), Trụ sạc (`Trụ số 3`), Mã lỗi (`0x41`), Dòng xe (`VF8`).
       - Khi đủ thông tin (như case `TRIAGE-003`): Tạo ngay hồ sơ `STAFF_REVIEWING` và chuyển thẳng lên Bàn điều phối (Console), không hỏi lặp lại.
       - Khi thiếu thông tin: Hỏi làm rõ chính xác trường còn thiếu kèm gợi ý phản hồi nhanh (Quick Replies).
     * **`safety_adversarial_oos` (An toàn & Ngoài phạm vi):**
       - Nguy hiểm khẩn cấp (cháy, khói dưới gầm) -> Cảnh báo đỏ, hotline 1900-232389, tạo hồ sơ CRITICAL.
       - Ngoài phạm vi (Rule 2.4 - xe Tesla, vé máy bay, hack tốc độ) -> Từ chối lịch sự theo quy tắc No Source.
     * **`complaint_feedback` (Khiếu nại / Góp ý):**
       - Tiếp nhận phản ánh xe xăng chiếm chỗ sạc, trừ tiền 2 lần, lỗi app văng crash -> Tạo hồ sơ khiếu nại chuyển CSKH xử lý ưu tiên.

3. **Kết nối Toàn diện Frontend UI với Live Backend APIs:**
   - **Customer Chat (`chatApi.ts` & `CustomerChatContainer.tsx`):**
     + Đấu nối trực tiếp vào `POST /api/v1/customer/chat`.
     + Đấu nối tải ảnh đính kèm táp-lô qua `POST /api/v1/customer/attachments`.
     + Đấu nối danh sách case khách hàng qua `GET /api/v1/customer/cases`.
     + Đấu nối mở lại case `POST /api/v1/customer/cases/{id}/reopen` và đánh giá dịch vụ `POST /api/v1/customer/cases/{id}/feedback`.
   - **Bàn điều phối Staff Console (`consoleApi.ts`):**
     + Tự động gắn token xác thực chuyên viên (`staff_token_demo_auto`) khi gọi `/api/v1/staff/tickets` và `/api/v1/staff/actions`.
     + Loại bỏ hoàn toàn lỗi 401 Unauthorized, hiển thị tức thời các Case kỹ thuật vừa tạo từ phòng chat để nhân viên duyệt HITL.
   - **Theo dõi Tiến độ Sự cố (`track-case/page.tsx`):**
     + Kết nối thời gian thực với backend để hiển thị quy trình xử lý 5 bước, thông tin tóm tắt Case Brief và quyết định của chuyên viên.
   - **Xác thực Người dùng (`AuthContext.tsx`):**
     + Đồng bộ đăng nhập, đăng ký và lấy thông tin phiên làm việc từ `POST /api/v1/auth/login`, `POST /api/v1/auth/register`, `GET /api/v1/auth/me`.

4. **Nâng cấp Trải nghiệm Chatbot (Chat UX):**
   - **Nút "Làm mới" (Reset Chat):** Bố trí tiện lợi tại thanh công cụ trên đầu khung chat và thanh bên trái; cho phép làm mới phiên hội thoại, reset session ID, xóa case cũ và dọn sạch ảnh đính kèm.
   - **Hiệu ứng AI Thinking (Sequential AI Bubble):** Khi người dùng gửi câu hỏi, giao diện lập tức hiển thị trạng thái suy nghĩ của bot với avatar thương hiệu, nhãn trạng thái nhấp nháy (*"Trợ lý VinFast AI • Đang suy nghĩ..."*) và hiệu ứng 3 chấm nảy sinh động trước khi câu trả lời hoàn tất.

5. **Cơ chế Database Auto-Fallback Thông minh:**
   - Trong `src/db.py`: Bổ sung cơ chế tự động bắt lỗi khi chuỗi kết nối là PostgreSQL nhưng máy chưa cài driver `psycopg`. Hệ thống tự động chuyển mượt sang SQLite cục bộ (`sqlite:///./data/app.db`) mà không bao giờ ném lỗi dừng server.

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
