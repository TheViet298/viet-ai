# Screen Specification (Screen-to-API & State Mapping)

> **Người phụ trách chính:** Việt (Frontend) + Triển (Backend) + Long (AI)  
> **Cập nhật lần cuối:** 2026-09-24  
> **Trạng thái:** Draft / In Review

---

> [!IMPORTANT]
> **Tài liệu Cầu nối Trọng tâm (Single Source of Truth):**  
> Mỗi màn hình trong tài liệu này định nghĩa rõ: Người dùng tương tác gì $\rightarrow$ Gửi field nào $\rightarrow$ Gọi API nào $\rightarrow$ Nhận phản hồi gì $\rightarrow$ Hiển thị các trạng thái (Loading, Empty, Error, Critical, No-source RAG) ra sao.

---

## 1. Màn hình 1: Customer Chat / Intake (`SCR-01`)

### 1.1. Mục đích & Giao diện
Giao diện chat chính cho khách hàng gửi thắc mắc hoặc báo sự cố xe VinFast.

### 1.2. Tương tác & API Mapping
* **Thao tác người dùng:** Gõ văn bản vào ô chat và nhấn "Gửi" (hoặc chọn Quick Prompt).
* **API gọi:** `POST /api/v1/customer/chat`
* **Request Payload:**
```json
{
  "session_id": "string",
  "case_id": "string | null",
  "message": "string",
  "customer_info": { "name": "string", "phone": "string", "vehicle_model": "string" }
}
```

### 1.3. Bảng Đặc tả Trạng thái Giao diện (UI States)

| Trạng thái (UI State) | Điều kiện kích hoạt | Hành vi & Hiển thị trên Giao diện |
| :--- | :--- | :--- |
| **Normal / Idle** | Sẵn sàng nhận tin nhắn | Hiển thị khung chat, lịch sử tin nhắn và 3 nút gợi ý câu hỏi nhanh (Quick Prompts). |
| **Loading / Typing** | Đang chờ API phản hồi | Khóa nút gửi tạm thời; hiển thị hiệu ứng "AI đang phân tích..." (Typing indicator). |
| **RAG Answer (Có nguồn)** | Response trả về `FAQ_ANSWER` | Hiển thị bong bóng chat câu trả lời kèm thẻ Card trích dẫn nguồn có thể click mở URL. |
| **RAG No Source / Fallback** | Response trả về `NO_SOURCE` | Hiển thị câu trả lời lịch sự: "Hệ thống chưa có dữ liệu chính thức, đang chuyển tiếp chuyên viên." |
| **Critical Safety Alert** | Priority = `CRITICAL` | Hiển thị Banner đỏ nổi bật trên đầu khung chat với nút bấm gọi nhanh Hotline cứu hộ 1900-232389. |
| **Network / Error State** | API trả về 5xx hoặc Timeout | Hiển thị toast lỗi màu cam: "Mất kết nối tạm thời. Vui lòng nhấn thử lại" kèm nút [Thử lại]. |

---

## 2. Màn hình 2: AI Clarification (`SCR-02`)

### 2.1. Mục đích & Giao diện
Giao diện xuất hiện khi AI nhận diện sự cố kỹ thuật nhưng còn thiếu các trường dữ liệu cốt lõi (Mã lỗi, Trụ sạc, Tình trạng vận hành).

### 2.2. Tương tác & API Mapping
* **Thao tác người dùng:** Bấm vào nút lựa chọn gợi ý (Quick Reply Chips) hoặc nhập văn bản chi tiết.
* **API gọi:** `POST /api/v1/customer/chat` (với `case_id` và `session_id` hiện tại).

### 2.3. Bảng Đặc tả Trạng thái Giao diện (UI States)

| Trạng thái (UI State) | Điều kiện kích hoạt | Hành vi & Hiển thị trên Giao diện |
| :--- | :--- | :--- |
| **Clarification Prompt** | Response trả về `CLARIFICATION` | Hiển thị câu hỏi làm rõ của AI dưới dạng Card nổi bật kèm danh sách các nút bấm gợi ý (Chips). |
| **Input Validation Error** | Khách bấm gửi tin rỗng / ký tự lạ | Hiển thị viền đỏ dưới ô input: "Vui lòng nhập rõ thông tin hoặc chọn gợi ý bên dưới." |

---

## 3. Màn hình 3: Customer Case Status & Result (`SCR-03`)

### 3.1. Mục đích & Giao diện
Màn hình xuất hiện sau khi Case Brief đã được tạo thành công, giúp khách hàng theo dõi tiến độ xử lý của nhân viên dịch vụ.

### 3.2. Tương tác & API Mapping
* **API Polling định kỳ:** `GET /api/v1/customer/cases/{case_id}/status` (Polling mỗi 5 giây hoặc SSE/WebSocket).

### 3.3. Bảng Đặc tả Trạng thái Giao diện (UI States)

| Trạng thái (UI State) | Trạng thái Ticket tương ứng | Hiển thị trên Giao diện |
| :--- | :--- | :--- |
| **Case Created / Reviewing** | `Staff Reviewing` | Hiển thị Mã Case (`CASE-xxxx`), Step 1: "Chuyên viên đang tiếp nhận và xem xét". |
| **In Progress** | `In Progress` | Step 2: "Kỹ thuật viên đang xử lý sự cố". Hiển thị ghi chú hỗ trợ sơ bộ. |
| **Needs Information** | `Needs Information` | Card thông báo màu vàng: "Nhân viên cần anh/chị cung cấp thêm thông tin" kèm ô nhập tin nhắn. |
| **Resolved** | `Resolved` | Step 3: "Sự cố đã có phương án giải quyết". Hiển thị hướng dẫn xử lý từ nhân viên & Nút "Xác nhận hài lòng". |
| **Closed** | `Closed` | Hiển thị màn hình đánh giá chất lượng dịch vụ (1 - 5 sao). |

---

## 4. Màn hình 4: Service Agent Console (`SCR-04`)

### 4.1. View 4A: Ticket Queue Dashboard

#### Tương tác & API Mapping:
* **API gọi:** `GET /api/v1/staff/tickets?status={status}&priority={priority}&intent={intent}`
* **Thao tác:** Lọc theo tab trạng thái, sắp xếp theo thời gian hoặc mức ưu tiên (CRITICAL lên đầu).

#### UI States:
* **Empty State:** Không có ticket nào thỏa mãn bộ lọc $\rightarrow$ Hiển thị illustration: "Không có phiếu yêu cầu nào đang chờ xử lý."
* **Loading State:** Skeleton table shimmer trong khi load danh sách.
* **Critical Highlight:** Hàng chứa ticket `CRITICAL` có nền viền đỏ nhấp nháy nhẹ để thu hút sự chú ý của nhân viên.

---

### 4.2. View 4B: Ticket Detail & HITL Actions

#### Tương tác & API Mapping:
* **API lấy chi tiết:** `GET /api/v1/staff/tickets/{case_id}`
* **API thực hiện hành động:** `POST /api/v1/staff/tickets/{case_id}/actions`
  * Body: `{ "action": "APPROVE" | "EDIT_BRIEF" | "REROUTE" | "CLOSE", "staff_id": "...", ... }`

#### UI States & Các nút bấm thao tác:
1. **[Approve Proposal]:** Duyệt nguyên trạng đề xuất của AI $\rightarrow$ Chuyển status sang `In Progress`.
2. **[Edit Case Brief]:** Mở form modal cho phép Staff sửa lại tóm tắt, mã lỗi hoặc phương án xử lý trước khi duyệt (Ghi nhận vào Audit Log).
3. **[Reroute Ticket]:** Chọn bộ phận điều phối mới (Đội cứu hộ cao tốc, Kỹ thuật trạm sạc, Showroom...) $\rightarrow$ Chuyển giao case.
4. **[Request Customer Info]:** Mở ô chat gửi tin nhắn trực tiếp yêu cầu khách bổ sung thông tin $\rightarrow$ Chuyển status sang `Needs Information`.
5. **[Close Ticket]:** Đóng case sau khi khách xác nhận hoàn tất.
