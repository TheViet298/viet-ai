# Architecture Document — VinFast ServiceFlow AI (VFO2O-18)

## 1. System Overview

VinFast ServiceFlow AI là Web Support Hub tích hợp AI Agent (Web-first theo ADR-004; Zalo, Email, Hotline chưa nằm trong phạm vi MVP) hỗ trợ tiếp nhận, phân loại 4 nhóm Intent, làm rõ dữ kiện có ngữ cảnh, tra cứu cẩm nang kỹ thuật & chính sách VinFast, tổng hợp **Case Brief** chuẩn hóa và hỗ trợ Reviewer điều phối (routing) chính xác đến bộ phận tiếp nhận tiếp theo.

## 2. Architecture Diagrams & Chi tiết Luồng Hoạt động

Hệ thống được trực quan hóa qua 3 sơ đồ hoạt động chính thức tại thư mục [`docs/architecture/`](docs/architecture/):
1. **[Activity Tổng thể MVP Main (Khách hàng — Hệ thống AI — Staff)](docs/architecture/Activity%20diagram%20system.jpg):** Thể hiện trọn vẹn luồng từ Web Support Hub, phân tích ảnh, LangGraph state machine, gợi ý điểm dịch vụ đến bảng điều khiển Staff Console và vòng đời ticket.
2. **[Sơ đồ Hoạt động Toàn hệ thống (End-to-End System Activity)](docs/architecture/serviceflow-system-activity.png):** 3 làn bơi nghiệp vụ mô tả chi tiết từ xác thực RBAC, Guardrails, duyệt Case Brief đến CSAT / Đóng hồ sơ.
3. **[Sơ đồ Xử lý Một lượt Hội thoại Khách hàng](docs/architecture/serviceflow-customer-activity.png):** Mô tả thứ tự rẽ nhánh xử lý trong một turn chat (`POST /api/v1/customer/chat`).

```mermaid
graph TB
    subgraph Frontend[Frontend Clients - Next.js 14]
        WC[Web Chat Client: Khách hàng / Guest tối đa 5 lượt]
        Track[Track Case: xác nhận, mở lại, CSAT]
        Console[Service Agent Console: Reviewer HITL]
    end

    subgraph Backend[FastAPI & Agent Gateway]
        API[FastAPI Routes: /customer, /staff, /auth, /public]
        Agent[LangGraph StateGraph Engine]
        Guard[Safety, PII Sanitizer & Boundary Guardrails]
        Worker[Auto-close Worker: Resolved quá 72h thành Closed]
    end

    subgraph Intelligence[AI Services & Local Models]
        LLM[LLM Gateway: openai/gpt-5.6 qua LiteLLM, tùy chọn Gemini]
        Vision[Vision: gpt-6-luna hoặc Gemini & CarDD Runtime]
        RAG[VinFast Knowledge Retrieval Service]
        LocalONNX[Local ONNX Model: multilingual-e5-small]
    end

    subgraph Storage[Data Layer]
        DB[(Ticket DB: Users, Sessions, Cases, Messages, Briefs, Audit Logs, Feedback)]
        VectorStore[(ChromaDB: VF Manuals, FAQs, Warranty)]
    end

    WC -->|HTTP REST| API
    Track -->|HTTP REST| API
    Console -->|HTTP REST| API
    API --> Agent
    Agent --> Guard
    Guard --> LLM
    API --> Vision
    Agent --> RAG
    RAG --> VectorStore
    VectorStore <--> LocalONNX
    Agent --> DB
    Worker --> DB
    Agent --> Console
```

## 3. Core Components & State Machine (`src/agents/graph.py`)

```mermaid
graph TD
    START([Bắt đầu lượt chat]) --> intake[intake_node: Chuẩn hóa text & context]
    intake --> safety[safety_node: Kiểm tra Hard Safety & Policy]

    safety -->|is_critical HOẶC vi phạm| case_brief[case_brief_node: Tạo Brief tối thiểu & Hotline]
    safety -->|Tín hiệu CarDD ngoại thất mới| cardd[cardd_review_node: Đánh giá hư hại & xác nhận]
    safety -->|Hội thoại thông thường| triage[triage_node: Intent + Priority + Confidence]

    cardd -->|Tiếp tục phân loại| triage
    cardd -->|Hoàn thành phản hồi ảnh| END([Kết thúc lượt])

    triage -->|Out_of_Scope| END
    triage -->|is_general_query| general[general_node: Trả lời xã giao / chào hỏi]
    general --> END

    triage -->|is_rag_query| rag[rag_node: Tra cứu ChromaDB & trích dẫn]
    rag -->|Có nguồn kiểm chứng| END
    rag -->|is_no_source| case_brief

    triage -->|Thiếu dữ kiện sự cố & lượt <= 2| clarify[clarify_node: Hỏi gom 1 câu + Quick Replies]
    clarify -->|Chờ khách bổ sung| END
    clarify -->|Sau 2 lượt vẫn thiếu (Needs Information)| case_brief

    triage -->|Đủ dữ kiện HOẶC Confidence < 0.60| case_brief

    case_brief --> console[Service Agent Console: Hàng đợi duyệt HITL]
    console --> reviewer{Reviewer: Approve / Edit / Reroute / Request Info / Resolve}
    reviewer -->|Request Info| needinfo[Needs Information: chờ khách bổ sung]
    reviewer -->|Approve / Reroute| dispatch[In Progress: điều phối kỹ thuật]
    dispatch --> resolved[Resolved: chờ khách xác nhận]
    reviewer -->|Resolve| resolved
    resolved -->|Khách xác nhận Đã được hỗ trợ| closed[Closed + đánh giá CSAT]
    resolved -->|Khách báo Vẫn chưa giải quyết| reopened[Reopened: quay lại hàng đợi Staff]
    resolved -->|Không phản hồi quá 72h| autoclose[Auto-close bởi worker nền]
    autoclose --> closed
```

### 3.1 Intent Router & Specialized Briefs
Hệ thống phân hóa rõ ràng theo 4 nhóm intent (`Charging/Battery`, `Service/Incident`, `Sales/General Info`, `Complaint/Feedback`; backend vẫn chấp nhận alias ngắn `Sales`, `Complaint`), tránh áp đặt luồng kỹ thuật cho mọi yêu cầu:
1. **Bán hàng / Tư vấn xe (Sales/General Info):** Tra cứu thông số xe, phiên bản, giá bán, gói pin $\to$ Tạo **Sales Inquiry Brief**.
2. **Sạc & Pin (Charging):** Hướng dẫn sạc, giải đáp chính sách thuê/mua pin, cách xử lý trụ sạc $\to$ Tạo **Charging Support Brief**.
3. **Khiếu nại & Góp ý (Complaint/Feedback):** Đánh giá mức độ nhạy cảm/bức xúc (Sentiment analysis), ghi nhận phản ánh $\to$ Tạo **Complaint Case Brief** (ưu tiên chuyển người xử lý).
4. **Dịch vụ & Sự cố kỹ thuật (Service/Incident):** Kiểm tra dữ kiện (dòng xe, mã lỗi, tình trạng pin, vị trí), thực hiện Contextual Clarification nếu thiếu, tra cứu cẩm nang kỹ thuật và sinh **Service Brief** chi tiết cho xưởng/cứu hộ.

### 3.2 Human-in-the-Loop (HITL) & Dispatching
- **Agent không tự ý dispatch:** Agent chỉ tạo Case Brief và đề xuất Routing.
- **Reviewer là người quyết định cuối cùng:** Cố vấn dịch vụ / Manager kiểm tra trên **Service Agent Console**, chọn một trong các thao tác *Approve / Edit Brief / Reroute / Request Info / Resolve / Close / Reopen* (`POST /staff/tickets/{id}/actions`) rồi mới thực hiện dispatch chính thức đến bộ phận tương ứng. Mọi thao tác được ghi vào `staff_audit_logs` kèm snapshot trạng thái trước và sau.
- **Xác nhận, CSAT & tự động đóng:** Khi ticket ở `Resolved`, khách chọn *Đã được hỗ trợ* ($\to$ `Closed`) hoặc *Vẫn chưa giải quyết* ($\to$ `Reopened`, quay lại hàng đợi Staff). Sau khi đã `Resolved`/`Closed`, khách có thể gửi đánh giá CSAT 1–5 sao (mỗi case một đánh giá, được sửa trong 7 ngày; 1–2 sao có thể kèm `reason_tags`). Job nền trong `src/services/case_lifecycle.py` quét định kỳ (10 phút/lần, và cả mỗi lần Staff tải `GET /staff/tickets`) và tự động chuyển `Resolved` $\to$ `Closed` nếu quá 72 giờ khách không phản hồi, ghi `staff_audit_logs` với `staff_id = SYSTEM_AUTO_CLOSE` và một `case_updates` do `SYSTEM` tạo; Console hiển thị nhãn auto-close qua trường `is_auto_closed`.
- **Cảnh báo khẩn cấp:** Với các tình huống nguy hiểm (mất phanh, bốc khói, chết máy trên cao tốc), Agent cung cấp ngay hướng dẫn an toàn tiêu chuẩn và số Hotline cứu hộ chính thức; không tự xác nhận là đã điều xe cứu hộ đến nơi.

### 3.3 Database & Storage Layer
Lưu trữ theo chuẩn Data Model (`users`, `cases`, `messages`, `case_briefs`, `staff_audit_logs`, `attachments`, `customer_feedback`, `case_locations`, `case_updates`, cùng `chat_sessions`, `chat_request_records` cho lease phiên và chống gửi trùng; chi tiết xem `docs/architecture/data-model.md`):
- `user_id` / `session_id`: Chủ sở hữu case (tài khoản đăng nhập hoặc phiên guest); quyền truy cập kiểm tra qua `check_case_ownership`
- `intent`: `Charging/Battery`, `Service/Incident`, `Sales/General Info`, `Complaint/Feedback`
- `priority`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
- `confidence_score`: Điểm tự tin của LLM trong phân loại/trích xuất (0.0 - 1.0)
- `suggested_action`: Hành động gợi ý cho nhân viên kỹ thuật / CSKH
- `captured_fields`: Dữ liệu trích xuất có cấu trúc (mã lỗi, trụ sạc, SoC,...)
- `staff_audit_logs`: Ghi nhận thao tác của Staff, của Customer (reopen) và của hệ thống (auto-close) kèm snapshot trước/sau (phục vụ evaluation)
- `customer_feedback`: Đánh giá CSAT 1–5 sao, nhận xét, `reason_tags` (duy nhất cho mỗi case)
- `safety_status` / `incident_version`: Theo dõi khách đã xác nhận an toàn cho case khẩn cấp đang mở
- `status`: Vòng đời ticket thống nhất: `New` $\to$ `Needs Information` $\to$ `Staff Reviewing` $\to$ `In Progress` $\to$ `Resolved` $\to$ `Closed` (và `Reopened`)

## 4. Guardrails & Safety Thresholds

1. **Safety Trigger:** Ngắt hỏi ngay lập tức, kích hoạt cảnh báo an toàn và cung cấp Hotline 1900-232389 khi phát hiện từ khóa nguy hiểm sinh mạng/an toàn giao thông; tạo Case `CRITICAL` đẩy thẳng lên đầu hàng đợi Staff (`Staff Reviewing`).
2. **Sensitive Complaint Guardrail:** Tự động gắn cờ escalate với các khiếu nại gay gắt hoặc tranh chấp bảo hành/tài chính không chắc chắn.
3. **Confidence Thresholds & HITL Routing (theo Triage & HITL Rules):**
   - **Câu hỏi FAQ / tra cứu (`is_rag_query`):** Chỉ sinh câu trả lời khi có trích dẫn hợp lệ và $\text{Score} \ge 0.60$; ngưỡng truy hồi tài liệu là khoảng cách vector $\le 0.70$ (`RAG_MAX_DISTANCE`). Nếu không có nguồn kiểm chứng thì chuyển thành Case Brief để chuyên viên xử lý. Intent `Sales/General Info` có `rag_score < 0.70` bắt buộc qua Staff.
   - **$\text{Score} \ge 0.60$ & Thiếu trường:** Kích hoạt Contextual Clarifier (tối đa 2 lượt kèm Quick Replies); sau 2 lượt vẫn thiếu thì tạo Case trạng thái `Needs Information`.
   - **$\text{Score} < 0.60$ HOẶC priority `HIGH`/`CRITICAL` HOẶC thuộc nhóm Sự cố kỹ thuật / Sạc & Pin / Khiếu nại:** Bắt buộc 100% qua Human-in-the-Loop trên Console với trạng thái `Staff Reviewing` (`is_hitl_mandatory`).
4. **Out-of-Scope Filter:** Lịch sự từ chối các yêu cầu ngoài phạm vi xe điện và dịch vụ VinFast.