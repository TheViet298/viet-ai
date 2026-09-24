# Product Scope & Problem Definition (MVP)

> **Người phụ trách chính:** Việt (Product Lead)  
> **Cập nhật lần cuối:** 2026-09-24  
> **Trạng thái:** In Review (Đã cập nhật theo kết quả khảo sát thăm dò ban đầu)

---

## 1. Định vị và Tên gọi Chính xác của Hệ thống

> [!IMPORTANT]
> **Tên chính thức:** *Hệ thống AI Agent điều phối yêu cầu dịch vụ đa kênh và chuẩn hóa bàn giao case cho nhân viên VinFast.*  
> **KHÔNG GỌI LÀ:** *"AI Agent tự động giải quyết / sửa chữa sự cố xe"*.  
> Việc chẩn đoán chuyên sâu, cứu hộ hiện trường và sửa chữa kỹ thuật thực tế do Đội ngũ Kỹ thuật viên / Chuyên viên VinFast xử lý. AI đóng vai trò là "Cầu nối số" giúp tiếp nhận 24/7, sàng lọc, làm rõ thông tin và tổng hợp thành Case Brief chuẩn nghiệp vụ.

---

## 2. Vấn đề cần giải quyết & Kết quả Khảo sát Thăm dò Ban đầu

### 2.1. Khảo sát thăm dò ban đầu (Exploratory Survey - Mẫu n=4)
> [!NOTE]
> Khảo sát thăm dò ban đầu với 4 chủ xe VinFast cho thấy 3/4 người từng cần hỗ trợ kỹ thuật/dịch vụ trong 6 tháng gần đây; các phản hồi ghi nhận tình trạng phải liên hệ lại (trung bình 2 lần/kênh) và mô tả lại một phần thông tin đã cung cấp.  
> **Lưu ý phương pháp luận:** Đây là tập tín hiệu và giả thuyết ban đầu để MVP kiểm chứng, **không đại diện cho toàn bộ khách hàng VinFast**. Nhóm sẽ tiếp tục mở rộng khảo sát và phỏng vấn sâu ở các giai đoạn tiếp theo để bổ sung thêm dữ liệu. File raw chứa thông tin cá nhân (Email, Họ tên) được bảo mật nội bộ và **tuyệt đối không commit lên repository công khai**.

### 2.2. Đối chiếu Tín hiệu Khảo sát vào Bài toán MVP
| Tín hiệu từ Khảo sát Thăm dò (n=4) | Cách Match vào Bài toán & Scope MVP |
| :--- | :--- |
| **3/4** từng cần hỗ trợ trong 6 tháng; vấn đề tập trung ở **Cảnh báo lỗi, Sự cố kỹ thuật, Pin/Trụ sạc**. | Quyết định đi sâu vào 2 Intent cốt lõi: `Charging/Battery` và `Service/Incident`. |
| **3/3** người từng cần hỗ trợ cho biết phải liên hệ $\ge 2$ lần/kênh và phải mô tả lại thông tin "có một phần". | **P0 MVP:** Bắt buộc có cơ chế **Contextual Clarification** (làm rõ có cấu trúc) + **Case Brief** chuẩn hóa + hiển thị **Tiến độ/Lịch sử case**. |
| **3/4** chọn mong muốn *"Giải thích cảnh báo/lỗi dễ hiểu"*; **3/4** chọn *"Tóm tắt để không phải mô tả lại"*. | Xác định đây là **2 Value Proposition chính** trên giao diện Customer Chat. |
| **2/4** chọn tự động thu thập thông tin; **2/4** chọn routing; **2/4** chọn theo dõi trạng thái. | Giữ trong MVP, nhưng đứng sau tính năng giải thích lỗi và sinh Case Brief. |
| **Trong 4 phản hồi thăm dò, cả 4 người đều chọn ít nhất một tình huống rủi ro hoặc nhạy cảm cần kết nối nhân viên ngay**, như an toàn, cứu hộ, xe không thể di chuyển, lỗi nghiêm trọng, khiếu nại hoặc chi phí. | **Human-in-the-Loop (HITL)** là yêu cầu cốt lõi (Core Requirement), không phải tính năng phụ. |

### 2.3. Vấn đề của các Bên liên quan (Problem Statement)
1. **Khách hàng sở hữu xe điện (EV):** Khi gặp vấn đề phát sinh (trụ sạc, cảnh báo taplo, thắc mắc dịch vụ), khách hàng thường hoang mang, cung cấp thông tin rời rạc hoặc thiếu các dữ kiện kỹ thuật then chốt (dòng xe, mã lỗi, vị trí trụ sạc).
2. **Tổng đài & Nhân viên Dịch vụ (Service Staff):** Mất nhiều thời gian chat/hỏi lặp đi lặp lại các thông tin cơ bản trước khi tạo được phiếu điều phối. Thông tin bàn giao giữa các ca trực dễ bị thiếu sót.
3. **Mục tiêu MVP:**
   * Hỗ trợ khách hàng gửi thông tin nhanh chóng, có gợi ý trả lời nhanh (Quick Replies).
   * Tự động làm rõ tối đa 2 lượt để thu thập đủ các trường dữ liệu bắt buộc (Required Fields).
   * Tổng hợp thành **Case Brief** chuẩn hóa bàn giao cho Staff Dashboard.
   * Đảm bảo an toàn 100%: Mọi case rủi ro/khẩn cấp hoặc khiếu nại đều được chuyển cho nhân viên xử lý.

---

## 3. Phạm vi Dự án (MVP Scope)

### 3.1. In-Scope (Làm trong MVP)
* **Intake & Triage 4 Intents:**
  1. `Charging/Battery` *(Làm sâu)*: Xử lý sự cố không nhận sạc, sạc ngắt quãng, lỗi giao tiếp trụ sạc.
  2. `Service/Incident` *(Làm sâu)*: Cảnh báo đèn taplo, rùa vàng, lỗi 12V, lỗi điều hòa, hướng dẫn dịch vụ.
  3. `Sales/General Info` *(Làm tinh gọn)*: Hỏi thông số xe, hướng dẫn tính năng trên ứng dụng VinFast (RAG FAQ có trích dẫn nguồn công khai đã kiểm chứng).
  4. `Complaint/Feedback` *(Làm tinh gọn)*: Tiếp nhận phản ánh thái độ, chậm trễ $\rightarrow$ Thu thập brief tối thiểu và chuyển thẳng Staff.
* **Quy tắc AI Clarification chuẩn hóa:**
  * Tối đa **2 lượt** Agent chủ động hỏi làm rõ. Mỗi lượt chỉ gửi **1 câu hỏi** có thể gom nhiều dữ kiện, kèm **Quick Replies** để khách trả lời nhanh.
  * **Xử lý khi thiếu thông tin sau 2 lượt:**
    * Nếu sau 2 lượt vẫn thiếu dữ kiện $\rightarrow$ Tạo Case $\rightarrow$ Trạng thái `Status = Needs Information`.
    * Case này vẫn xuất hiện trong Staff Queue với nhãn **"Thiếu thông tin"** để Staff có thể tự tiếp quản hoặc gửi tin nhắn yêu cầu bổ sung.
  * **Khi đã đủ dữ kiện và Agent sinh Brief hoàn chỉnh:** Vòng đời trạng thái diễn ra theo thứ tự: `New` $\rightarrow$ `Staff Reviewing` $\rightarrow$ `In Progress`.
* **Thông báo Phản hồi An toàn:** *"Hệ thống đã ghi nhận sự cố và tạo hồ sơ hỗ trợ. Thông tin sẽ được hiển thị cho nhân viên xử lý trên môi trường demo; vui lòng theo dõi cập nhật trên giao diện này."*
* **Case Brief Generation:** Tự động tóm tắt: *Vấn đề chính, Thông số xe (Model, Pin %), Mã lỗi/Hiện tượng, Mức độ ưu tiên, Hành động đề xuất cho Staff*.
* **Cơ chế HITL (Human-in-the-Loop):** Staff Dashboard để Review, Chỉnh sửa (Edit), Duyệt (Approve), Điều phối (Reroute), Đóng phiếu.
* **Trích dẫn nguồn RAG công khai:** Trích dẫn nguồn tài liệu VinFast chính thức đã được kiểm chứng (kèm URL, ngày kiểm chứng, model áp dụng). Chỉ trả lời nội dung chính sách khi đã có tài liệu nguồn xác thực.
* **Bàn giao Dịch vụ Hiện hữu:** Đối với nhu cầu đặt lịch bảo dưỡng/sửa chữa hoặc xem trạng thái xe, hệ thống hướng dẫn khách hàng sử dụng các chức năng đã có trên **Ứng dụng VinFast chính thức**.

### 3.2. Out-of-Scope (KHÔNG làm trong MVP)
* ❌ Không tích hợp Telemetry trực tiếp qua CAN Bus / OBD-II xe thật.
* ❌ Không làm hệ thống đặt lịch hẹn (Booking Engine) riêng biệt (Ứng dụng VinFast đã có tính năng đặt lịch và theo dõi dịch vụ).
* ❌ Không tự động hoàn tiền, xuất hóa đơn tài chính hoặc cam kết bồi thường mà không qua duyệt của Staff.
* ❌ Không tích hợp Voice AI / Call Center thật (tập trung Web Chat text/rich UI).
* ❌ **Không thu thập và không lưu trữ PII thật:** Không yêu cầu họ tên, SĐT thật, CCCD, VIN hay biển số thật. MVP chỉ sử dụng `session_id`, `mock_customer_id`, `vehicle_model` (optional), `vehicle_code_mock` (optional dạng `VF-SF-xxxxx`). Tên và SĐT chỉ dùng trong seed demo nội bộ.

---

## 4. Ba (03) Demo Flow Trọng tâm cho MVP

| Flow # | Tên kịch bản | Intent chính | Điểm mấu chốt cần Demo |
| :---: | :--- | :--- | :--- |
| **Flow 1** *(Vertical Slice - Ưu tiên số 1)* | **Sự cố trụ sạc không nhận súng / lỗi kết nối** | `Charging/Battery` | Khách báo lỗi sạc $\rightarrow$ AI Clarify (max 2 lượt kèm quick replies) $\rightarrow$ Sinh Case Brief $\rightarrow$ Đẩy sang Staff Console $\rightarrow$ Staff duyệt/cập nhật $\rightarrow$ Khách theo dõi trạng thái. |
| **Flow 2** | **Cảnh báo rủi ro an toàn / Đèn taplo** | `Service/Incident` | Khách báo lỗi $\rightarrow$ Kiểm tra Safety Rule (Rùa vàng + Cao tốc / Nguy cơ an toàn) $\rightarrow$ Gán `CRITICAL` + Hotline cứu hộ $\rightarrow$ Tạo ticket khẩn cho Kỹ thuật viên. |
| **Flow 3** | **Tra cứu FAQ hướng dẫn tính năng & Dịch vụ** | `Sales/General Info` | Hỏi tính năng/dịch vụ $\rightarrow$ RAG trích dẫn URL chính thức kèm ngày kiểm chứng $\rightarrow$ Hướng dẫn vào luồng dịch vụ trên Ứng dụng VinFast. |

---

## 5. Mục tiêu Đánh giá (Evaluation Targets)

Các chỉ số dưới đây là **mục tiêu thử nghiệm và benchmark (Targets)** để nhóm tối ưu mô hình, không phải kết quả đã đạt:

1. **Độ chính xác phân loại Intent (Intent Triage Accuracy Target):** Mục tiêu $\ge 90\%$ trên bộ test benchmark `eval/datasets/triage_cases_v1.jsonl`.
2. **Tính đầy đủ của Case Brief (Brief Completeness Target):** Mục tiêu $\ge 95\%$ các trường bắt buộc theo từng intent.
3. **Độ bao phủ phát hiện sự cố khẩn cấp (Critical Case Recall Target):** Mục tiêu $100\%$ case có nguy cơ an toàn kích hoạt cảnh báo khẩn cấp và chuyển Staff Queue.
4. **Độ trung thực RAG (RAG Grounded Rate Target):** $100\%$ câu trả lời FAQ có trích dẫn link nguồn công khai hợp lệ đã kiểm chứng, không bịa đặt thông tin.
5. **Tiến độ Vertical Slice (Flow 1 E2E):** Chạy thông suốt trước mốc **29/09/2026**.
