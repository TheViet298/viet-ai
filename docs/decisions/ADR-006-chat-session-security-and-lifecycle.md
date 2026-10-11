# ADR-006 — Chat Session Security, Ownership Isolation & Lifecycle Hardening

**Trạng thái:** Accepted  
**Ngày:** 2026-10-11  
**Phạm vi:** Backend API (`src/api/auth.py`, `src/api/customer.py`), Data Model (`src/models/schemas.py`, `src/models/db_models.py`), Frontend Client (`useChat.ts`, `AuthContext.tsx`, `ChatHistorySidebar.tsx`)

---

## 1. Bối cảnh & Vấn đề (Context & Problem Statement)

Khi bổ sung tính năng Lịch sử trò chuyện đa phiên (Multi-session Chat History) cho giao diện Web:
1. **Lỗ hổng chiếm đoạt phiên (Session Takeover):** Điều kiện query trước đây `(ChatSession.owner == f"guest:{raw_claim}") | (ChatSession.id == raw_claim)` cho phép kẻ tấn công chỉ cần gửi `raw_claim` là `session_id` của bất kỳ user nào khác khi đăng nhập/đăng ký là có thể cướp quyền sở hữu (`owner`) của phiên đó sang tài khoản kẻ tấn công.
2. **Nguy cơ rò rỉ dữ liệu khi gộp Case & Message:** Nếu cập nhật Case hoặc Message trực tiếp theo `raw_claim`, có thể ghi đè Case/Message thuộc về người dùng khác.
3. **Session Enumeration (IDOR):** Việc trả về HTTP 403 Forbidden khi kiểm tra quyền sở hữu làm lộ sự tồn tại của session_id trong hệ thống.
4. **Entropy của Guest ID quá thấp:** Sinh mã dạng `sess_vf_${Math.random()}` dễ bị đoán trước.
5. **SQLAlchemy JSON Mutation Silent Drop:** Cột `memory_states` là JSON; việc cập nhật dict in-place không kích hoạt cơ chế dirty tracking của SQLAlchemy nếu không gán lại dict mới hoặc gọi `flag_modified`, dẫn đến mất cờ `title_edited`.
6. **Title Cache bị đóng băng quá sớm:** Nếu câu đầu tiên là lời chào ("xin chào"), tiêu đề bị lưu vĩnh viễn là "Cuộc trò chuyện mới" và không bao giờ tự cập nhật khi câu hỏi thực sự xuất hiện.
7. **Rò rỉ lịch sử trên máy dùng chung (Shared Computer Leak):** Khi đăng xuất (logout), nếu client không dọn dẹp state và không rotate guest id thì người sau có thể đọc được tin nhắn của người trước.
8. **Dữ liệu mồ côi (Orphan Records):** Xóa session không xóa Message và ChatRequestRecord đi kèm.

---

## 2. Quyết định Kiến trúc (Decisions)

### 2.1. Khắc phục triệt để lỗ hổng Session Takeover & Phân quyền nghiêm ngặt
* **Loại bỏ hoàn toàn vế `ChatSession.id == raw_claim`:**
  ```python
  guest_sessions = (
      db.query(ChatSession)
      .filter(ChatSession.owner == f"guest:{raw_claim}")
      .all()
  )
  ```
  Chỉ những phiên đang ở trạng thái khách vãng lai của đúng client đó (`owner == "guest:{raw_claim}"`) mới được phép chuyển sang `user:{user.id}`.
* **Gộp Case an toàn:** Chỉ gộp `Case` có `Case.user_id.is_(None)` và `Case.session_id` thuộc danh sách session hợp lệ của guest đó. Tuyệt đối không ghi đè Case đã có chủ.
* **Cập nhật Message theo phạm vi session đã claim:** Chỉ cập nhật metadata `user_id` cho các tin nhắn nằm trong `claimed_session_ids` đã được xác thực ở bước trên.
* **Thực thi nguyên tử (Atomic Transaction):** Luồng gộp dữ liệu được thực thi trong cùng transaction của cả `POST /api/v1/auth/login` và `POST /api/v1/auth/register`. Trả về số lượng `claimed_sessions` trong `AuthResponseData`.

### 2.2. Bảo vệ IDOR & Chống Dò Quét (Anti-Enumeration 404)
* Mọi endpoint truy xuất, đổi tên, xóa phiên (`/customer/sessions/*`, `/customer/sessions/{id}/history`):
  Nếu session không tồn tại HOẶC không thuộc về user/guest hiện tại $\rightarrow$ **Luôn trả về HTTP 404 Not Found** (thay vì 403 Forbidden).

### 2.3. Định danh Guest với Entropy cao (UUID v4)
* Guest session ID trên client bắt buộc sinh qua `crypto.randomUUID()` (chuẩn RFC 4122 UUID v4 với 122 bit entropy ngẫu nhiên thực sự).
* Regex backend kiểm tra độ dài từ 8 đến 64 ký tự `^[a-zA-Z0-9_\-]+$`.

### 2.4. Đồng bộ JSON Column bền vững với `flag_modified`
* Mọi thao tác sửa đổi trường `memory_states` (lưu tiêu đề, cờ `title_edited`, dữ liệu ngữ cảnh) bắt buộc gọi:
  ```python
  from sqlalchemy.orm.attributes import flag_modified
  flag_modified(session, "memory_states")
  ```
  Đảm bảo ORM luôn đánh dấu dirty và commit chuẩn xác xuống cơ sở dữ liệu.

### 2.5. Trích xuất Tiêu đề Động & Chống Đóng Băng Cache Sớm
* Trong `extract_session_title`: sử dụng regex bóc tách toàn bộ tiền tố chào hỏi tiếng Việt (`dạ`, `em`, `xin chào`, `chào trợ lý`, `alo`, `hi`, v.v.).
* Nếu phiên mới chỉ có câu chào $\rightarrow$ tiêu đề tạm thời là `"Cuộc trò chuyện mới"` và **không ghi cache vào DB**.
* Khi có tin nhắn nội dung thực đầu tiên $\rightarrow$ tự động trích xuất tiêu đề và ghi cache DB.
* Khi người dùng đổi tên thủ công qua `PATCH` $\rightarrow$ bật `title_edited: true` vĩnh viễn, ngăn auto-title ghi đè.

### 2.6. Vòng đời Client Storage & Vệ sinh khi Đăng xuất (Logout Hygiene)
* Client chỉ xóa `vf_chat_session:guest` khi nhận phản hồi xác thực thành công (HTTP 200). Nếu lỗi mạng hoặc lỗi server, guest id được giữ nguyên để bảo toàn dữ liệu.
* Khi `logout()`: Xóa sạch toàn bộ token, profile, session storage cũ; đồng thời **tự động sinh ngay một UUID v4 mới** cho guest tiếp theo. State React trong `useChat` lập tức reset về welcome message sạch.

### 2.7. Xóa Triệt Để Dữ Liệu (Cascade Orphan Deletion)
* Khi xóa 1 phiên hoặc xóa toàn bộ lịch sử: đồng thời xóa tường minh toàn bộ bản ghi `Message` và `ChatRequestRecord` thuộc `session_id` đó trước khi xóa `ChatSession`, tuân thủ cam kết bảo mật quyền riêng tư của hệ thống.

### 2.8. Chuẩn hóa Định tuyến (Route Standardization & Deprecation)
* Đường dẫn chính thức: `/api/v1/customer/sessions` và `/api/v1/customer/sessions/{session_id}/history`.
* Đường dẫn cũ `/api/v1/customer/chat/sessions/*` được gắn `deprecated=True, include_in_schema=False`.

---

## 3. Hệ quả & Đánh giá (Consequences)

* ✅ Loại bỏ hoàn toàn nguy cơ chiếm đoạt phiên (IDOR / Session Takeover).
* ✅ Đảm bảo tính toàn vẹn dữ liệu: không còn case hay message mồ côi.
* ✅ UX mượt mà: tiêu đề tự động cập nhật đúng lúc, tên thủ công được giữ nguyên sau F5.
* ✅ An toàn trên máy dùng chung: đăng xuất xóa sạch lịch sử và cấp ngay guest key mới.
* ✅ Toàn bộ 5 kịch bản kiểm thử bảo mật tự động đạt 100% Pass trong bộ `tests/test_api/test_session_security_and_lifecycle.py`.
