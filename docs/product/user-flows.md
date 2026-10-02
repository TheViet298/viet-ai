# User Flows Specification (Customer & Staff)

> **Người phụ trách chính:** Việt (Product Lead)  
> **Cập nhật lần cuối:** 2026-09-24  
> **Trạng thái:** In Review (Đã cập nhật Clarification Bounds và App Handoff)

---

## 1. Customer User Flow

**Access flow:** Guest xem Landing/FAQ/Policy và được chat tối đa 5 lượt/phiên. Khi cần tạo/theo dõi case hoặc hết limit, hệ thống yêu cầu Login/Register Customer bằng SĐT + OTP demo. Customer chỉ xem case của mình; Staff dùng tài khoản seed/invite.

```mermaid
flowchart TD
    Start([Guest xem Landing / FAQ / Policy]) --> GuestChat[Chat FAQ/tư vấn: tối đa 5 lượt]
    GuestChat --> NeedCase{Cần tạo/theo dõi case hoặc hết limit?}
    NeedCase -->|Có| Login[Login / Register Customer: SĐT + OTP demo]
    NeedCase -->|Không| Intake
    Login --> Intake[Nhập text và/hoặc upload ảnh]
    Intake --> Image{Có ảnh?}
    Image -->|Có| Vision[OCR/Vision nhận diện dấu hiệu sơ bộ]
    Image -->|Không| CheckSafety
    Vision --> CheckSafety
    Intake --> CheckSafety{Phát hiện rủi ro an toàn khẩn cấp?}
    
    %% Emergency Path
    CheckSafety -->|Có: Cháy / Mất phanh / Rùa vàng trên cao tốc| EmergencyFlow[Cảnh báo an toàn ngay + Hotline]
    EmergencyFlow --> CreateCritCase[Tạo Ticket CRITICAL tối thiểu & Chuyển đỉnh Queue Staff]
    CreateCritCase --> LocationConsent{Chia sẻ vị trí?}
    LocationConsent -->|Dùng vị trí / Nhập khu vực| ServiceMap[Hiển thị map & điểm hỗ trợ gần]
    LocationConsent -->|Bỏ qua| TrackStatus
    ServiceMap --> TrackStatus
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
    CreateCase --> LocationNeed{Intent cần địa điểm?}
    LocationNeed -->|Có| LocationCard[Card: Dùng vị trí / Nhập khu vực / Bỏ qua]
    LocationCard --> ServiceMap
    LocationNeed -->|Không| ShowCaseView
    ShowCaseView --> TrackStatus
    TrackStatus --> SupportCenter[Customer Support Center: tìm kiếm case của tôi / timeline / lịch sử chat]
    SupportCenter --> CaseDetail[Xem Customer Update + visual evidence + service point nếu có]
    CaseDetail --> ResolutionChoice{Case Resolved?}
    ResolutionChoice -->|Đã được hỗ trợ| CloseByCustomer[Customer xác nhận → Closed + Feedback]
    ResolutionChoice -->|Vẫn chưa giải quyết| ReopenByCustomer[Customer Reopen → Staff Queue]
```

---

## 2. Staff Console User Flow

```mermaid
flowchart TD
    StaffLogin([Nhân viên Dịch vụ đăng nhập Dashboard]) --> ViewQueue[Xem Ticket Queue: Filter theo Priority / Status / Intent]
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
    ResolveTicket --> ConfirmCustomer{Customer xác nhận kết quả?}
    ConfirmCustomer -->|Xác nhận| CloseTicket[Trạng thái: Closed]
    ConfirmCustomer -->|Vẫn còn lỗi| ReopenTicket[Trạng thái: Reopened $\rightarrow$ Quay lại Queue]
```

---

## 3. Customer Support Center & Privacy Flow

```mermaid
flowchart LR
    Customer[Customer đăng nhập] --> Mine[Tab: Yêu cầu của tôi]
    Mine --> Search[Tìm theo Case ID / từ khóa / trạng thái]
    Search --> Detail[Case Detail: timeline, Customer Update, chat history]
    Customer --> Library[Tab: Tình huống thường gặp]
    Library --> Curated[FAQ/bài viết đã biên soạn + citation]
    Curated --> Agent[Hỏi Agent / tạo case mới]
```

* Customer chỉ truy cập case mà `customer_id` sở hữu.
* Tab `Tình huống thường gặp` không hiển thị raw case, ảnh, vị trí, Case ID, chat history hoặc kết quả xử lý của Customer khác.

---

## 3. Exception Flows & Guardrails

| Tình huống ngoại lệ | Xử lý của Hệ thống | Trạng thái Ticket |
| :--- | :--- | :--- |
| **Phát hiện từ khóa Nguy hiểm (Cháy, Mất phanh, Tai nạn, Rùa vàng cao tốc)** | Cắt đứt luồng chat thông thường, hiển thị cảnh báo an toàn lập tức (Hotline 1900-232389), tạo Case Brief mức `CRITICAL` và đẩy lên đỉnh hàng đợi Staff. | `Staff Reviewing` (Priority: CRITICAL) |
| **Khách gửi thông tin không liên quan / Spam** | AI nhắc nhở lịch sự phạm vi hỗ trợ của trợ lý ảo VinFast. Cho phép thử lại tối đa 3 lần trước khi khóa phiên. | `N/A` |
| **RAG không tìm thấy tài liệu phù hợp** | Tuyệt đối không phỏng đoán. Phản hồi: *"Hiện tại hệ thống chưa có dữ liệu chính xác về vấn đề này. Em đã tạo yêu cầu để chuyên viên VinFast kiểm tra lại cho mình."* | `Staff Reviewing` |
| **Khách chưa cung cấp đủ thông tin sau 2 lượt hỏi** | Dừng hỏi tự động, tạo Case để nhân viên hỗ trợ trực tiếp. | `Needs Information` |
