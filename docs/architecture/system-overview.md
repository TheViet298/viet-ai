# System Overview Architecture

> **Người phụ trách chính:** Long (AI/Agent) + Triển (Backend)  
> **Cập nhật lần cuối:** 2026-09-24  
> **Trạng thái:** Draft / In Review

---

## 1. Kiến trúc Tổng thể Hệ thống (High-Level Architecture)

```mermaid
graph TD
    subgraph Client Layer ["1. Client Layer (Frontend Web)"]
        CustomerUI["Customer Chat & Intake UI\n(Khách hàng gửi yêu cầu / theo dõi Case)"]
        StaffConsole["Service Agent Console\n(Nhân viên duyệt Brief / xử lý Ticket)"]
    end

    subgraph APILayer ["2. API & Gateway Layer (FastAPI)"]
        CustomerAPI["Customer REST Endpoints\n(/api/v1/chat, /api/v1/cases/status)"]
        StaffAPI["Staff REST Endpoints\n(/api/v1/staff/tickets, /api/v1/staff/actions)"]
        AuthMiddleware["Authentication & Rate Limiter"]
    end

    subgraph AgentLayer ["3. AI Agent & Reasoning Layer (Google Gemini)"]
        TriageEngine["Triage & Classifier Engine\n(Intent & Priority & Safety Filter)"]
        ClarificationEngine["Clarification Generator\n(Hỏi làm rõ có cấu trúc)"]
        BriefGenerator["Case Brief Synthesizer\n(Chuẩn hóa schema nghiệp vụ)"]
        RAGRouter["RAG Query Engine\n(ChromaDB / Vector Search)"]
    end

    subgraph DataLayer ["4. Data & Storage Layer"]
        PostgreSQL[("Relational DB (PostgreSQL / SQLite)\n- Cases, Messages, Staff Logs")]
        VectorStore[("Vector Store (ChromaDB / Qdrant)\n- Public VinFast Docs Chunks")]
    end

    %% Connections
    CustomerUI -->|HTTPS / JSON| CustomerAPI
    StaffConsole -->|HTTPS / JSON| StaffAPI

    CustomerAPI --> AuthMiddleware
    StaffAPI --> AuthMiddleware

    AuthMiddleware --> TriageEngine
    AuthMiddleware --> PostgreSQL

    TriageEngine -->|Tra cứu FAQ| RAGRouter
    RAGRouter --> VectorStore
    TriageEngine -->|Cần làm rõ| ClarificationEngine
    TriageEngine -->|Đủ dữ liệu| BriefGenerator

    BriefGenerator -->|Lưu Ticket & Brief| PostgreSQL
    StaffAPI -->|Đọc / Cập nhật Ticket| PostgreSQL
```

---

## 2. Các Thành phần Cốt lõi (Core Components)

### 2.1. Client Layer (Frontend)
* **Customer Chat App:** 
  * Cung cấp giao diện chat trực quan, hiển thị tin nhắn, gợi ý trả lời nhanh (quick replies), màn hình thông tin Ticket & Trạng thái.
  * **Quy tắc an toàn:** Không bao giờ hiển thị suy luận nội bộ (Chain-of-Thought) của AI cho khách hàng.
* **Service Agent Console (Staff):**
  * Dashboard quản lý ticket theo thời gian thực (Ticket Queue).
  * Chi tiết Ticket (Ticket Detail): Xem Case Brief do AI trích xuất, xem lại đoạn chat của khách, các nút thao tác `Approve`, `Edit`, `Reroute`, `Close`.

### 2.2. API Layer (FastAPI / Python)
* Tiếp nhận và xác thực request từ Client.
* Kiểm soát phân quyền (Role-based: Customer vs Staff).
* Chuyển tiếp payload vào Agent Pipeline và lưu vết dữ liệu vào cơ sở dữ liệu.

### 2.3. AI Agent Layer (Google Gemini SDK)
* **Triage Engine:** Phân loại 4 Intent (`Charging/Battery`, `Service/Incident`, `Sales/General Info`, `Complaint/Feedback`).
* **Hard Rule & Safety Guard:** Kiểm tra từ khóa khẩn cấp trước khi cho LLM xử lý.
* **Brief Generator:** Định dạng thông tin rời rạc thành JSON Case Brief có cấu trúc nghiêm ngặt.

### 2.4. Data & Storage Layer
* **Database quan hệ (SQLite cho MVP / PostgreSQL cho Prod):** Lưu trữ bảng `cases`, `messages`, `case_briefs`, `staff_audit_logs`.
* **Vector Database:** Lưu trữ embeddings các tài liệu công khai chính thức của VinFast phục vụ RAG.
