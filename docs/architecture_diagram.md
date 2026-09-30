# Architecture Diagram — VinFast ServiceFlow AI (VFO2O-18)

## 1. System Overview (Web Support Hub & Service Flow)

```mermaid
graph TB
    subgraph ClientLayer[Web Support Hub]
        Guest[Guest: Landing / FAQ / Policy]
        WC[Customer: Web Chat text + ảnh / My Cases]
        Staff[Staff: Queue + Ticket Detail]
    end

    subgraph APILayer[FastAPI Backend Gateway]
        Router[API Router /api/v1/cases]
        Auth[Authentication + RBAC]
        Upload[Attachment Upload / Private Storage]
    end

    subgraph AgentLayer[LangGraph AI Core]
        IntakeNode[intake_node: Chuẩn hóa text, ảnh & context]
        VisionNode[image_analysis_node: OCR/Vision tín hiệu sơ bộ]
        TriageNode[triage_node: Intent + Priority + Confidence]
        SafetyCheck{Safety trigger, sensitive case<br/>hoặc confidence thấp?}
        IntentRoute{Intent Router}
        
        SalesBranch[Sales FAQ & Inquiry Brief]
        ChargingBranch[Charging FAQ & Support Brief]
        ComplaintBranch[Complaint Sentiment & Case Brief]
        
        subgraph ServiceSubGraph[Nhánh Dịch vụ & Sự cố Kỹ thuật]
            SlotCheck{Đủ dữ kiện cần thiết?}
            ClarifyNode[Contextual Clarifier]
            ServiceRAG[VinFast Technical Knowledge RAG]
            ServiceBriefNode[Service Brief Generator]
        end
        
        CaseBriefGen[Case Brief Aggregator]
    end

    subgraph DataLayer[Data & Knowledge Base]
        DB[(Ticket DB: user, case, message, attachment, brief)]
        VDB[(ChromaDB: Cẩm nang VF, FAQ, Bảo hành chính hãng)]
    end

    subgraph HITLLayer[Human-in-the-Loop Review & Dispatch]
        Console[Service Agent Console]
        ReviewerAction{Reviewer: Approve / Edit / Escalate}
        Dispatch[Dispatching tới Sales, Service, Charging hoặc CSKH]
    end

    Guest --> Auth
    WC --> Upload
    Upload --> VisionNode
    ClientLayer --> Router
    Router --> Auth
    Auth --> IntakeNode
    VisionNode --> IntakeNode
    IntakeNode --> TriageNode
    
    TriageNode --> SafetyCheck
    SafetyCheck -- Yes (Rủi ro/Nhạy cảm/Low Conf) --> Console
    
    SafetyCheck -- No --> IntentRoute
    IntentRoute -- Sales --> SalesBranch
    IntentRoute -- Charging --> ChargingBranch
    IntentRoute -- Complaint --> ComplaintBranch
    IntentRoute -- Service/Incident --> SlotCheck
    
    SlotCheck -- Chưa đủ dữ kiện --> ClarifyNode
    ClarifyNode -.->|Gửi câu hỏi làm rõ| WC
    
    SlotCheck -- Đã đủ dữ kiện --> ServiceRAG
    ServiceRAG <--> VDB
    ServiceRAG --> ServiceBriefNode
    
    SalesBranch --> CaseBriefGen
    ChargingBranch --> CaseBriefGen
    ComplaintBranch --> CaseBriefGen
    ServiceBriefNode --> CaseBriefGen
    
    CaseBriefGen --> DB
    CaseBriefGen --> Console
    Staff --> Console
    Console --> ReviewerAction
    ReviewerAction --> Dispatch
```

---

## 2. LangGraph Detailed State Machine

```mermaid
graph TD
    START([Input text và/hoặc ảnh từ Web]) --> intake[intake_node: Chuẩn hóa nội dung và context]
    intake --> image{Có ảnh?}
    image -->|Có| vision[image_analysis_node: OCR/Vision, evidence sơ bộ]
    image -->|Không| triage
    vision --> triage[triage_node: Intent + Priority + Confidence]

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

---

## 3. Component Details & Responsibility Matrix

| Component | Technology | Chỉnh lại theo kiến trúc chuẩn |
|---|---|---|
| **Vector DB** | ChromaDB / FAISS | Lưu trữ tài liệu chính hãng, FAQ xe điện, chính sách bảo hành, cẩm nang hướng dẫn sử dụng xe VinFast |
| **LLM Inference** | LLM API hỗ trợ Structured Output | Cấu hình linh hoạt theo môi trường (`gpt-4o-mini`, `gpt-4o`, `gemini-1.5-flash`, v.v.) phục vụ phân loại intent, trích xuất slot, tóm tắt brief |
| **Guardrails & Safety** | Rule Engine + Sentiment + Guard Prompts | Bổ sung **confidence threshold**, bắt **complaint sensitive case**, **safety emergency trigger** và chính sách từ chối yêu cầu ngoài phạm vi |
<!-- update info from feature/ai-long branch: merge giữ nguyên cả hai phiên bản để nhóm review sau. -->
<!-- Hai phần bên dưới có thể khác nhau về trạng thái, phạm vi hoặc số liệu; chưa chọn một phiên bản thay cho phiên bản còn lại. -->

<!-- Phiên bản feature/ai-khoi -->
| **Database** | SQLite (MVP) / PostgreSQL | Lưu trữ đầy đủ: `source_channel`, `intent`, `priority`, `confidence_score`, `suggested_action`, `captured_fields`, `reviewer_feedback`, `status` |

<!-- Phiên bản feature/ai-long -->
| **Attachment / Vision** | Private storage + OCR/Vision API | Lưu ảnh táp-lô; trích xuất tín hiệu sơ bộ để hỏi context, không chẩn đoán kỹ thuật |
| **Database** | SQLite (MVP) / PostgreSQL | Lưu user/role, case, message, attachment, intent, priority, brief, audit log, ticket status |
| **Console (HITL)** | React / Next.js / Tailwind UI | Service Agent Console — **Reviewer là người quyết định cuối cùng** với escalation, chỉnh sửa brief và routing trước khi dispatch |
