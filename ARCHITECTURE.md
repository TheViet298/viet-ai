# Architecture Document — VinFast ServiceFlow AI (VFO2O-18)

## 1. System Overview

VinFast ServiceFlow AI là hệ thống AI Agent tổng đài đa kênh (Web Chat thật, cùng mô phỏng Zalo, Email, Hotline call transcript) hỗ trợ tiếp nhận, phân loại 4 nhóm Intent, làm rõ dữ kiện có ngữ cảnh, tra cứu cẩm nang kỹ thuật & chính sách VinFast, tổng hợp **Case Brief** chuẩn hóa và hỗ trợ Reviewer điều phối (routing) chính xác đến bộ phận tiếp nhận tiếp theo.

## 2. Architecture Diagram

```mermaid
graph TB
    subgraph Frontend[Frontend Clients]
        WC[Web Chat Client]
        Sim[Omnichannel Mock Simulator: Zalo / Email / Hotline]
        Console[Service Agent Console - Reviewer HITL]
    end

    subgraph Backend[FastAPI & Agent Gateway]
        API[FastAPI Routes /api/v1/cases]
        Agent[LangGraph StateGraph Engine]
        Guard[Safety, Sensitive Sentiment & Confidence Guardrails]
    end

    subgraph Intelligence[AI Services]
        LLM[LLM API with Structured Output]
        RAG[VinFast Knowledge Retrieval Service]
    end

    subgraph Storage[Data Layer]
        DB[(Ticket DB: channel, intent, priority, confidence, brief, feedback)]
        VectorStore[(ChromaDB - VF Manuals, FAQs, Warranty)]
    end

    WC -->|HTTP REST / WebSocket| API
    Sim -->|API Simulator| API
    Console -->|HTTP REST| API
    API --> Agent
    Agent --> Guard
    Guard --> LLM
    Agent --> RAG
    RAG --> VectorStore
    Agent --> DB
    Agent --> Console
```

## 3. Core Components & Intent Routing

```mermaid
graph TD
    START([Input từ Web Chat hoặc kênh mô phỏng]) --> intake[intake_node: Chuẩn hóa nội dung và context]
    intake --> triage[triage_node: Intent + Priority + Confidence]

    triage --> safety{Safety trigger, sensitive case hoặc confidence thấp?}
    safety -- Yes --> hitl[HITL: Escalate reviewer hoặc nhân viên phù hợp]

    safety -- No --> route{Intent router}

    route -- Sales --> sales_rag[Sales FAQ hoặc Sales Brief]
    route -- Charging --> charging_rag[Charging FAQ hoặc Charging Brief]
    route -- Complaint --> complaint_brief[Complaint Case Brief]
    route -- Service Incident --> slot{Đủ dữ kiện cần thiết?}

    slot -- No --> clarify[Contextual Clarifier]
    clarify --> wait([Chờ phản hồi khách trên Channel Session])
    wait --> intake

    slot -- Yes --> service_rag[VinFast Knowledge Retrieval]
    service_rag --> service_brief[Service Brief Generator]

    sales_rag --> case_brief[Case Brief]
    charging_rag --> case_brief
    complaint_brief --> case_brief
    service_brief --> case_brief

    case_brief --> console[Service Agent Console]
    console --> reviewer{Approve, Edit hoặc Escalate}
    reviewer --> dispatch[Routing tới Sales, Service, Charging hoặc CSKH]
```

### 3.1 Intent Router & Specialized Briefs
Hệ thống phân hóa rõ ràng theo 4 nhóm intent, tránh áp đặt luồng kỹ thuật cho mọi yêu cầu:
1. **Bán hàng / Tư vấn xe (Sales):** Tra cứu thông số xe, phiên bản, giá bán, gói pin $\to$ Tạo **Sales Inquiry Brief**.
2. **Sạc & Pin (Charging):** Hướng dẫn sạc, giải đáp chính sách thuê/mua pin, cách xử lý trụ sạc $\to$ Tạo **Charging Support Brief**.
3. **Khiếu nại dịch vụ (Complaint):** Đánh giá mức độ nhạy cảm/bức xúc (Sentiment analysis), ghi nhận phản ánh $\to$ Tạo **Complaint Case Brief** (ưu tiên chuyển người xử lý).
4. **Dịch vụ & Sự cố kỹ thuật (Service/Incident):** Kiểm tra dữ kiện (dòng xe, mã lỗi, tình trạng pin, vị trí), thực hiện Contextual Clarification nếu thiếu, tra cứu cẩm nang kỹ thuật và sinh **Service Brief** chi tiết cho xưởng/cứu hộ.

### 3.2 Human-in-the-Loop (HITL) & Dispatching
- **Agent không tự ý dispatch:** Agent chỉ tạo Case Brief và đề xuất Routing.
- **Reviewer là người quyết định cuối cùng:** Cố vấn dịch vụ / Manager kiểm tra trên **Service Agent Console**, bấm *Approve / Edit / Escalate* rồi mới thực hiện dispatch chính thức đến bộ phận tương ứng.
- **Cảnh báo khẩn cấp:** Với các tình huống nguy hiểm (mất phanh, bốc khói, chết máy trên cao tốc), Agent cung cấp ngay hướng dẫn an toàn tiêu chuẩn và số Hotline cứu hộ chính thức; không tự xác nhận là đã điều xe cứu hộ đến nơi.

### 3.3 Database & Storage Layer
Lưu trữ toàn diện theo chuẩn Data Model (`cases`, `case_briefs`, `staff_audit_log`):
- `source_channel`: `web_chat`, `zalo`, `email`, `hotline_transcript`
- `intent`: `Charging/Battery`, `Service/Incident`, `Sales`, `Complaint`
- `priority`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
- `confidence_score`: Điểm tự tin của LLM trong phân loại/trích xuất (0.0 - 1.0)
- `suggested_action`: Hành động gợi ý cho nhân viên kỹ thuật / CSKH
- `captured_fields`: Dữ liệu trích xuất có cấu trúc (mã lỗi, trụ sạc, SoC,...)
- `reviewer_feedback` (`staff_audit_log`): Ghi nhận thao tác & đánh giá của Staff (phục vụ evaluation)
- `status`: Vòng đời ticket thống nhất: `New` $\to$ `Needs Information` $\to$ `Staff Reviewing` $\to$ `In Progress` $\to$ `Resolved` $\to$ `Closed` (và `Reopened`)

## 4. Guardrails & Safety Thresholds

1. **Safety Trigger:** Ngắt hỏi ngay lập tức, kích hoạt cảnh báo an toàn và cung cấp Hotline 1900-232389 khi phát hiện từ khóa nguy hiểm sinh mạng/an toàn giao thông; tạo Case `CRITICAL` đẩy thẳng lên đầu hàng đợi Staff (`Staff Reviewing`).
2. **Sensitive Complaint Guardrail:** Tự động gắn cờ escalate với các khiếu nại gay gắt hoặc tranh chấp bảo hành/tài chính không chắc chắn.
3. **Confidence Thresholds & HITL Routing (theo Triage & HITL Rules):**
   - **$\ge 0.85$ & Intent = FAQ** (kèm RAG similarity $\ge 0.70$): Tự động trả lời FAQ kèm link nguồn trích dẫn.
   - **$0.60 \le \text{Score} < 0.85$ & Thiếu trường:** Kích hoạt Contextual Clarifier (tối đa 2 lượt kèm Quick Replies); sau 2 lượt vẫn thiếu thì tạo Case trạng thái `Needs Information`.
   - **$\text{Score} < 0.60$ HOẶC thuộc nhóm Sự cố kỹ thuật / Sạc & Pin / Khiếu nại:** Bắt buộc 100% qua Human-in-the-Loop trên Console với trạng thái `Staff Reviewing`.
4. **Out-of-Scope Filter:** Lịch sự từ chối các yêu cầu ngoài phạm vi xe điện và dịch vụ VinFast.
