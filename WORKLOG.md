# Worklog — Team VFO2O-18 (VinFast ServiceFlow AI)

> Ghi lại công việc theo ngày, gồm người thực hiện, kết quả, thời gian và blocker.

> **Lưu ý kiểm tra ngày 2026-09-27:** Trạng thái cập nhật trong các bảng dưới đây phản ánh bằng chứng có thể kiểm tra trong repo. `Có bản thảo` không đồng nghĩa với tính năng đã chạy. `Chưa xác minh` không có nghĩa là công việc chưa được thực hiện bên ngoài repo. Xem bảng đối chiếu từng mục ở cuối file.

---

## 2026-09-20 (Gate G1: Scope & Alignment)

| Member | Task | Status | Output | Time |
|---|---|---|---|---|
| Cả nhóm | Nghiên cứu đề VFO2O-18 và đối chiếu với các tính năng hiện có của VinFast | ⚠️ Có định vị; nghiên cứu chưa xác minh | Tài liệu nêu AI tiếp nhận, chuẩn hóa và routing; chưa có hồ sơ đối chiếu độc lập trong repo | 2 ngày |
| Cả nhóm | Chốt problem statement, MVP scope và out-of-scope cho Gate G1 | ✅ Có bản thảo | Brief và phạm vi MVP trong tài liệu sản phẩm; ADR chấp thuận sau đó vào 24/09 | 4h |
| Thế Việt | Thiết lập quản lý dự án: role, scope, backlog và tài liệu Gate G1 | ⚠️ Một phần | Có phân vai, WORKLOG và README boilerplate; README chính còn là template, chưa thấy backlog/checklist Gate G1 riêng | 3h |
| Khôi | Review intent taxonomy và đề xuất hướng đánh giá AI | ✅ Có bản thảo | 4 intent, priority matrix và mục tiêu đánh giá trong docs; chưa có kết quả benchmark | 4h |
| Long | Phác thảo Agent workflow, RAG và rule engine | ✅ Có bản thảo | Workflow và ranh giới nguồn RAG trong docs; chưa phải logic agent triển khai | 4h |
| Triển | Phác thảo database schema và ticket workflow | ✅ Có bản thảo | Data model và API contract trong docs; chưa phải Case lifecycle API | 4h |

**Tổng kết ngày:** Đã chốt đề tài VFO2O-18, định vị sản phẩm và scope MVP cho Gate G1. 

---

## 2026-09-23 (Gate G1: Mentor Duty & Sprint 1 Prep)

| Member | Task | Status | Output | Time |
|---|---|---|---|---|
| Cả nhóm | Tổng hợp tiến độ Gate G1, chuẩn bị nội dung Mentor Duty submit | ✅ Done | Mentor Duty log (Done/Doing/Blocked/Questions) | 2h |
| Thế Việt, Long | Thiết kế form khảo sát người dùng xe điện VinFast để kiểm chứng pain point | ✅ Done | Draft câu hỏi khảo sát cho chủ xe & tài xế GSM | 3h |
| Khôi | Xây dựng bộ test cases đánh giá Intent Accuracy & Critical Recall | 🔄 WIP | Benchmark dataset (40 mẫu test) | 4h |
| Long | Thiết kế chi tiết LangGraph state schema và guardrails | ✅ Done | `src/agents/state.py` & `src/agents/guardrails.py` + 19 unit tests | 4h |
| Triển | Khởi tạo cấu trúc Pydantic models và FastAPI routes cho Case lifecycle | 🔄 WIP | `src/models/schemas.py` & `src/api/routes.py` | 4h |

<!-- update info from feature/ai-khoi branch -->

### Đối chiếu lịch sử ngày 27/09 từ feature/ai-khoi

Các nhận xét sau phản ánh thời điểm kiểm tra, không thay thế tiến độ triển khai mới trên develop.

| Member | Task | Status | Output | Time |
|---|---|---|---|---|
| Cả nhóm | Tổng hợp tiến độ Gate G1, chuẩn bị nội dung Mentor Duty submit | 🔎 Chưa xác minh | WORKLOG ghi nhận đã chuẩn bị/nộp; repo chưa có nội dung log hoặc biên nhận nộp bài | 2h |
| Thế Việt, Long | Thiết kế form khảo sát người dùng xe điện VinFast để kiểm chứng pain point | 🔎 Chưa xác minh | Repo chưa có bản câu hỏi/form; tài liệu chỉ ghi nhận kết quả khảo sát thăm dò | 3h |
| Khôi | Xây dựng bộ test cases đánh giá Intent Accuracy & Critical Recall | 🔄 WIP | Dataset v1 có 12/40 ca mục tiêu; chưa có baseline | 4h |
| Long | Thiết kế chi tiết LangGraph state schema và guardrails | 🔄 WIP | State TypedDict/graph mẫu; emergency rules mới ở tài liệu | 4h |
| Triển | Khởi tạo cấu trúc Pydantic models và FastAPI routes cho Case lifecycle | 🔄 WIP | `src/models/schemas.py` và `src/api/routes.py` hiện chỉ xử lý chat mẫu | 4h |

**Tổng kết ngày (đã đối chiếu 27/09):** WORKLOG ban đầu ghi đã nộp Mentor Duty ngày 23/09/2026, nhưng repo chưa có bằng chứng để xác nhận việc nộp. Form khảo sát và WBS chi tiết cũng chưa có đầu ra kiểm tra được trong repo. Các module LangGraph và FastAPI vẫn đang WIP.

---

## 2026-09-24 (Gate G2: Rà soát Docs & Scope MVP theo Khảo sát Thăm dò)

| Member | Task | Status | Output | Time |
|---|---|---|---|---|
| Thế Việt | Cập nhật `problem-and-mvp-scope.md` và `user-flows.md` theo khảo sát thăm dò (n=4), bỏ các con số chưa có bằng chứng, chuẩn hóa mục tiêu evaluation | ✅ Có tài liệu | Scope và user flows đã cập nhật; dữ liệu khảo sát gốc không được đối chiếu trong repo | 3h |
| Long | Cập nhật `triage-and-hitl-rules.md` và `agent-workflow.md`: tổ hợp Critical rule ("rùa vàng" + cao tốc/nguy hiểm), khóa rule làm rõ $\le 2$ lượt | ✅ Có tài liệu | Hard rules và state flow đã viết; chưa triển khai/kiểm thử trong agent | 3h |
| Khôi | Kiểm chứng URL tài liệu công khai chính thức ([Hướng dẫn app VinFast](https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast)), tạo bộ dataset benchmark `eval/datasets/triage_cases_v1.jsonl` không PII | ⚠️ Một phần | Có đặc tả nguồn và 12 ca mô phỏng; không xác minh được lần kiểm tra URL ngày 24/09, metadata đã được rà lại ngày 27/09 | 3h |
| Triển | Chuẩn hóa `api-contract.md` và `data-model.md` loại bỏ hoàn toàn PII, thống nhất State Machine của Ticket | ⚠️ Cần đồng bộ | Có API contract và data model; screen spec vẫn chứa `name`/`phone`, chưa có ràng buộc PII trong code | 3h |
| Cả nhóm | Thống nhất kế hoạch triển khai: ưu tiên build Vertical Slice Flow 1 (`Charging/Battery`) trước 29/09/2026 | ✅ Có quyết định | ADR-001 và JOURNAL ghi rõ mốc/ưu tiên; Flow 1 chưa hoàn thành | 2h |

**Tổng kết ngày (đã đối chiếu 27/09):** Đã cập nhật các tài liệu Product, Architecture và Evaluation, tạo dataset mô phỏng 12 ca và ghi quyết định ưu tiên Flow 1. Một số đặc tả vẫn In Review/chưa thống nhất; không xem tài liệu đã viết là bằng chứng tính năng đã triển khai.

---

## Đối chiếu từng đầu việc trước 26/09/2026 (kiểm tra ngày 27/09/2026)

`Bằng chứng` dưới đây chỉ xác nhận nội dung đang có trong repo, không xác nhận thời gian làm việc, khảo sát gốc hoặc hoạt động trên hệ thống ngoài repo. Các liên kết tới bản tài liệu hiện tại có thể đã được chỉnh sửa sau ngày ghi trong WORKLOG.

| ID | Ngày / đầu việc | Bằng chứng trong repo | Phần chưa xác minh / chưa đạt | Trạng thái đề xuất |
| --- | --- | --- | --- | --- |
| 01 | 20/09 — Nghiên cứu đề và đối chiếu ứng dụng VinFast | [Định vị và phạm vi](docs/product/problem-and-mvp-scope.md), [ADR-001](docs/decisions/ADR-001-mvp-scope.md) | Không có hồ sơ nghiên cứu/đối chiếu độc lập hoặc xác nhận khoảng trống đa kênh. | ⚠️ Có định vị; nghiên cứu chưa xác minh |
| 02 | 20/09 — Problem statement, MVP scope, out-of-scope | [Problem & MVP scope](docs/product/problem-and-mvp-scope.md), [ADR-001](docs/decisions/ADR-001-mvp-scope.md) | Bản scope còn In Review; khảo sát n=4 chưa đối chiếu dữ liệu gốc. | ✅ Có bản thảo; cần review |
| 03 | 20/09 — Role, scope, backlog, README, Gate G1 checklist | [WORKLOG](WORKLOG.md), [README boilerplate](README_boilerplate.md), [README chính](README.md) | README chính vẫn là template; không thấy backlog/checklist Gate G1 riêng trong repo. | ⚠️ Một phần |
| 04 | 20/09 — Intent taxonomy và hướng đánh giá | [Triage & HITL](docs/architecture/triage-and-hitl-rules.md), [mục tiêu đánh giá](eval/results/report.md) | Có đề xuất 4 intent và ma trận ưu tiên; chưa có kết quả đo. | ✅ Có bản thảo |
| 05 | 20/09 — Agent workflow, RAG, rule engine | [Agent workflow](docs/architecture/agent-workflow.md), [nguồn RAG](docs/architecture/rag-and-data-sources.md) | Phác thảo trong docs; [node hiện tại](src/agents/nodes/example_node.py) còn logic mẫu. | ✅ Có bản thảo; code chưa xong |
| 06 | 20/09 — Database schema và ticket workflow | [Data model](docs/architecture/data-model.md), [API contract](docs/architecture/api-contract.md) | Chưa có bảng dữ liệu hay API ticket trong [routes hiện tại](src/api/routes.py). | ✅ Có bản thảo; code chưa xong |
| 07 | 23/09 — Mentor Duty log và nộp bài | Chỉ có ghi nhận trong [WORKLOG](WORKLOG.md) | Không có nội dung log/biên nhận trong repo; không thể xác nhận đã nộp. | 🔎 Chưa xác minh |
| 08 | 23/09 — Draft form khảo sát | [Scope](docs/product/problem-and-mvp-scope.md) ghi nhận khảo sát thăm dò n=4 | Không có bản câu hỏi/form trong repo; không kiểm tra hoặc yêu cầu đưa dữ liệu người tham gia lên repo. | 🔎 Chưa xác minh |
| 09 | 23/09 — Dataset 40 ca | [Dataset v1](eval/datasets/triage_cases_v1.jsonl) có 12 ca | Chưa đủ 40 ca và chưa có script/chỉ số baseline thực chạy. | 🔄 WIP |
| 10 | 23/09 — LangGraph state và guardrails | [Agent state](src/agents/state.py), [graph](src/agents/graph.py), [đặc tả rules](docs/architecture/triage-and-hitl-rules.md) | State và graph vẫn là khung mẫu; chưa có emergency fast-track bằng code. | 🔄 WIP |
| 11 | 23/09 — Pydantic models và Case lifecycle routes | [Schemas](src/models/schemas.py), [routes](src/api/routes.py) | Mới có schema chat và `/chat`, `/status`; chưa có Case lifecycle API. | 🔄 WIP |
| 12 | 24/09 — Cập nhật scope và user flows theo khảo sát | [Scope](docs/product/problem-and-mvp-scope.md), [user flows](docs/product/user-flows.md) | Xác nhận tài liệu có nội dung n=4; không xác minh được dữ liệu khảo sát gốc và chưa có phê duyệt cuối. | ✅ Có tài liệu; giới hạn bằng chứng khảo sát |
| 13 | 24/09 — Quy tắc Critical và giới hạn hai lượt hỏi | [Triage & HITL](docs/architecture/triage-and-hitl-rules.md), [agent workflow](docs/architecture/agent-workflow.md) | Đã tài liệu hóa; chưa có code/test chứng minh quy tắc chạy. | ✅ Có tài liệu; code chưa xong |
| 14 | 24/09 — URL VinFast và dataset không PII | [Đặc tả nguồn](docs/architecture/rag-and-data-sources.md), [dataset](eval/datasets/triage_cases_v1.jsonl), [báo cáo rà metadata](docs/change-report-2026-09-27-rag-metadata.md) | Có URL và dữ liệu mô phỏng; lần kiểm tra URL ngày 24/09 không xác minh được. Không suy ra mọi đầu vào thực tế đều không có PII. | ⚠️ Có đầu ra; giới hạn xác minh |
| 15 | 24/09 — API/data model không PII và trạng thái ticket | [API contract](docs/architecture/api-contract.md), [data model](docs/architecture/data-model.md) | [Screen spec](docs/design/screen-spec.md) vẫn có `name`/`phone`; chưa có enforcement trong code. | ⚠️ Cần đồng bộ |
| 16 | 24/09 — Kế hoạch ưu tiên Flow 1 trước 29/09 | [ADR-001](docs/decisions/ADR-001-mvp-scope.md), [JOURNAL](JOURNAL.md) | Xác nhận quyết định ưu tiên; không đồng nghĩa Flow 1 đã chạy. | ✅ Có quyết định; triển khai WIP |

**Việc cần bổ sung để đóng các mục còn mở:** Việt hoàn thiện README/backlog và đồng bộ screen spec với quy tắc không PII; Long và Triển triển khai, kiểm thử agent/Case lifecycle; Khôi mở rộng dataset và tạo script đo kết quả. Với Mentor Duty và form khảo sát, chỉ cập nhật trạng thái khi nhóm cung cấp bằng chứng phù hợp. Không đưa bản khảo sát hay biên nhận có dữ liệu cá nhân vào repo khi chưa được phép và kiểm tra nội dung.

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

## 2026-10-03 (Gate G2: Chuẩn hóa UI/UX Chat, Bản đồ Vị trí ADR-005 & Đa dạng hóa Intent Landing Page)

| Member | Task | Status | Output | Time |
|---|---|---|---|---|
| Thế Việt | Tinh gọn giao diện Chat (`SCR-01`, `SCR-02`): Áp dụng luật "Một tin nhắn chỉ một box", bỏ box lồng box, phục hồi 70% không gian hội thoại | ✅ Done | `ChatMessageItem.tsx`, `CustomerChatContainer.tsx`, `ChatFeed.tsx` | 4h |
| Thế Việt | Tích hợp Bản đồ Dịch vụ & Xin quyền Vị trí theo ADR-005: Docking thanh consent trên ô nhập, tính khoảng cách Haversine chính xác theo GPS, hạ độ cao map 45% hiển thị trọn vẹn nút Chỉ đường/Gọi, làm mờ ghim ngoài nhóm lọc | ✅ Done | `ServiceMapPanel.tsx`, `LocationConsentCard.tsx`, `distance.ts`, `constants.ts` | 5h |
| Thế Việt | Tái cấu trúc Hero Section Landing Page (`SCR-05.1`): Chuyển tông giọng trung tính "Bạn cần hỗ trợ gì về xe điện?", xoay vòng placeholder 4 kịch bản, chip đa dạng 4 nhóm ý định, phân tách trạng thái Guest vs Customer | ✅ Done | `LandingPage.tsx` | 3.5h |
| Long | Tối ưu hóa phân loại Intent & Hard Safety Guardrails: Phân định ca khẩn cấp cao tốc (kích hoạt sticky red banner) và ca thường (lỗi sạc CC01, bảo dưỡng không chiếm dụng diện tích banner) | ✅ Done | `src/agents/chatbot_agent.py`, `EmergencyAlertBanner.tsx`, `useChat.ts` | 3h |
| Triển | Chuẩn hóa sinh mã Case ID động (`CASE-YYYYMMDD-XXX`) trên cả Backend và Frontend Mock fallback, bổ sung chip `"Xem bản đồ trạm sạc ›"` vào kịch bản làm rõ | ✅ Done | `src/api/customer.py`, `src/models/schemas.py`, `useChat.ts` | 2.5h |
| Cả nhóm | Kiểm thử Production Build Next.js & Kiểm tra luồng liên thông giữa Chat, Bản đồ gợi ý và Landing Page | ✅ Done | `npm run build` thành công 100% (9/9 routes, 0 error, 0 lint warning) | 2h |

**Tổng kết ngày:** Đã hoàn thiện toàn diện bộ giao diện người dùng theo chuẩn `screen-spec.md` (Mục 1, 2, 5.1, 5.4) và `ADR-005`:
1. **Chat:** Triệt tiêu anti-pattern "box lồng box", cố định banner an toàn khẩn cấp 46px ngay dưới Navbar, thanh consent vị trí mỏng nhẹ không làm nghẽn luồng chat.
2. **Bản đồ:** Tự động đồng bộ vị trí GPS thực tế, tính khoảng cách Haversine chuẩn xác, chiều cao bản đồ 45% giúp thẻ điểm hỗ trợ đầu tiên không bị che khuất nút hành động, ghim ngoài bộ lọc tự động làm mờ trực quan.
3. **Landing Hero:** Mở rộng từ định kiến "chỉ báo lỗi" sang tiếp nhận toàn diện 3 nhóm khách (sự cố, hỏi cẩm nang/đặt lịch, khách vãng lai), dropdown dòng xe linh hoạt cho Guest và tự động điền cho Customer đã đăng nhập.

---

## 2026-10-11 (Bảo mật Phiên Chat, Khắc phục Session Takeover & Vòng đời Đa phiên ADR-006)

| Member | Task | Status | Output | Time |
|---|---|---|---|---|
| Triển, Thế Việt | Khắc phục lỗ hổng chiếm đoạt phiên (Session Takeover): loại bỏ `ChatSession.id == raw_claim`, chỉ cho phép claim khi `owner == f"guest:{raw_claim}"` | ✅ Done | `src/api/auth.py`, `src/api/customer.py` | 3.5h |
| Triển | Ràng buộc gộp Case & Message an toàn: chỉ nhận Case `user_id IS NULL`, Message theo `claimed_session_ids`, thực thi nguyên tử trong login/register | ✅ Done | `src/api/auth.py`, `src/models/schemas.py` | 3h |
| Triển | Chuẩn hóa IDOR Protection 404 (chống dò session) và cascade deletion xóa sạch Message & ChatRequestRecord khi xóa session | ✅ Done | `src/api/customer.py` | 2.5h |
| Triển | Khắc phục mất cờ `title_edited` trong JSON column bằng `flag_modified`; sửa lỗi đóng băng sớm Title cache trên câu chào | ✅ Done | `src/api/customer.py` | 2h |
| Thế Việt | Nâng cấp bảo mật client: sinh guest id bằng UUID v4 (`crypto.randomUUID`), xóa localStorage sau khi xác thực 200 OK, dọn dẹp state và xoay guest id khi logout | ✅ Done | `useChat.ts`, `AuthContext.tsx`, `ChatHistorySidebar.tsx` | 3.5h |
| Cả nhóm | Xây dựng bộ test nghiệm thu tự động bảo mật & kiểm thử hồi quy toàn diện (takeover prevention, guest isolation, double-claim, title lifecycle, clean deletion) | ✅ Done | `tests/test_api/test_session_security_and_lifecycle.py` (5/5 PASS), `npm run build` PASS | 3h |

**Tổng kết ngày:**
1. **Khắc phục lỗ hổng nghiêm trọng:** Triệt tiêu hoàn toàn khả năng chiếm đoạt session (`Session Takeover`) bằng cách loại bỏ query theo session id tự do.
2. **Kiến trúc bền vững:** Ghi nhận `ADR-006` và cập nhật `api-contract.md` v1.2.0; bảo đảm đồng bộ dirty state cho JSON column và cascade deletion chống dữ liệu mồ côi.
3. **UX & Bảo mật đồng hành:** Tiêu đề động thông minh không bị đóng băng khi mới chào hỏi, giữ nguyên tiêu đề đổi thủ công; khách đăng xuất trên máy dùng chung được bảo vệ tuyệt đối.

---

<!-- Format: copy block trên cho mỗi ngày làm việc -->
