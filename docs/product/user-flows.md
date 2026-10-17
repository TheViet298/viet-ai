# User Flows Specification (Customer & Staff)

> **Người phụ trách chính:** Việt (Product Lead)  
> **Cập nhật lần cuối:** 2026-10-17  
> **Trạng thái:** Approved (Đã bổ sung Sequence Diagrams chi tiết cho toàn bộ luồng nghiệp vụ cốt lõi)

---

## 1. Customer User Flow

**Access flow:** Guest xem Landing/FAQ/Policy và được chat tư vấn tối đa 5 lượt/phiên. Khi cần tải ảnh, tạo/theo dõi hồ sơ sự cố hoặc chạm ngưỡng 5 lượt, hệ thống yêu cầu Đăng nhập / Đăng ký tài khoản Customer (Username + Password). Customer chỉ xem được hồ sơ của chính mình; Staff sử dụng tài khoản nội bộ được cấp sẵn.

```mermaid
flowchart TD
    Start([Guest xem Landing / FAQ / Policy]) --> GuestChat[Chat FAQ/tư vấn: tối đa 5 lượt]
    GuestChat --> NeedCase{Cần tạo/theo dõi case, tải ảnh hoặc hết 5 lượt?}
    NeedCase -->|Có| Login[Login / Register Customer: Username + Password]
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

### 1.1 Chi tiết Luồng Hồ Sơ Thiếu Dữ Kiện & Vòng lặp Bổ sung (Needs Information Loop)

Khi khách hàng báo sự cố kỹ thuật thông thường (không đe dọa an toàn) nhưng thiếu dữ kiện bắt buộc (dòng xe, mã lỗi, vị trí trạm/trụ sạc), hệ thống áp dụng cơ chế giới hạn 2 lượt hỏi và vòng lặp bổ sung 2 chiều giữa Khách hàng và Nhân viên:

```mermaid
sequenceDiagram
    autonumber
    actor Customer as Khách hàng (Customer)
    participant Chat as Trợ lý Chat AI (/chat)
    participant Core as Backend & DB (Case/Brief)
    participant Track as Yêu cầu của tôi (/track-case)
    actor Staff as Nhân viên Kỹ thuật (/console)

    Note over Customer,Chat: Giai đoạn 1: AI làm rõ tối đa 2 lượt
    Customer->>Chat: Báo sự cố kỹ thuật (chưa đủ dữ kiện)
    Chat-->>Customer: Lượt 1: Hỏi làm rõ (kèm chips gợi ý)
    Customer->>Chat: Trả lời nhưng vẫn thiếu dữ kiện
    Chat-->>Customer: Lượt 2: Hỏi làm rõ lần cuối
    Customer->>Chat: Phản hồi nhưng vẫn chưa đủ thông tin

    Note over Chat,Core: Giai đoạn 2: Tạo Case 'Needs Information'
    Chat->>Core: Tự động lập Case (Status: Needs Information, Priority: MEDIUM)
    Chat-->>Customer: Thông báo mã Case-ID, chuyển hàng đợi nhân viên hỗ trợ
    Core-->>Staff: Ticket xuất hiện tại Console với cờ "Thiếu dữ kiện"

    Note over Customer,Staff: Giai đoạn 3: Vòng lặp tương tác bổ sung (Song song)
    par Lựa chọn A: Khách tự bổ sung qua Chat
        Customer->>Chat: Tải ảnh táp-lô/màn hình sạc hoặc gõ thêm mã lỗi, trạm sạc
        Chat->>Core: Vision AI & NLP trích xuất dữ kiện -> Cập nhật CaseBrief
        Core->>Core: Dữ kiện đầy đủ -> Tự động chuyển Case sang "Staff Reviewing"
        Core-->>Staff: Xóa cờ "Thiếu dữ kiện", cập nhật bảng phân tích AI
    and Lựa chọn B: Khách theo dõi qua Trang Hồ sơ & Staff chỉ đạo
        Customer->>Track: Mở xem tiến trình Case tại /track-case
        Track-->>Customer: Hiển thị bước "Xác minh - Làm rõ" + Hộp nhắc "CẦN THÔNG TIN"
        alt Staff gửi yêu cầu bổ sung (REQUEST_INFO)
            Staff->>Core: Action: REQUEST_INFO (kèm lời nhắn hướng dẫn cụ thể)
            Core-->>Track: Hiển thị ghi chú của Staff tại mục "Ghi chú từ Cố vấn Kỹ thuật"
        else Staff gọi điện thoại trao đổi trực tiếp
            Staff->>Customer: Gọi điện thoại Hotline theo SĐT trên hồ sơ
            Staff->>Core: Action: EDIT_BRIEF (tự tay điền thông tin thu thập được)
        end
    end

    Note over Staff,Core: Giai đoạn 4: Duyệt và điều phối xử lý
    Staff->>Core: Action: APPROVE (Duyệt phương án kỹ thuật)
    Core->>Core: Chuyển trạng thái sang "In Progress"
    Core-->>Track: Tiến trình cập nhật sang bước 3: "Xử lý"
```

#### Quy tắc nghiệp vụ chi tiết:
1. **Dừng hỏi tự động sau 2 lượt (`max_clarification_turns = 2`):** Tránh trải nghiệm "hỏi cung" khó chịu cho khách hàng khi khách không nhớ hoặc không biết thông tin kỹ thuật chuyên sâu.
2. **Phân loại mức độ ưu tiên:** Case `Needs Information` luôn có mức ưu tiên `Priority = MEDIUM` (không kích hoạt cảnh báo nguy hiểm khẩn cấp, không hiển thị banner tấp xe vào lề nguy hiểm).
3. **Cơ chế tự động nâng cấp trạng thái (Auto-Promotion):** Nếu khách hàng quay lại gửi ảnh táp-lô hoặc nhắn tin bổ sung đủ dữ kiện vào phiên chat, hệ thống tự động bóc tách và chuyển trạng thái từ `Needs Information` sang `Staff Reviewing` mà không bắt khách phải tạo lại ca mới.
4. **Kênh trao đổi hai chiều:**
   - Khách xem chỉ đạo và ghi chú của nhân viên tại trang `/track-case` (thông qua `CaseUpdate` từ `REQUEST_INFO`).
   - Nhân viên tại `/console` có thể dùng `REQUEST_INFO` để gửi lời nhắn, hoặc dùng `EDIT_BRIEF` để trực tiếp điền dữ kiện sau khi gọi hotline cho khách.

---

### 1.2 Chi tiết Luồng Cứu hộ Khẩn cấp, Xác nhận An toàn & Chia sẻ Vị trí (Critical Safety & Location Consent)

Khi khách hàng báo các dấu hiệu đe dọa trực tiếp tới an toàn vận hành (bốc khói, mùi khét, mất phanh, tai nạn hoặc hiện đèn rùa vàng khi đang chạy trên cao tốc/quốc lộ), hệ thống lập tức ngắt quy trình hỏi đáp thông thường để ưu tiên bảo vệ an toàn cho người ngồi trên xe:

```mermaid
sequenceDiagram
    autonumber
    actor Customer as Khách hàng (Customer)
    participant Chat as Giao diện Chat (/chat)
    participant Core as Backend & Safety Guard
    participant Track as Theo dõi Hồ sơ (/track-case)
    actor Staff as Đội Cứu hộ / Kỹ thuật (/console)

    Note over Customer,Core: Giai đoạn 1: Phát hiện nguy hiểm & Cắt ngang luồng hỏi đáp (Pre-empt)
    Customer->>Chat: Báo sự cố nguy hiểm (bốc khói, mất phanh, rùa vàng trên cao tốc...)
    Chat->>Core: Gửi tin nhắn và/hoặc ảnh táp-lô
    Core->>Core: Safety Guard kích hoạt cờ CRITICAL -> Lập ngay Case (bỏ qua hỏi làm rõ 2 lượt)
    Core-->>Chat: Trả về CASE_CREATED (show_emergency_banner = true, request_location = true)
    Core-->>Staff: Đẩy Ticket CRITICAL lên đỉnh hàng đợi (Top of Queue)

    Note over Customer,Chat: Giai đoạn 2: Hướng dẫn an toàn tức thời & Xác nhận trạng thái (Safety Ack)
    Chat-->>Customer: Hiển thị Sticky Banner Đỏ (Hotline 1900-232389) + Hướng dẫn xử lý an toàn
    Customer->>Chat: Bấm nút "Tôi đã ở vị trí an toàn" trên Banner (hoặc tại /track-case)
    Chat->>Core: POST /cases/{id}/safety-ack (safety_status = customer_reported_safe)
    Core-->>Chat: Thu gọn Banner đỏ thành thanh trạng thái an toàn màu xanh/vàng
    Core-->>Staff: Cập nhật huy hiệu "Khách xác nhận đã an toàn" trên Ticket Detail

    Note over Customer,Track: Giai đoạn 3: Xin quyền vị trí (Consent-first, Timeout 8s)
    Chat-->>Customer: Hiển thị thẻ Location Consent (3 lựa chọn minh bạch)
    alt Khách chọn "Dùng vị trí hiện tại (GPS)"
        Chat->>Chat: Gọi Browser Geolocation (Giới hạn chờ tối đa 8 giây)
        alt Lấy GPS thành công (<= 8s)
            Chat->>Core: POST /customer/location (status = CONSENTED, lat/lng)
            Core-->>Chat: Mở Split-view Bản đồ (55/45) + Gợi ý Trạm cứu hộ/Xưởng gần nhất
        else Quá 8s (trong hầm/mất sóng) hoặc bị chặn quyền
            Chat-->>Customer: Tự động chuyển sang ô "Nhập khu vực thủ công" (Không làm treo UI)
        end
    else Khách chọn "Nhập khu vực thủ công"
        Customer->>Chat: Nhập vị trí (VD: "Km 20 Cao tốc Long Thành")
        Chat->>Core: POST /customer/location (status = MANUAL, location_label)
        Core-->>Staff: Hiển thị vị trí khách nhập trong Case Detail
    else Khách chọn "Bỏ qua"
        Chat->>Core: Ghi nhận status = NOT_SHARED (Tiếp tục hỗ trợ bình thường)
    end
```

#### Quy tắc nghiệp vụ & Lưu ý thiết kế:
1. **Ưu tiên tính mạng hơn dữ kiện (`Safety Pre-emption`):** Ngay khi nhận diện từ khóa hoặc tín hiệu nguy hiểm, AI không hỏi vặn lại dòng xe hay mã lỗi mà lập tức tạo hồ sơ mức `CRITICAL`, ghim cảnh báo đỏ kèm nút gọi nhanh Hotline Cứu hộ 24/7 (`1900-232389`).
2. **Xác nhận an toàn hai chiều (`Safety Acknowledgement`):** Nút *"Tôi đã ở vị trí an toàn"* giúp giảm áp lực thị giác cho khách hàng (thu gọn banner đỏ sau khi đã đỗ xe an toàn), đồng thời báo ngay cho điều phối viên trên Console biết tình trạng hiện tại của chủ xe.
3. **Quyền riêng tư vị trí & Chống treo giao diện (`8s GPS Timeout` - ADR-005):** Hệ thống tuyệt đối không tự động bóc tách tọa độ GPS ngầm từ EXIF ảnh chụp. Nếu khách bấm chia sẻ GPS khi đang ở tầng hầm hoặc khu vực sóng yếu, sau đúng **8 giây** giao diện tự động mở ô nhập tay để khách gõ tên đường/cột mốc mà không bị kẹt màn hình.

---

### 1.3 Chi tiết Luồng Chuyển tiếp Khách vãng lai sang Tài khoản Khách hàng (Guest-to-Customer Atomic Handoff)

Để khách hàng có thể trải nghiệm trợ lý AI ngay từ trang chủ mà không gặp rào cản đăng nhập sớm, đồng thời vẫn bảo toàn trọn vẹn mạch hội thoại khi phát sinh sự cố cần lập hồ sơ, hệ thống vận hành cơ chế chuyển giao phiên nguyên tử (`ADR-006`):

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng (Guest -> Customer)
    participant UI as Giao diện Web (/ , /chat, /login)
    participant API as Backend API (/customer/chat, /auth)
    participant DB as Database (chat_sessions, messages, cases)

    Note over User,DB: Giai đoạn 1: Trải nghiệm Khách vãng lai (Tối đa 5 lượt hỏi đáp)
    User->>UI: Truy cập Landing Page hoặc bấm câu hỏi mẫu (Quick Prompts)
    UI->>API: POST /customer/chat (guest_session_id, không cần Token)
    API->>DB: Khởi tạo phiên Guest (user_id = NULL) & Đếm số lượt hỏi
    API-->>UI: Trả lời tư vấn / FAQ + Hiển thị số lượt hỏi còn lại (remaining_guest_messages)

    Note over User,DB: Giai đoạn 2: Chạm ngưỡng cần định danh (Hết 5 lượt / Tải ảnh / Lập hồ sơ)
    alt Khách hỏi vượt quá 5 lượt hoặc bấm Tải ảnh / Gặp sự cố cần tạo Case
        UI-->>User: Hiển thị thông báo mời Đăng nhập / Đăng ký để lưu hồ sơ & bảo mật thông tin
        User->>UI: Đăng nhập hoặc Đăng ký tài khoản (Username + Password)
        UI->>API: POST /auth/login (hoặc /auth/register)
        API-->>UI: Cấp JWT Access Token + Thông tin xe mặc định trên hồ sơ (VD: VF8)
    end

    Note over User,DB: Giai đoạn 3: Tiếp quản phiên chat liền mạch (Atomic Session Claim)
    UI->>API: Gửi tin nhắn tiếp theo kèm JWT Token + guest_session_id cũ
    API->>DB: Atomic UPDATE chat_sessions SET user_id = current_user.id WHERE id = session_id AND user_id IS NULL
    API->>DB: Đồng bộ quyền sở hữu toàn bộ Messages & Attachments trong phiên sang Customer
    API-->>UI: Tiếp tục mạch hội thoại trước đó (không phải gõ lại từ đầu)
```

#### Quy tắc nghiệp vụ & Lưu ý bảo mật:
1. **Giới hạn 5 lượt cho Khách vãng lai (`Guest Quota`):** Khách chưa đăng nhập được hỏi tối đa 5 lượt cho các nhu cầu tra cứu thông số xe, giá bán, chính sách pin và trạm sạc. Các tính năng tạo dữ liệu nhạy cảm (tải ảnh sự cố, lập hồ sơ kỹ thuật, xem lịch sử `/track-case`) yêu cầu tài khoản định danh.
2. **Tiếp quản phiên không đứt quãng (`Seamless Context Carry-over`):** Khi khách đăng nhập ở giữa cuộc trò chuyện, toàn bộ lịch sử tin nhắn vừa trao đổi ở chế độ Guest được gắn tự động vào tài khoản vừa đăng nhập, giúp AI nhớ ngay dòng xe và triệu chứng khách vừa kể.
3. **Chống chiếm đoạt phiên (`Anti-Hijacking`):** Thao tác gán chủ sở hữu phiên tại Database chỉ thực thi thành công khi `user_id IS NULL`. Nếu một tài khoản khác cố tình truyền `session_id` đã thuộc về người dùng khác, hệ thống lập tức từ chối và trả mã lỗi `404` để chống dò quét dữ liệu.

---

### 1.4 Chi tiết Luồng Nhận diện Ảnh Đa phương thức (Vision OCR Táp-lô/Trụ sạc & Ngoại thất CarDD)

Thay vì bắt khách hàng phải tự đọc và gõ lại các mã lỗi kỹ thuật phức tạp trên màn hình xe hoặc trụ sạc, hệ thống tích hợp luồng xử lý ảnh đa phương thức tự động phân nhánh theo ngữ cảnh bức ảnh:

```mermaid
sequenceDiagram
    autonumber
    actor Customer as Khách hàng (Customer)
    participant Chat as Giao diện Chat (/chat)
    participant Vision as Vision & Attachment Service
    participant Agent as AI Triage & CarDD Node
    participant DB as Database (attachments, case_briefs)

    Note over Customer,Vision: Giai đoạn 1: Tải ảnh & Phân loại nguồn ảnh tự động
    Customer->>Chat: Chọn ảnh từ máy / điện thoại đính kèm vào khung chat
    Chat->>Vision: POST /customer/attachments (file, image_kind = "auto")
    Vision->>Vision: Kiểm tra định dạng (JPG/PNG/WEBP <= 10MB) & Phân tích sơ bộ
    Vision->>DB: Lưu bản ghi Attachment kèm tín hiệu nhận diện (detected_signals)
    Vision-->>Chat: Trả về attachment_id + Phân loại nhánh ảnh (dashboard / charger / exterior)

    Note over Chat,DB: Giai đoạn 2: Xử lý chuyên biệt theo loại ảnh khi Khách bấm Gửi
    Customer->>Chat: Bấm gửi tin nhắn kèm attachment_id
    alt Nhánh 1: Ảnh Táp-lô hoặc Màn hình Trụ sạc (dashboard / charger)
        Chat->>Agent: Gửi text + Tín hiệu OCR (Mã lỗi CC01/0x41, đèn rùa vàng, % SoC...)
        Agent->>Agent: Tự động điền vào các trường còn thiếu (Slot Filling) mà không bắt khách gõ lại
        Agent->>DB: Đính kèm visual_signals vào CaseBrief để Kỹ thuật viên đối chiếu
        Agent-->>Chat: Xác nhận triệu chứng đọc được từ ảnh + Tạo Case (hoặc hỏi nốt thông tin thiếu)
    else Nhánh 2: Ảnh Ngoại thất / Thân vỏ xe (exterior - CarDD Flow)
        Chat->>Agent: Kích hoạt luồng đánh giá ngoại thất (cardd_review_node)
        Agent->>Agent: Khoanh vùng dấu hiệu trầy xước, móp méo, nứt vỡ đèn/kính bên ngoài
        Agent->>DB: Lập Case Dịch vụ đồng sơn/bảo hiểm kèm tóm tắt hư hại ngoại quan
        Agent-->>Chat: Trả kết quả nhận diện bề mặt + Khuyến nghị đưa xe tới Xưởng Dịch vụ kiểm tra
    end
```

#### Quy tắc nghiệp vụ & Ranh giới an toàn:
1. **Tự động bóc tách thông số (`Visual Slot-Filling`):** Với ảnh chụp bảng đồng hồ táp-lô hoặc màn hình trụ sạc, Vision AI trích xuất mã lỗi (`error_code`), đèn cảnh báo (`warning_symbol`) và mức pin (`SoC`) để điền thẳng vào `CaseBrief`, giúp rút ngắn số lượt hỏi làm rõ.
2. **Ranh giới chẩn đoán ảnh ngoại thất (`CarDD Guardrail`):** Với ảnh chụp thân vỏ xe (`exterior`), AI chỉ mô tả các dấu hiệu hư hại nhìn thấy được trên bề mặt (trầy xước, móp cản, nứt kính) để hỗ trợ cố vấn dịch vụ chuẩn bị tiếp nhận; **tuyệt đối không phán đoán tình trạng khung gầm, hệ thống treo hay pin cao áp bên trong** khi chỉ dựa vào ảnh chụp.

---

## 2. Staff Console User Flow

```mermaid
flowchart TD
    StaffLogin([Nhân viên Dịch vụ đăng nhập Dashboard]) --> Dashboard[Dashboard Summary: Critical / Reviewing / Needs Info / Resolved]
    Dashboard --> ViewQueue[Xem Ticket Queue: Filter theo Priority / Status / Intent]
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
    
    InProgress --> ResolveTicket[Hoàn tất xử lý kỹ thuật → Trạng thái: Resolved]
    ResolveTicket --> ConfirmCustomer{Customer xác nhận kết quả?}
    ConfirmCustomer -->|Xác nhận| CloseTicket[Trạng thái: Closed]
    ConfirmCustomer -->|Vẫn còn lỗi| ReopenTicket[Trạng thái: Reopened → Quay lại Queue]

    ViewQueue --> CaseHistory[Lịch sử case: Resolved / Closed / Reopened]
    CaseHistory --> ViewDetail
    ViewDetail --> RoutingDirectory[Chọn Routing Directory demo]
    RoutingDirectory --> Reroute
```

---

### 2.1 Chi tiết Luồng Thẩm định của Chuyên viên & Khép kín Vòng đời Hồ sơ (Staff HITL, Handover & 72h Lifecycle)

Sau khi AI tạo hồ sơ tóm tắt (`CaseBrief`), quy trình xử lý tuân thủ nguyên tắc **Con người giữ quyền quyết định cuối cùng (Human-in-the-Loop)** và chỉ đóng hồ sơ khi có sự nghiệm thu từ phía khách hàng (hoặc hết thời hạn chờ 72 giờ):

```mermaid
sequenceDiagram
    autonumber
    actor Staff as Chuyên viên Kỹ thuật (/console)
    participant Core as Backend & Lifecycle Scheduler
    participant Track as Trung tâm Hỗ trợ (/track-case)
    actor Customer as Khách hàng (Customer)

    Note over Staff,Core: Giai đoạn 1: Tiếp nhận & Thẩm định Case Brief (Human-in-the-Loop)
    Staff->>Core: Mở Ticket từ Hàng đợi (Ưu tiên CRITICAL -> HIGH -> MEDIUM)
    Core-->>Staff: Hiển thị Case Brief do AI tóm tắt + Lịch sử Chat + Ảnh đính kèm + Vị trí
    alt Dữ kiện đã chuẩn xác
        Staff->>Core: Bấm APPROVE (hoặc EDIT_BRIEF nếu cần tinh chỉnh chẩn đoán)
        Core->>Core: Chuyển trạng thái sang "In Progress"
    else Cần chuyển sang bộ phận chuyên trách khác
        Staff->>Core: Bấm REROUTE (Chọn 1 trong 5 bộ phận: Trạm sạc / Xưởng / CSKH / Sales / Cứu hộ)
        Core->>Core: Ghi nhận lịch sử điều phối & Chuyển trạng thái "In Progress"
    end
    Core-->>Track: Cập nhật thanh tiến trình của khách sang Bước 3: "Đang xử lý"

    Note over Staff,Customer: Giai đoạn 2: Hoàn tất xử lý & Bàn giao kết quả cho Khách
    Staff->>Core: Bấm RESOLVE (Nhập tóm tắt cách khắc phục & hướng dẫn bước tiếp theo)
    Core->>Core: Chuyển trạng thái sang "Resolved" + Ghi mốc thời gian resolved_at
    Core-->>Track: Hiển thị thông báo "Hồ sơ đã được giải quyết" kèm ghi chú của Chuyên viên

    Note over Core,Customer: Giai đoạn 3: Nghiệm thu từ phía Khách hàng hoặc Tự động đóng sau 72h
    alt Khách xác nhận đã khắc phục xong
        Customer->>Track: Bấm "Xác nhận đã giải quyết"
        Track->>Core: POST /cases/{id}/confirm -> Chuyển trạng thái sang "Closed"
        Track-->>Customer: Mở biểu mẫu đánh giá CSAT (1-5 sao + Thẻ lý do nhanh)
        Customer->>Track: Gửi đánh giá -> Lưu vào bảng feedbacks
    else Sự cố tái phát hoặc chưa giải quyết triệt để
        Customer->>Track: Bấm "Vẫn còn lỗi / Yêu cầu hỗ trợ lại" (kèm lý do)
        Track->>Core: POST /cases/{id}/reopen -> Chuyển trạng thái sang "Reopened" (Tăng incident_version)
        Core-->>Staff: Đẩy lại Ticket vào Hàng đợi xử lý kèm lý do mở lại của khách
    else Khách không phản hồi sau 72 giờ kể từ khi Resolved
        Core->>Core: Background Job (quét định kỳ) tự động chuyển "Resolved" -> "Closed" (Auto-Closed)
        Core-->>Track: Ghi nhận đóng hồ sơ tự động (Khách vẫn có quyền Reopen nếu lỗi lặp lại)
    end
```

#### Quy tắc nghiệp vụ & Lưu ý vận hành:
1. **AI chỉ gợi ý, Chuyên viên quyết định (`HITL Governance`):** Mọi bản tóm tắt `CaseBrief` do AI sinh ra đều gắn cờ `is_edited_by_staff = false` ban đầu. Chuyên viên có thể sửa lại nội dung chẩn đoán (`EDIT_BRIEF`) hoặc điều phối lại (`REROUTE`) về đúng một trong 5 đơn vị nghiệp vụ trước khi xử lý.
2. **Duyệt hàng đợi tốc độ cao kèm nút Hoàn tác (`Auto-Advance & Undo`):** Trên giao diện `/console`, ngay khi chuyên viên bấm Duyệt (`Approve`) hoặc Hoàn tất (`Resolve`), hệ thống tự động chuyển sang ca tiếp theo trong hàng đợi để tiết kiệm thao tác, đồng thời hiển thị thanh thông báo **Hoàn tác (Undo)** phòng trường hợp thao tác nhầm.
3. **Quy tắc đóng hồ sơ 2 lớp & Tự động đóng sau 72 giờ (`ADR-005`):** Nhân viên chỉ được chuyển hồ sơ tới trạng thái `Resolved`. Quyền chuyển sang `Closed` thuộc về khách hàng sau khi nghiệm thu kết quả. Nếu sau **72 giờ** kể từ thời điểm `resolved_at` mà khách không phản hồi, tiến trình nền (`case_lifecycle.py`) sẽ tự động đóng hồ sơ nhưng vẫn giữ nguyên quyền `Reopen` nếu sự cố tái diễn.

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

#### Nguyên tắc hiển thị & Bảo mật quyền riêng tư:
* **Cô lập dữ liệu cá nhân (`Strict Ownership`):** Tại tab **Yêu cầu của tôi**, khách hàng chỉ truy cập được các hồ sơ thuộc quyền sở hữu của `user_id` đang đăng nhập.
* **Tiết lộ thông tin theo lớp (`Progressive Disclosure`):** Để tránh gây rối mắt cho chủ xe, giao diện chi tiết hồ sơ ưu tiên hiển thị thanh tiến trình 4 bước và lời nhắn mới nhất từ Cố vấn Kỹ thuật; phần lịch sử đoạn chat gốc và bảng thông số kỹ thuật chi tiết được thu gọn mặc định trong các khối mở rộng (Accordion).
* **Tách biệt kho tri thức công khai:** Tab **Tình huống thường gặp** chỉ hiển thị các bài hướng dẫn chuẩn hóa kèm trích dẫn nguồn chính thức của VinFast; tuyệt đối không hiển thị hồ sơ thô, hình ảnh, vị trí hay đoạn chat của các khách hàng khác.

---

## 4. Staff Console Navigation & Workspace Architecture

Không gian làm việc của Chuyên viên Kỹ thuật tại `/console` được tổ chức thành 7 phân khu chức năng (chia làm 2 nhóm chính), cho phép xử lý hàng đợi, tra cứu quy chuẩn kỹ thuật và kiểm thử AI trên cùng một màn hình duy nhất:

```mermaid
flowchart TB
    subgraph StaffWorkspace["Không gian làm việc Nhân viên Kỹ thuật (/console)"]
        direction LR
        subgraph CoreOps["1. Nhóm Điều hành & Xử lý Sự cố"]
            TabQueue["Hàng đợi xử lý (Queue)\nMaster-Detail 2 cột + Bộ lọc nhanh"]
            TabOverview["Tổng quan (Overview)\nThống kê SLA, Critical, Khối lượng ca"]
            TabRouting["Danh bạ Điều phối (Routing)\n5 Bộ phận chuyên trách P0"]
            TabHistory["Lịch sử Hồ sơ (History)\nTra cứu ca Resolved / Closed / Reopened"]
        end

        subgraph SupportTools["2. Nhóm Công cụ Tri thức & Kiểm thử"]
            TabKnowledge["Kho Tri thức (Knowledge Hub)\nTài liệu chuẩn VinFast & Nguồn trích dẫn RAG"]
            TabPreview["Thử nghiệm Trợ lý (Customer Preview)\nSandbox kiểm thử bóc tách Intent & RAG"]
            TabProfile["Hồ sơ Ca trực (Staff Profile)\nThông tin nhân sự & Cài đặt phiên"]
        end
    end

    TabOverview -->|Click vào nhóm chỉ số| TabQueue
    TabQueue <-->|Chọn điều phối đơn vị| TabRouting
    TabQueue -->|Ca hoàn tất / đóng| TabHistory
    TabHistory -->|Xem lại biên bản & CSAT| TabQueue
    TabKnowledge -.->|Đối chiếu quy chuẩn kỹ thuật| TabQueue
```

#### Giải thích & Lưu ý vận hành:
* **Môi trường thử nghiệm cô lập (`Sandbox Isolation` tại Customer Preview):** Tab **Customer Preview** cho phép nhân viên đóng vai khách hàng nhắn tin thử để kiểm tra cách AI bóc tách Intent và trích dẫn nguồn từ **Knowledge Hub**. Mọi tin nhắn tại đây sử dụng mã phiên độc lập (`staff_preview_*`), hoàn toàn tách biệt với dữ liệu và hàng đợi của khách hàng thật.
* **Đồng bộ trạng thái qua URL (`Deep-linking`):** Khi nhân viên chọn một hồ sơ trong hàng đợi, đường dẫn trình duyệt tự động đồng bộ theo dạng `/console?case=CASE-...`, hỗ trợ chia sẻ nhanh đường dẫn hồ sơ giữa các ca trực hoặc bấm nút Back/Forward trên trình duyệt mà không mất trạng thái đang làm việc.

---

## 5. Exception Flows & Guardrails

| Tình huống ngoại lệ | Xử lý của Hệ thống | Trạng thái Ticket |
| :--- | :--- | :--- |
| **Phát hiện từ khóa Nguy hiểm (Cháy, Mất phanh, Tai nạn, Rùa vàng cao tốc)** | Cắt đứt luồng chat thông thường, hiển thị cảnh báo an toàn lập tức (Hotline 1900-232389), tạo Case Brief mức `CRITICAL` và đẩy lên đỉnh hàng đợi Staff. | `Staff Reviewing` (Priority: CRITICAL) |
| **Khách hỏi thao tác can thiệp điện cao áp / tự tháo lắp nguy hiểm** | Từ chối hướng dẫn tự tháo sửa các bộ phận điện cao áp/pin/cầu chì để bảo đảm an toàn và quyền lợi bảo hành; khuyên khách đưa xe tới Xưởng Dịch vụ hoặc kết nối Cố vấn Kỹ thuật. | `N/A` (hoặc giữ nguyên Case hiện tại) |
| **Khách gửi thông tin ngoài phạm vi (Out-of-Scope) / Hãng xe khác** | AI từ chối lịch sự, nhắc lại phạm vi chuyên trách về xe điện và dịch vụ VinFast, kèm gợi ý các chủ đề hỗ trợ hợp lệ. | `N/A` |
| **RAG không tìm thấy tài liệu phù hợp** | Tuyệt đối không phỏng đoán. Phản hồi: *"Hiện tại hệ thống chưa có dữ liệu chính xác về vấn đề này. Em đã tạo yêu cầu để chuyên viên VinFast kiểm tra lại cho mình."* | `Staff Reviewing` |
| **Khách chưa cung cấp đủ thông tin sau 2 lượt hỏi** | Dừng hỏi tự động, tạo Case để nhân viên hỗ trợ trực tiếp và mở vòng lặp bổ sung dữ kiện 2 chiều (xem Mục 1.1). | `Needs Information` |

