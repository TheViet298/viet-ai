# Worklog — Team VFO2O-18 (VinFast ServiceFlow AI)

> Ghi lại công việc theo ngày, gồm người thực hiện, kết quả, thời gian và blocker.

---

## 2026-09-20 (Gate G1: Scope & Alignment)

| Member | Task | Status | Output | Time |
|---|---|---|---|---|
| Cả nhóm | Nghiên cứu đề VFO2O-18 và đối chiếu với các tính năng hiện có của VinFast | ✅ Done | Chốt định vị: AI Agent tiếp nhận, chuẩn hóa và routing yêu cầu đa kênh; không làm lại app VinFast | 2 ngày |
| Cả nhóm | Chốt problem statement, MVP scope và out-of-scope cho Gate G1 | ✅ Done | Brief và PRD draft | 4h |
| Thế Việt | Thiết lập quản lý dự án: role, scope, backlog và tài liệu Gate G1 | ✅ Done | README/Worklog/Gate G1 checklist | 3h |
| Khôi | Review intent taxonomy và đề xuất hướng đánh giá AI | ✅ Done | Intent taxonomy (4 nhóm) + Priority Matrix draft | 4h |
| Long | Phác thảo Agent workflow, RAG và rule engine | ✅ Done | State graph flow + RAG knowledge boundary | 4h |
| Triển | Phác thảo database schema và ticket workflow | ✅ Done | Ticket state lifecycle + API endpoints draft | 4h |

**Tổng kết ngày:** Đã chốt đề tài VFO2O-18, định vị sản phẩm và scope MVP cho Gate G1. 

---

## 2026-09-23 (Gate G1: Mentor Duty Submission & Sprint 1 Prep)

| Member | Task | Status | Output | Time |
|---|---|---|---|---|
| Cả nhóm | Tổng hợp tiến độ Gate G1, chuẩn bị nội dung Mentor Duty submit | ✅ Done | Mentor Duty log (Done/Doing/Blocked/Questions) | 2h |
| Thế Việt, Long | Thiết kế form khảo sát người dùng xe điện VinFast để kiểm chứng pain point | ✅ Done | Draft câu hỏi khảo sát cho chủ xe & tài xế GSM | 3h |
| Khôi | Xây dựng bộ test cases đánh giá Intent Accuracy & Critical Recall | 🔄 WIP | Benchmark dataset (40 mẫu test) | 4h |
| Long | Thiết kế chi tiết LangGraph state schema và guardrails | ✅ Done | `src/agents/state.py` & `src/agents/guardrails.py` + 19 unit tests | 4h |
| Triển | Khởi tạo cấu trúc Pydantic models và FastAPI routes cho Case lifecycle | 🔄 WIP | `src/models/schemas.py` & `src/api/routes.py` | 4h |

**Tổng kết ngày:** Đã nộp Mentor Duty ngày 23/09/2026. Nhóm đang triển khai form khảo sát và phân chia task WBS để bắt đầu code các module nền tảng của LangGraph & FastAPI backend.

---

## 2026-09-24 (Gate G2: Rà soát Docs & Scope MVP theo Khảo sát Thăm dò)

| Member | Task | Status | Output | Time |
|---|---|---|---|---|
| Thế Việt | Cập nhật `problem-and-mvp-scope.md` và `user-flows.md` theo khảo sát thăm dò (n=4), bỏ các con số chưa có bằng chứng, chuẩn hóa mục tiêu evaluation | ✅ Done | Tài liệu Scope & User Flows được cập nhật | 3h |
| Long | Cập nhật `triage-and-hitl-rules.md` và `agent-workflow.md`: tổ hợp Critical rule ("rùa vàng" + cao tốc/nguy hiểm), khóa rule làm rõ $\le 2$ lượt | ✅ Done | Hard rules & State flow chuẩn hóa | 3h |
| Khôi | Kiểm chứng URL tài liệu công khai chính thức ([Hướng dẫn app VinFast](https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast)), tạo bộ dataset benchmark `eval/datasets/triage_cases_v1.jsonl` không PII | ✅ Done | `rag-and-data-sources.md` & `eval/datasets/triage_cases_v1.jsonl` | 3h |
| Triển | Chuẩn hóa `api-contract.md` và `data-model.md` loại bỏ hoàn toàn PII, thống nhất State Machine của Ticket | ✅ Done | API & Data Model chuẩn hóa | 3h |
| Cả nhóm | Thống nhất kế hoạch triển khai: ưu tiên build Vertical Slice Flow 1 (`Charging/Battery`) trước 29/09/2026 | ✅ Done | Kế hoạch tuần 2 & Phân công nhiệm vụ chi tiết | 2h |

**Tổng kết ngày:** Đã đồng bộ toàn diện hệ thống tài liệu docs (Product, Architecture, Evaluation) theo tín hiệu khảo sát thăm dò ban đầu. Đã tạo dataset benchmark mô phỏng và chốt lộ trình ưu tiên Flow 1.

---

## 2026-09-30 (Gate G2: Core Engine, Vertical Slice & Full-Stack AI Integration)

| Member | Task | Status | Output | Time |
|---|---|---|---|---|
| Thế Việt | Tích hợp toàn diện giao diện Frontend (Chat, Case Tracking, Console, Auth) với Live REST APIs | ✅ Done | `chatApi.ts`, `track-case/page.tsx`, `CustomerChatContainer.tsx`, `AuthContext.tsx` | 5h |
| Thế Việt | Nâng cấp trải nghiệm Chat: Nút làm mới phiên hội thoại (Reset Chat) và hiệu ứng AI Thinking Bubble sinh động | ✅ Done | `ChatFeed.tsx`, `CustomerChatContainer.tsx`, `useChat.ts` | 3h |
| Long | Tích hợp Core AI Chatbot Agent từ nhánh develop, chuẩn hóa Guardrails (Hard Safety, No-PII, HITL flag) | ✅ Done | `src/agents/chatbot_agent.py`, `src/agents/guardrails.py` | 4h |
| Khôi | Mở rộng Fallback Knowledge Base lên 7 nguồn (bổ sung danh mục xe VF 3 - VF 9 và catalog thông số kỹ thuật) | ✅ Done | `src/services/rag_service.py` (SRC-001 đến SRC-007) | 3h |
| Triển | Chuẩn hóa Triage Router 5 Intents (`sales_general_info`, `charging_battery`, `service_incident`, `complaint_feedback`, `safety_adversarial_oos`); xử lý thông minh câu hỏi tư vấn mua xe | ✅ Done | `src/api/customer.py` | 4h |
| Cả nhóm | Kiểm thử End-to-End Vertical Slice: Khẩn cấp (Safety) $\rightarrow$ Tra cứu (RAG FAQ) $\rightarrow$ Sự cố sạc ($\text{Landmark 81}$) $\rightarrow$ Bàn điều phối (Console HITL) | ✅ Done | Hệ thống chạy thông suốt trên `localhost:3000` & `localhost:8000` | 3h |

**Tổng kết ngày:** Đã merge và kết nối hoàn chỉnh giữa Frontend UI, Backend FastAPI, SQLite Database và Core AI Agent. Đã tinh chỉnh router theo đúng chuẩn bộ dataset `triage_test_v1.jsonl`, loại bỏ hiện tượng hỏi mặc định và cho phép phân luồng thông minh từ chào hỏi, tư vấn bán hàng đến tiếp nhận sự cố kỹ thuật.

---

<!-- Format: copy block trên cho mỗi ngày làm việc -->

<!-- Format: copy block trên cho mỗi ngày làm việc -->
