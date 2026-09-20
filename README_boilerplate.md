# VFO2O-18 VinFast ServiceFlow AI

> AI Agent tiếp nhận yêu cầu hội thoại tự do từ nhiều kênh, hỏi đủ dữ kiện, tạo Service Brief và điều phối đúng bộ phận cho khách hàng Xe Vinfast.

## Vấn đề (Problem)

### Ai đang gặp vấn đề?

- Khách hàng Xe Vinfast gửi yêu cầu qua Web Chat, Zalo, hotline hoặc email khi cần tư vấn xe, hỗ trợ sạc/pin, dịch vụ/sự cố hoặc khiếu nại.
- Nhân viên CSKH và cố vấn dịch vụ phải đọc, phân loại, hỏi thêm thông tin và chuyển case đến đúng bộ phận.
- Reviewer/manager cần kiểm soát các case nhạy cảm, khẩn cấp hoặc bị phân loại sai.

### Pain point

- Yêu cầu từ khách thường ở dạng hội thoại tự do và thiếu dữ kiện cần thiết, ví dụ: loại xe, thời điểm xảy ra vấn đề, mã cảnh báo, tình trạng xe hiện tại hoặc nhu cầu cụ thể.

- Điều này khiến nhân viên phải hỏi lại nhiều lần, khó giữ ngữ cảnh khi khách liên hệ từ nhiều kênh và có nguy cơ chuyển case sai bộ phận. Với case dịch vụ/sự cố, việc thiếu dữ kiện làm quá trình bàn giao đến xưởng hoặc cứu hộ kém hiệu quả.

### Tại sao giải pháp hiện tại chưa đủ?

- Ứng dụng VinFast đã hỗ trợ các tác vụ như: theo dõi xe, cảnh báo lỗi, đặt lịch, cứu hộ và theo dõi dịch vụ. Tuy nhiên, ứng dụng không phải là điểm tiếp nhận duy nhất của khách hàng.

- Các yêu cầu vẫn có thể đến từ hội thoại tự do qua Web Chat, Zalo, hotline hoặc email. Nhóm tập trung vào lớp tiếp nhận và điều phối trước khi khách được đưa vào luồng dịch vụ phù hợp, thay vì xây lại các tính năng có sẵn trên ứng dụng VinFast.

### Giả thuyết cần kiểm chứng

- Nhóm giả thuyết rằng AI Agent có thể giảm mức độ thiếu thông tin trong case, tăng độ chính xác routing và giảm số lượt nhân viên cần hỏi lại khách so với quy trình tiếp nhận thủ công hoặc chatbot FAQ thông thường.

- Các chỉ số sẽ được đánh giá ở MVP gồm: intent/routing accuracy, recall cho case High/Critical, Service Brief completeness và tỷ lệ reviewer cần chỉnh sửa case.

## Giải pháp (Solution)

VinFast ServiceFlow AI là web application hỗ trợ tiếp nhận và điều phối yêu cầu khách hàng đa kênh. Hệ thống không thay thế ứng dụng VinFast, booking, cứu hộ hoặc quy trình sửa chữa hiện có. Hệ thống giúp chuẩn hóa yêu cầu trước khi bàn giao đến đúng nhóm nhân sự.

### Feature 1: Omnichannel Intake and AI Triage

- Khách gửi yêu cầu qua Web Chat. Hệ thống mô phỏng input từ Zalo, email và hotline transcript để kiểm thử luồng đa kênh.

- AI Agent phân loại yêu cầu thành các nhóm: Bán hàng/Tư vấn xe, Dịch vụ và sự cố, Sạc/Pin, Khiếu nại hoặc Ngoài phạm vi. Agent đồng thời đề xuất mức ưu tiên Low, Medium, High hoặc Critical.

### Feature 2: Contextual Clarification and Grounded Response

- Khi thông tin chưa đủ, Agent đặt follow-up questions theo loại yêu cầu để thu thập dữ kiện cần thiết.

- Với câu hỏi đơn giản, Agent truy xuất tài liệu, FAQ hoặc chính sách VinFast đã được phê duyệt để trả lời có nguồn. Với case rủi ro, thiếu căn cứ hoặc mức ưu tiên cao, Agent không tự kết luận mà chuyển sang reviewer.

### Feature 3: Service Brief and Human in the Loop Handoff

- Agent tổng hợp hội thoại thành Service Brief gồm: loại yêu cầu, tóm tắt vấn đề, dữ kiện đã thu thập, mức ưu tiên, bộ phận đề xuất và bước tiếp theo.

- Nhân viên trên Service Agent Console có thể xem inbox, approve, edit, escalate hoặc close ticket. Feedback của reviewer được lưu để đánh giá và cải thiện Agent.


## Target User

- Primary: Khách hàng Xe Vinfast cần hỗ trợ về dịch vụ, sự cố, sạc/pin, khiếu nại hoặc tư vấn xe.
- Secondary: hân viên CSKH, cố vấn dịch vụ và reviewer tiếp nhận/phân luồng case.

## MVP Scope

- Web Chat/Form là kênh tiếp nhận chính.
- Mô phỏng nguồn input từ email, Zalo và hotline transcript.
- Phân loại intent: Bán hàng, Dịch vụ/Sự cố, Sạc/Pin, Khiếu nại.
- Đề xuất priority: Low, Medium, High, Critical.
- Clarification questions.
- Service Brief.
- Reviewer handoff và ticket status mô phỏng.

## Out of Scope

- Tích hợp API hoặc CRM VinFast thật.
- Booking, cứu hộ hoặc thanh toán thật.
- Tích hợp production với Zalo, email và hotline.
- Telemetry, CAN, OBD hoặc chẩn đoán lỗi xe.
- Thay thế ứng dụng VinFast hiện có.

## Tech Stack

| Layer | Technology |
|---|---|
| AI Agent | LangGraph + LLM API |
| Backend | FastAPI + Python 3.11+ |
| Frontend | React/Next.js + TypeScript |
| Database | PostgreSQL hoặc SQLite cho MVP |
| Vector Store | ChromaDB hoặc PostgreSQL pgvector |
| DevOps | Docker + GitHub Actions |
| Deployment | Vercel + Render/Railway |

## AI Components

| Component | Vai trò |
|---|---|
| LLM | Hiểu phản ánh, tóm tắt và sinh câu hỏi làm rõ |
| RAG | Tra cứu tài liệu, FAQ và chính sách chính hãng |
| Rule Engine | Xác định priority và ngưỡng escalation |
| Case Tool | Tạo Service Brief, lưu trạng thái và routing |
| HITL | Reviewer duyệt, sửa hoặc escalation case nhạy cảm |

## Quick Start

```bash
# 1. Clone repo
git clone https://github.com/AI20K-Build-Phase-Cohort-4/P-142.git
cd P-142

# 2. Setup environment
cp .env.example .env
# Edit .env with your API keys

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run development server
uvicorn src.main:app --reload
```

## Project Structure

```
├── src/
│   ├── agents/          # LangGraph agent definitions
│   │   ├── graph.py     # Main graph (nodes + edges)
│   │   ├── state.py     # State schema
│   │   ├── nodes/       # Individual nodes
│   │   └── tools/       # Agent tools
│   ├── api/             # FastAPI routes
│   ├── models/          # Pydantic schemas
│   ├── services/        # Business logic
│   ├── config.py        # Settings
│   └── main.py          # App entry point
├── tests/               # Test suite
├── docs/                # Documentation
├── eval/                # Evaluation results
├── presentation/        # Demo materials
├── Dockerfile           # Multi-stage build
├── docker-compose.yml   # Full stack
└── .github/workflows/   # CI/CD pipelines
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/api/v1/cases` | Tạo case từ yêu cầu khách hàng |
| POST | `/api/v1/cases/{id}/messages` | Gửi phản hồi cho Agent |
| GET | `/api/v1/cases/{id}` | Xem Service Brief và trạng thái case |
| PATCH | `/api/v1/cases/{id}` | Reviewer approve, edit, escalate hoặc close case |

## Deliverables Checklist

- [x] GitHub Repo Setup
- [x] README.md
- [x] PRD
- [x] Brief
- [ ] Architecture Diagram (`docs/architecture_diagram.md`)
- [x] AI Logs (auto-collected)
- [ ] Live URL / Deploy
- [ ] Video Demo
- [ ] Pitch Deck (`presentation/`)
- [ ] Weekly Journal (`JOURNAL.md`)
- [x] Worklog (`WORKLOG.md`)
- [ ] Evaluation Evidence (`eval/results/`)

## Team

| Member | Role | Student ID |
|--------|------|-----------|
| Thế Việt | Project Manager, BA, Frontend/UI UX | 2A202602594 |
| Khôi | AI Engineer, Data and Evaluation | 2A202602434 |
| Long | AI Engineer, RAG and Agent Workflow | 2A202602633 |
| Triển | Backend Engineer, API and Database | 2A202602837 |

## License

MIT
