# UI Flow Diagram & Navigation

> **Người phụ trách chính:** Việt (UI/UX Lead)  
> **Cập nhật lần cuối:** 2026-09-24  
> **Trạng thái:** Draft / In Review

---

## 1. Sơ đồ Click-Flow Toàn diện

```mermaid
flowchart TD
    %% Public / Access
    Guest["Guest: Landing / FAQ / Policy"] -->|Chat tối đa 5 lượt| GuestChat["Guest Chat FAQ / tư vấn"]
    GuestChat -->|Cần case / hết limit| Login["Login / Register Customer"]

    %% Customer App
    subgraph CustomerApp ["Giao diện Khách hàng (Customer Experience)"]
        M1["SCR-01: Customer Chat / Intake\n(Nhập text và/hoặc upload ảnh)"]
        M2["SCR-02: AI Clarification View\n(Chọn gợi ý mã lỗi / trụ sạc)"]
        M3["SCR-03: Case Status & Result\n(Xem Case ID, Tiến độ & Hướng dẫn)"]
        SupportCenter["Customer Support Center\n(Yêu cầu của tôi / Tình huống thường gặp)"]
        FAQView["FAQ Answer Modal\n(Xem câu trả lời + Trích dẫn URL)"]

        Login --> M1
        M1 -->|Ảnh| Vision["AI đang đọc cảnh báo...\nOCR/Vision sơ bộ"]
        Vision --> M2
        M1 -->|Intent cần địa điểm| Map["Service Map Preview\nDùng vị trí / Nhập khu vực / Bỏ qua"]
        Map --> M3
        M1 -->|Hỏi thông tin chung| FAQView
        M1 -->|Sự cố kỹ thuật thiếu field| M2
        M2 -->|Khách bấm chọn hoặc gửi tin nhắn| M1
        M1 -->|AI tạo Case thành công| M3
        M3 -->|Theo dõi cập nhật từ Staff| M3
        M3 -->|Xem tất cả yêu cầu| SupportCenter
        SupportCenter -->|Chọn case của tôi| M3
    end

    %% Staff App
    subgraph StaffApp ["Giao diện Nhân viên (Service Agent Console)"]
        S1["SCR-04A: Ticket Queue Dashboard\n(Danh sách ticket, Bộ lọc, Cờ ưu tiên)"]
        S2["SCR-04B: Ticket Detail View\n(Case Brief, Lịch sử Chat, AI Đề xuất)"]
        S_Edit["Modal: Chỉnh sửa Case Brief"]
        S_Reroute["Modal: Điều phối Đội hỗ trợ"]

        S1 -->|Click chọn Ticket| S2
        S2 -->|Click 'Edit Brief'| S_Edit
        S_Edit -->|Lưu Brief mới| S2
        S2 -->|Click 'Reroute'| S_Reroute
        S_Reroute -->|Xác nhận điều phối| S1
        S2 -->|Click 'Approve'| S1
        S2 -->|Click 'Close Ticket'| S1
    end

    %% Đồng bộ dữ liệu
    M3 -.->|Polling / WebSocket đồng bộ trạng thái| S2
    S2 -.->|Customer Update: kết quả / next step| M3
```

---

## 2. Quy tắc Điều hướng & Trải nghiệm (UX Rules)

1. **Không chặn người dùng (Non-blocking):** Khi AI đang xử lý Triage, màn hình Chat phải hiển thị trạng thái `AI đang phân tích thông tin...` với hiệu ứng skeleton / pulse nhẹ, không làm đơ giao diện.
2. **Cảnh báo khẩn cấp (Emergency Banner):** Nếu case bị đánh dấu `CRITICAL`, giao diện Customer xuất hiện banner đỏ cố định ở đỉnh màn hình: *"Đây là tình huống khẩn cấp. Vui lòng giữ an toàn và gọi ngay Hotline 1900-232389."*
3. **Phản hồi trạng thái tức thời cho Staff:** Mỗi khi Staff bấm `Approve` hoặc `Edit`, nút bấm hiển thị trạng thái loading spinner ngắn (< 500ms) và chuyển sang ticket tiếp theo trong hàng đợi tự động (Next ticket in queue).
4. **Location consent:** Map không hiển thị mặc định. Chỉ hiển thị khi triage cần địa điểm; Customer chọn `Dùng vị trí hiện tại`, `Nhập khu vực` hoặc `Bỏ qua`.
5. **Support Center:** Case search, timeline và chat history chỉ áp dụng case của Customer đăng nhập. “Tình huống thường gặp” là knowledge content đã biên soạn/ẩn danh.
