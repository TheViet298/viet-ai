# Báo Cáo Đồng Bộ Hóa Xác Thực & Dữ Liệu Hồ Sơ (Auth & Profile Synchronization)

> **Người thực hiện:** Antigravity Pair Programmer  
> **Dự án:** VinFast ServiceFlow AI (P-142)  
> **Tài liệu tham chiếu:** `docs/architecture/auth-and-rbac.md`, `docs/architecture/api-contract.md`, `docs/decisions/ADR-004-web-first-auth-and-image-triage.md`, `ADR-005`  
> **Trạng thái:** Hoàn thành — Đồng bộ 100% từ Đăng ký, Đăng nhập, Chat tới Staff Console.

---

## 1. Mục Tiêu & Nguyên Tắc Đã Khóa Cứng (Guardrails)

Tuân thủ nghiêm ngặt 3 nguyên tắc nền tảng đã thống nhất:
1. **Không bỏ tính năng, không thay đổi đường dẫn URL hay nghiệp vụ đã chốt:** Giữ nguyên các endpoints `/api/v1/customer/*`, `/api/v1/staff/*`, `/api/v1/chat`, `/api/v1/agent/*`.
2. **Bảo toàn luồng Guest vãng lai:** Khách vãng lai (`Guest`) **không tạo bản ghi trong bảng `users`**. Giữ nguyên cơ chế đếm lượt (tối đa 5 lượt/phiên chat) và quy định **chỉ Customer đã đăng nhập mới được upload ảnh táp-lô/trụ sạc** (theo ADR-004 & api-contract.md).
3. **Thống nhất một cơ chế xác thực DB duy nhất:** Chuyển toàn bộ các route (kể cả nhóm `/agent/*`) từ demo token tĩnh sang JWT Bearer Token thật (HS256) mang `User.id` và vai trò thật từ cơ sở dữ liệu.

---

## 2. Chi Tiết Các Thay Đổi Theo Từng File

### 2.1. Cơ Sở Dữ Liệu & ORM Models
* **File:** `src/models/db_models.py`
  * Mở rộng bảng `users` thêm 3 cột lưu trữ hồ sơ:
    * `full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)`: Lưu tên khách hàng (xưng hô trong chat).
    * `phone: Mapped[str | None] = mapped_column(String(20), nullable=True)`: Lưu số điện thoại liên hệ.
    * `vehicle_model: Mapped[str | None] = mapped_column(String(50), nullable=True)`: Lưu dòng xe đang sử dụng (VF3, VF5, VF8, v.v.).
  * Giữ nguyên `UserRole` enum (`GUEST`, `CUSTOMER`, `STAFF`) và các ràng buộc khóa ngoại liên quan.

### 2.2. Schema Request / Response
* **File:** `src/models/schemas.py`
  * `RegisterRequest`: Bổ sung các trường `full_name`, `phone`, `vehicle_model`, `mock_customer_id` (đều có kiểu `str | None = None`).
  * `UserOut`: Bổ sung `full_name`, `phone`, `vehicle_model` trong payload trả về của `/auth/login`, `/auth/register` và `/auth/me`.

### 2.3. Dịch Vụ Xác Thực & Mã Hóa Mật Khẩu
* **File:** `src/services/auth.py`
  * **JWT Chuẩn RFC 7519 (HS256):** Token chứa các claims chuẩn: `sub` (`User.id`), `role`, `iat`, `exp` và `iss`. Giải mã và kiểm tra chữ ký nghiêm ngặt.
  * **Dual Password Verification (An toàn tương thích ngược):** Hỗ trợ thuật toán băm thế hệ mới `Argon2id` kết hợp kiểm tra tương thích ngược `SHA-256 + Salt` cho các tài khoản seed demo cũ. Tự động nâng cấp hash mật khẩu khi đăng nhập thành công.
  * **Siết RBAC theo Route:**
    * `require_customer`: Bắt buộc `current_user.role == "CUSTOMER"`.
    * `require_staff`: Bắt buộc `current_user.role == "STAFF"`.

### 2.4. Dependency Phân Tầng Sạch (Clean Architecture)
* **File:** `src/api/dependencies.py` (Mới)
  * Tách toàn bộ identity dependencies ra khỏi router:
    * Dataclass `Principal(id, role)`: Gắn liền với `User.id` và `role` thật từ cơ sở dữ liệu.
    * `optional_principal`: Trích xuất danh tính nếu có token hợp lệ.
    * `customer` & `staff`: Kiểm tra quyền dựa trên vai trò thực tế.

### 2.5. Routers Xác Thực Backend
* **File:** `src/api/auth.py`
  * `/auth/register`: 
    * Lưu trọn vẹn `full_name`, `phone`, `vehicle_model` vào bảng `users`.
    * Bọc khối `try...except IntegrityError` khi commit DB để trả về mã `HTTP 409 Conflict` thân thiện nếu tài khoản đã tồn tại.
  * `/auth/login` & `/auth/me`: Trả về `UserOut` đầy đủ thông tin hồ sơ cho Frontend.
  * Tích hợp cơ chế Rate Limiting chống spam/brute-force mật khẩu.
  * Re-export `Principal, customer, optional_principal, staff` để đảm bảo 100% tương thích ngược với các module và test case cũ.

### 2.6. Đồng Bộ Dữ Liệu Khi Khách Hàng Chat & Tạo Sự Cố
* **File:** `src/api/customer.py`
  * Trong hàm `customer_chat`:
    * Tự động ưu tiên dòng xe của khách hàng: nếu context chưa có, tự động lấy `current_user.vehicle_model`.
    * Khi tạo hồ sơ sự cố (`Case`), tự động điền `mock_customer_name = current_user.full_name` và `mock_customer_phone = current_user.phone`.
    * Đảm bảo `user_id = current_user.id if current_user else None` an toàn cho cả nhánh khiếu nại (tránh lỗi null attribute của Guest).

### 2.7. Dữ Liệu Khởi Tạo (Seed Data) & Công Cụ Quản Trị
* **File:** `src/seed.py`: Bổ sung thông tin hồ sơ mẫu cho `user_cust_1` (Nguyễn Văn Tuấn, VF8), `user_cust_2` (Trần Thị Mai, VF5) và `user_staff` (Cố vấn Dịch vụ VinFast).
* **File:** `src/create_staff.py`: Script CLI tạo tài khoản nhân viên nội bộ (`python -m src.create_staff <email>`) an toàn, không mở API đăng ký Staff ra internet.

### 2.8. Giao Diện Người Dùng Frontend
* **File:** `frontend/src/features/shared/context/AuthContext.tsx`
  * Mở rộng `ApiUser` và `AuthUser` thêm `phone`, `vehicleModel`.
  * `mapApiUser`: Đồng bộ trực tiếp `user.full_name`, `user.vehicle_model`, `user.phone` từ server vào trạng thái phiên làm việc.
  * `registerCustomer`: Gửi toàn bộ `full_name`, `phone`, `vehicle_model` lên API.
  * `loginDemo`: Tận dụng API đăng nhập thật với tài khoản seed (`customer@vinfast.vn`, `staff@vinfast.vn`).
* **File:** `frontend/src/app/register/page.tsx`
  * Chỉnh sửa giao diện tự nhiên, chuẩn mực cho khách hàng:
    * Ô nhập liệu: **Tên của bạn / Biệt danh xưng hô**, **Số điện thoại / Tên đăng nhập**, **Dòng xe**, **Mật khẩu**.
    * Banner cam kết bảo mật No-PII viết trang nhã, chuyên nghiệp (cam kết không thu thập CCCD, bằng lái, số khung VIN hay biển số xe).
    * Bắt lỗi và chỉ chuyển trang `/chat` khi đăng ký thành công trên backend.

---

## 3. Bảng Ma Trận Phân Quyền (RBAC Matrix Sau Đồng Bộ)

| Hành động | Khách vãng lai (Guest) | Khách hàng (Customer) | Nhân viên (Staff) | Endpoint / Ghi chú |
| :--- | :---: | :---: | :---: | :--- |
| **Xem Landing, FAQ, Bài viết** | ✅ | ✅ | ✅ | `GET /api/v1/public/articles` |
| **Đăng ký tài khoản mới** | ✅ (Tạo Customer) | ❌ | ❌ | `POST /api/v1/auth/register` (Luôn gán role `CUSTOMER`) |
| **Đăng nhập hệ thống** | ❌ | ✅ | ✅ | `POST /api/v1/auth/login` (Cấp Bearer JWT) |
| **Chat hỏi đáp cẩm nang / RAG** | ✅ (Giới hạn 5 lượt) | ✅ (Không giới hạn) | ✅ (Preview mode) | `POST /api/v1/customer/chat` & `/api/v1/chat` |
| **Tải ảnh táp-lô & trụ sạc** | ❌ (Chặn 401) | ✅ | ❌ | `POST /api/v1/customer/attachments` |
| **Tạo & theo dõi Case cá nhân** | ❌ | ✅ (Chỉ case của mình) | ❌ | `GET /api/v1/customer/cases` |
| **Truy cập Bàn điều phối (Console)** | ❌ (Chặn 401) | ❌ (Chặn 403) | ✅ | `GET /api/v1/staff/tickets` & `/dashboard` |
| **Duyệt / Điều phối sự cố (HITL)** | ❌ | ❌ | ✅ | `POST /api/v1/staff/tickets/{id}/actions` |

---

## 4. Kết Quả Sau Kiểm Tra
* Không làm vỡ bất kỳ route nào trong số các route hiện tại.
* Dữ liệu từ form đăng ký được truyền liền mạch vào DB và hiển thị đồng nhất ở màn hình Chat, Thông tin hồ sơ, và Bàn điều phối của Staff.
* Đạt chuẩn kiến trúc sạch, an toàn bảo mật và sẵn sàng triển khai thực tế.
