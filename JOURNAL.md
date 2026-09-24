# Weekly Journal — Team VFO2O-18 (VinFast ServiceFlow AI)

> Ghi lại mỗi tuần: học được gì, khó khăn gì, quyết định gì, kế hoạch tiếp.

---

## Week 1: 2026-09-17 - 2026-09-23 (Gate G1: Discovery & Architecture)

### Mục tiêu tuần này
- [x] Chốt định vị bài toán VFO2O-18 và đối chiếu với app VinFast hiện hữu.
- [x] Chốt phạm vi MVP web-based và out-of-scope.
- [x] Hoàn thiện tài liệu nền tảng: Brief, PRD, AI Components, Guardrails, Metrics.
- [x] Thiết lập repo chuẩn: README, AI Usage Logging, Worklog, Journal.
- [x] Thiết kế form khảo sát người dùng xe điện để kiểm chứng pain point.

### Đã hoàn thành
- **Định vị sản phẩm:** Xác định VinFast ServiceFlow AI là AI Agent tiếp nhận và điều phối yêu cầu đa kênh (Web Chat, Zalo, Email, Hotline transcript), giải quyết triệt để vấn đề hội thoại tự do thiếu dữ kiện bằng Contextual Clarification và tạo Service Brief.
- **Rà soát tính năng:** Phân tích kỹ các tính năng đã có trên app VinFast (booking, cứu hộ, cảnh báo xe) để không làm lại, chỉ tập trung vào lớp intake & routing trước khi bàn giao.
- **Tài liệu dự án & AI Architecture:** Draft hoàn chỉnh PRD, LangGraph workflow (Intake -> Triage -> Clarify -> RAG -> Brief -> HITL), Rule engine cho priority và ma trận an toàn (Safety triggers).
- **Hệ thống đánh giá:** Xây dựng khung metrics (Intent Accuracy, Critical Case Recall, Brief Completeness Score, RAGAS Faithfulness).
- **Repo & Tooling:** Kích hoạt hook ghi log AI, hoàn thiện cấu trúc thư mục chuẩn theo yêu cầu của BTC.

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|---|---|---|
| Nguy cơ trùng lặp tính năng với app VinFast chính hãng | Đối chiếu sâu app VinFast, xác định app chỉ phục vụ khách đã login/có xe, còn luồng đa kênh (Zalo, Web, Hotline) chưa có lớp AI chuẩn hóa dữ kiện trước khi routing | Định vị sản phẩm rõ ràng, không bị chồng chéo scope |
| Chưa có quyền truy cập API/CRM nội bộ của VinFast | Thiết kế Web Chat là kênh tương tác thật; xây dựng bộ Mock Channel Simulator cho Zalo, Email và Hotline transcript | Giải quyết được bài toán demo omnichannel trọn vẹn mà không phụ thuộc API bên thứ 3 |
| Tránh chia WBS task theo giả định chủ quan | Tạm hoãn phân rã WBS chi tiết cho đến khi có kết quả khảo sát người dùng thực tế | Ưu tiên đúng pain point thực tế của khách hàng và cố vấn dịch vụ |

### Bài học
- Cần làm rõ ranh giới MVP (In-scope vs Out-of-scope) ngay từ đầu để không bị phân tán nguồn lực vào các tính năng như chẩn đoán CAN-bus/OBD-II hay booking xưởng thật.
- Thiết kế Agent theo kiến trúc LangGraph giúp kiểm soát chặt chẽ trạng thái hội thoại và dễ dàng can thiệp bằng Human-in-the-loop (HITL) khi có rủi ro an toàn.

---

## Week 2: 2026-09-24 - 2026-09-30 (Gate G2: Core Engine & Vertical Slice Flow 1)

### Mục tiêu tuần này
- [x] Phân tích tín hiệu khảo sát thăm dò ban đầu (n=4) và điều chỉnh lại toàn bộ tài liệu đặc tả, scope MVP.
- [x] Khóa quy tắc bảo mật không PII và quy tắc Clarification tối đa 2 lượt.
- [x] Tạo bộ benchmark test cases `eval/datasets/triage_cases_v1.jsonl` mô phỏng không chứa PII.
- [ ] Build hoàn chỉnh Vertical Slice Flow 1: Sự cố sạc (`Charging/Battery`) E2E từ Customer Chat $\rightarrow$ Clarify $\rightarrow$ Case Brief $\rightarrow$ Staff Review $\rightarrow$ Customer Status.
- [ ] Mở rộng thu thập khảo sát chủ xe VinFast để củng cố dữ liệu nghiên cứu.

### Đã hoàn thành
- **Điều chỉnh Scope từ Khảo sát Thăm dò:**
  - Định vị 4 phản hồi ban đầu là "khảo sát thăm dò ban đầu" (exploratory survey), dùng làm giả thuyết định hướng MVP, không khẳng định đại diện cho toàn bộ khách hàng.
  - Bảo mật dữ liệu: Tuyệt đối không commit raw file khảo sát chứa PII lên repo công khai.
  - Chốt 2 Value Proposition chính trên Customer Chat: (1) Giải thích cảnh báo/lỗi dễ hiểu, (2) Tóm tắt Case Brief để khách không phải mô tả lại.
  - Khẳng định HITL là yêu cầu cốt lõi.
- **Chuẩn hóa Quy tắc & Schema:**
  - Chuẩn hóa quy tắc Clarification: Tối đa 2 lượt Agent chủ động hỏi làm rõ, mỗi lượt 1 tin nhắn gom dữ kiện + Quick Replies. Sau 2 lượt, nếu vẫn thiếu thông tin thì tạo case `Needs Information`.
  - Chuẩn hóa Hard Rule Critical: Bắt buộc tổ hợp tín hiệu ("rùa vàng" + "trên cao tốc/mất kiểm soát/giảm công suất nguy hiểm") hoặc cháy/khói/mất phanh. "Rùa vàng" điều kiện bình thường xếp loại High + Staff Review.
  - Loại bỏ PII khỏi schema API & Database: Dùng `session_id`, `mock_customer_id`, `vehicle_model`, `vehicle_code_mock`. Tên/SĐT chỉ dùng trong seed demo.
  - Loại bỏ hướng dẫn kỹ thuật chưa kiểm chứng trong bot response; bổ sung liên kết đến Ứng dụng VinFast chính thức cho luồng dịch vụ.
  - Cập nhật URL tài liệu công khai đã kiểm chứng thực tế ([Hướng dẫn sử dụng ứng dụng VinFast](https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast)) kèm ngày thu thập 2026-09-24.
- **Tạo Dataset Đánh giá:** Khởi tạo `eval/datasets/triage_cases_v1.jsonl` và cập nhật tiêu chí đo lường trong `eval/results/report.md`.

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|---|---|---|
| Dữ liệu khảo sát ban đầu còn ít (n=4) và chứa thông tin cá nhân (Email, Họ tên) | Định danh là khảo sát thăm dò ban đầu để lấy tín hiệu giả thuyết; loại bỏ toàn bộ PII và chỉ lưu trữ các case mô phỏng trong repo | Vừa có cơ sở định hướng thiết kế MVP vừa đảm bảo tuân thủ nghiêm ngặt bảo mật PII |
| Nguy cơ Agent đưa ra hướng dẫn kỹ thuật không an toàn / chưa kiểm chứng (như tự ý khuyên rút súng 30s, reset remote) | Quy định chặt chẽ: Bot chỉ phản hồi an toàn, ghi nhận và chuyển Staff Review để nhân viên có thẩm quyền chẩn đoán | Ngăn ngừa rủi ro trách nhiệm sản phẩm và ảo giác kỹ thuật |
| Mâu thuẫn giữa giới hạn 1-2 câu hỏi làm rõ và việc thu thập 3 trường bắt buộc của sự cố sạc | Cho phép 1 câu hỏi gom nhiều dữ kiện kèm lựa chọn trả lời nhanh (Quick Replies); giới hạn cứng tối đa 2 lượt hỏi | Đảm bảo trải nghiệm chat mượt mà, không tra khảo khách hàng |

### Bài học
- Tín hiệu khảo sát thăm dò rất giá trị để xác thực thứ tự ưu tiên tính năng (tóm tắt brief và giải thích lỗi được quan tâm hàng đầu).
- Cần tách biệt rõ ràng giữa "Mục tiêu đánh giá" (Evaluation Targets) và "Kết quả đã đạt được" trong tài liệu kỹ thuật để giữ tính trung thực khoa học.

### Kế hoạch tiếp theo
- [ ] **Việt:** Cập nhật tài liệu Problem Scope & PRD theo khảo sát thăm dò; chốt Figma link và 4 màn giao diện chính.
- [ ] **Long:** Chốt rule matrix, ngưỡng HITL và logic LangGraph clarification bounds.
- [ ] **Khôi:** Mở rộng bộ eval benchmark lên 40 test cases mô phỏng; hoàn thiện script kiểm thử tự động.
- [ ] **Triển:** Khóa status enum và schema không PII; triển khai Case/Ticket lifecycle API trên FastAPI.
- [ ] **Cả nhóm:** Tập trung build hoàn thiện Flow 1 (Vertical Slice Charging) trước ngày 29/09/2026.
