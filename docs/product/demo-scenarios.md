# Demo Scenarios & Test Scripts (MVP)

> **Người phụ trách:** Cả nhóm (Chủ trì: Việt & Long)  
> **Cập nhật lần cuối:** 2026-09-27
>
> **Trạng thái:** In Review (Đã chuẩn hóa Safe Guidance, Rule Critical kết hợp và App Handoff)

---

## 1. Dữ liệu Mô phỏng Chuẩn (Seed Data Conventions)

> [!IMPORTANT]
> **Quy định Bảo mật Dữ liệu (Privacy Guardrail):**
> * Tuyệt đối không dùng VIN thật, biển số thật, số điện thoại thật của khách hàng.
> * Định dạng mã định danh xe mẫu: `VF-SF-00231` (Dòng xe: VF8 Plus, Năm SX: 2024).
> * Mã trụ sạc mẫu: `VN-CS-HN042-P02` (Trạm sạc Vincom Metropolis, Cổng sạc DC 150kW).
> * Khách hàng mẫu: `Khách hàng Demo 01` (ID: `CUST_MOCK_01`, SĐT giả lập: `0900-000-231`).

---

## 2. Kịch bản Demo 1: Sự cố không sạc được tại Trụ sạc (Vertical Slice Core - Ưu tiên P0)

* **Intent:** `Charging/Battery`
* **Mục tiêu Demo:** Chứng minh khả năng Triage $\rightarrow$ Hỏi làm rõ (tối đa 2 lượt có cấu trúc kèm quick replies) $\rightarrow$ Sinh Case Brief chuẩn $\rightarrow$ Staff duyệt $\rightarrow$ Khách xem tiến độ.

### Các bước thực hiện:

1. **Bước 1 (Customer Intake):**
   * *User gửi:* ảnh màn hình/táp-lô hoặc trụ sạc kèm: `"Em không biết lỗi gì, xe không nhận sạc."`
   * *Vision/OCR:* trích xuất tín hiệu sơ bộ (nếu ảnh rõ), ví dụ mã `CC01` hoặc đèn đỏ; nếu không đọc được thì Agent hỏi ảnh rõ hơn/mô tả hiện tượng.
2. **Bước 2 (AI Triage & Clarify - Lượt 1):**
   * *AI nhận diện sơ bộ:* Intent `Charging/Battery`, Priority `HIGH`.
   * *AI phân tích thiếu:* Mã cổng sạc và mã lỗi cụ thể hiển thị trên màn hình xe.
   * *AI phản hồi (kèm gợi ý):* *"Dạ em ghi nhận xe VF8 đang gặp sự cố sạc tại Vincom Metropolis. Màn hình xe có hiển thị mã lỗi (ví dụ: CC01, BMS_012) hoặc mã trụ sạc không ạ?"*
   * *Gợi ý Quick Replies:* `["Mã lỗi CC01, trụ P02", "Đèn đỏ, không hiện mã", "Không thấy mã lỗi"]`
3. **Bước 3 (Customer bổ sung):**
   * *User chọn:* `"Mã lỗi CC01, trụ P02"` (hoặc nhập: `"Màn hình báo lỗi giao tiếp CC01, trụ VN-CS-HN042-P02"`).
4. **Bước 4 (AI Case Brief & Output):**
   * *AI xuất ra giao diện Customer:*
     * Mã Case: `CASE-20260924-001`
     * Trạng thái: `Staff Reviewing` (Đã đủ dữ kiện $\rightarrow$ Chuyển Staff Review)
     * Tóm tắt sơ bộ: Sự cố kết nối CC01 tại trụ sạc VN-CS-HN042-P02.
     * Thông báo an toàn: *"Hệ thống đã ghi nhận sự cố và tạo hồ sơ hỗ trợ. Thông tin sẽ được hiển thị cho nhân viên xử lý trên môi trường demo; vui lòng theo dõi cập nhật trên giao diện này."*
5. **Bước 5 (Staff Console):**
   * Staff mở Ticket Detail của `CASE-20260924-001`.
   * Thấy đầy đủ Case Brief (Model: VF8, Mã lỗi: CC01, Vị trí: Metropolis, Đề xuất: Kiểm tra tín hiệu trụ sạc từ xa hoặc điều phối kỹ thuật viên trạm hỗ trợ).
   * Staff chọn `Approve` & cập nhật sang `In Progress`. Khách hàng thấy trạng thái cập nhật ngay lập tức.

---

## 3. Kịch bản Demo 2: Cảnh báo Rùa vàng & Giảm công suất nguy hiểm (Service & Critical Safety)

* **Intent:** `Service/Incident`
* **Mục tiêu Demo:** Chứng minh quy tắc an toàn tổ hợp (Composite Safety Rule), phân loại `CRITICAL`, phản hồi an toàn tức thì.

### Các bước thực hiện:

1. **Bước 1 (Customer Intake):**
   * *User nhập:* `"Xe VF9 của tôi đang chạy trên cao tốc thì hiện biểu tượng rùa vàng và xe bị giật, đạp ga không lên quá 30km/h."`
2. **Bước 2 (AI Safety Check & Triage):**
   * *Hệ thống kích hoạt Hard Safety Rule:* Phát hiện tổ hợp `"rùa vàng"` + `"trên cao tốc"` (Nguy cơ an toàn giao thông nghiêm trọng).
   * *Priority:* `CRITICAL`.
3. **Bước 3 (AI Output & Immediate Safety Advice):**
   * *AI phản hồi ngay lập tức (bỏ qua hỏi làm rõ):*
     * Hướng dẫn an toàn: *"Anh/chị vui lòng bật đèn khẩn cấp (Hazard), từ từ tấp xe vào làn dừng khẩn cấp an toàn."*
     * Hotline cứu hộ: **1900-232389**.
     * Tự động tạo Case khẩn cấp: `CASE-20260924-002` (Trạng thái: `Staff Reviewing`, Priority: `CRITICAL`).
4. **Bước 4 (Staff Console):**
   * Ticket xuất hiện trên cùng hàng đợi với nhãn đỏ nổi bật **[CRITICAL]**.
   * Staff nhấn `Reroute` chuyển thẳng Đội Cứu hộ Cao tốc Khu vực lân cận.

---

## 4. Kịch bản Demo 3: Tra cứu Hướng dẫn Tính năng Ứng dụng & Dịch vụ (RAG FAQ)

* **Intent:** `Sales/General Info`
* **Mục tiêu Demo:** Trích dẫn nguồn tài liệu VinFast công khai chính thức đã kiểm chứng, hướng dẫn khách hàng vào tính năng dịch vụ trên Ứng dụng VinFast.

### Các bước thực hiện:

1. **Bước 1 (Customer Intake):**
   * *User nhập:* `"Làm thế nào để tôi có thể theo dõi tình trạng pin và đặt lịch bảo dưỡng xe VinFast trên điện thoại?"`
2. **Bước 2 (RAG Retrieval):**
   * Truy xuất tài liệu: `Hướng dẫn sử dụng Ứng dụng VinFast cho ô tô điện (Phần 2)` (`SRC-APP-001`).
   * Tìm thấy đoạn: *Khách hàng có thể theo dõi tình trạng xe, kiểm tra dung lượng pin, đặt lịch dịch vụ và theo dõi tiến độ sửa chữa trực tiếp trên ứng dụng VinFast.*
3. **Bước 3 (AI Output):**
   * *AI phản hồi:* *"Theo Hướng dẫn sử dụng Ứng dụng VinFast, anh/chị có thể dễ dàng quản lý tình trạng xe, kiểm tra mức pin/sạc và chủ động đặt lịch dịch vụ bảo dưỡng/sửa chữa trực tiếp trên Ứng dụng VinFast."*
   * *Trích dẫn nguồn:* [Hướng dẫn sử dụng Ứng dụng VinFast cho ô tô điện (Phần 2)](https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast) (Ngày kiểm tra nội dung: 2026-09-27, Mã nguồn: `SRC-APP-001`).
   * *Hướng dẫn dịch vụ:* *"Để thực hiện, anh/chị mở Ứng dụng VinFast $\rightarrow$ chọn mục **Dịch vụ** $\rightarrow$ **Đặt lịch dịch vụ** hoặc chọn xưởng dịch vụ gần nhất."*
