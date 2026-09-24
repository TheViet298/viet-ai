# User Flows Specification (Customer & Staff)

> **Người phụ trách chính:** Việt (Product Lead)  
> **Cập nhật lần cuối:** 2026-09-24  
> **Trạng thái:** In Review (Đã cập nhật Clarification Bounds và App Handoff)

---

## 1. Customer User Flow

```mermaid
flowchart TD
    Start([Khách truy cập Chat]) --> Intake[Nhập nội dung vấn đề / câu hỏi]
    Intake --> CheckSafety{Phát hiện rủi ro an toàn khẩn cấp?}
    
    %% Emergency Path
    CheckSafety -->|Có: Cháy / Mất phanh / Rùa vàng trên cao tốc| EmergencyFlow[Cảnh báo an toàn ngay + Hotline 1900-232389]
    EmergencyFlow --> CreateCritCase[Tạo Ticket CRITICAL & Chuyển đỉnh Queue Staff]
    CreateCritCase --> TrackStatus[Theo dõi tiến độ từ Staff]
    
    %% Normal Path
    CheckSafety -->|Không| AI_Triage{AI Triage & Phân loại Intent}
    
    %% FAQ Path
    AI_Triage -->|Sales / General Info| CheckRAG{RAG có nguồn tin cậy?}
    CheckRAG -->|Có nguồn trích dẫn| FAQ_Answer[Hiển thị câu trả lời + Link Nguồn + Hướng dẫn App VinFast]
    FAQ_Answer --> IsResolved{Khách hài lòng?}
    IsResolved -->|Có| EndCustomer([Kết thúc phiên])
    IsResolved -->|Cần hỗ trợ thêm| CreateCase[Chuyển tạo Case hỗ trợ]
    
    CheckRAG -->|Không có nguồn / RAG score < 0.70| LowConfMsg[Thông báo chưa có dữ liệu chính thức & Chuyển tạo Case]
    LowConfMsg --> CreateCase
    
    %% Clarification Path (Max 2 turns)
    AI_Triage -->|Charging / Service thiếu trường bắt buộc| ClarifyTurn1[Lượt 1: AI gửi 1 câu hỏi gom dữ kiện + Quick Replies]
    ClarifyTurn1 --> CustomerReply1[Khách chọn hoặc nhập bổ sung]
    CustomerReply1 --> CheckTurn1{Đã đủ thông tin?}
    
    CheckTurn1 -->|Đủ| CreateCase
    CheckTurn1 -->|Vẫn thiếu| ClarifyTurn2[Lượt 2: AI hỏi làm rõ lần cuối + Quick Replies]
    ClarifyTurn2 --> CustomerReply2[Khách phản hồi]
    CustomerReply2 --> CheckTurn2{Đủ hay thiếu?}
    
    CheckTurn2 -->|Đủ| CreateCase
    CheckTurn2 -->|Vẫn thiếu sau 2 lượt| CreateNeedsInfoCase[Tạo Case trạng thái 'Needs Information']
    CreateNeedsInfoCase --> ShowCaseView[Hiển thị Case ID + Thông báo Chuyên viên tiếp quản]
    
    %% Case Creation Path
    CreateCase --> ShowCaseView
    ShowCaseView --> TrackStatus
```

---

## 2. Staff Console User Flow

```mermaid
flowchart TD
    StaffLogin([Nhân viên Dịch vụ mở Dashboard]) --> ViewQueue[Xem Ticket Queue: Filter theo Priority / Status / Intent]
    ViewQueue --> SelectTicket[Chọn Ticket để xử lý]
    SelectTicket --> ViewDetail[Xem Ticket Detail: Case Brief + Lịch sử Chat + AI Đề xuất]
    
    ViewDetail --> StaffAction{Hành động của Staff}
    
    StaffAction -->|Thông tin chuẩn| Approve[Duyệt đề xuất & Chuyển In Progress]
    StaffAction -->|Cần chỉnh sửa| EditBrief[Sửa Case Brief / Điều chỉnh chẩn đoán]
    StaffAction -->|Sai bộ phận| Reroute[Điều phối sang Đội Cứu hộ / Showroom khác]
    StaffAction -->|Cần hỏi thêm khách| AskCustomer[Gửi tin nhắn yêu cầu bổ sung thông tin]
    
    EditBrief --> InProgress[Chuyển trạng thái: In Progress]
    Approve --> InProgress
    Reroute --> InProgress
    AskCustomer --> AwaitingCust[Chuyển trạng thái: Needs Information]
    
    InProgress --> ResolveTicket[Hoàn tất xử lý kỹ thuật $\rightarrow$ Trạng thái: Resolved]
    ResolveTicket --> ConfirmCustomer{Khách xác nhận hài lòng / Hết hạn quy định}
    ConfirmCustomer -->|Xác nhận| CloseTicket[Trạng thái: Closed]
    ConfirmCustomer -->|Vẫn còn lỗi| ReopenTicket[Trạng thái: Reopened $\rightarrow$ Quay lại Queue]
```

---

## 3. Exception Flows & Guardrails

| Tình huống ngoại lệ | Xử lý của Hệ thống | Trạng thái Ticket |
| :--- | :--- | :--- |
| **Phát hiện từ khóa Nguy hiểm (Cháy, Mất phanh, Tai nạn, Rùa vàng cao tốc)** | Cắt đứt luồng chat thông thường, hiển thị cảnh báo an toàn lập tức (Hotline 1900-232389), tạo Case Brief mức `CRITICAL` và đẩy lên đỉnh hàng đợi Staff. | `Staff Reviewing` (Priority: CRITICAL) |
| **Khách gửi thông tin không liên quan / Spam** | AI nhắc nhở lịch sự phạm vi hỗ trợ của trợ lý ảo VinFast. Cho phép thử lại tối đa 3 lần trước khi khóa phiên. | `N/A` |
| **RAG không tìm thấy tài liệu phù hợp** | Tuyệt đối không phỏng đoán. Phản hồi: *"Hiện tại hệ thống chưa có dữ liệu chính xác về vấn đề này. Em đã tạo yêu cầu để chuyên viên VinFast kiểm tra lại cho mình."* | `Staff Reviewing` |
| **Khách chưa cung cấp đủ thông tin sau 2 lượt hỏi** | Dừng hỏi tự động, tạo Case để nhân viên hỗ trợ trực tiếp. | `Needs Information` |
