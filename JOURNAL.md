# Weekly Journal — Team VFO2O-18 (VinFast ServiceFlow AI)

> Ghi lại mỗi tuần: học được gì, khó khăn gì, quyết định gì, kế hoạch tiếp.

---

## Week 1: 2026-09-17 - 2026-09-23 (Gate G1: Discovery & Architecture)

### Mục tiêu tuần này
- [x] Chốt định vị bài toán VFO2O-18 và đối chiếu với app VinFast hiện hữu.
- [x] Chốt phạm vi MVP web-based và out-of-scope.
- [x] Hoàn thiện tài liệu nền tảng: Brief, PRD, AI Components, Guardrails, Metrics.
- [x] Thiết lập repo chuẩn: README, AI Usage Logging, Worklog, Journal.
- [ ] Thiết kế form khảo sát người dùng xe điện để kiểm chứng pain point.

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

### Kế hoạch tuần sau (Week 2)
- [ ] Thu thập và phân tích kết quả khảo sát người dùng xe điện (tối thiểu 30 mẫu + 3 phỏng vấn sâu).
- [ ] Hoàn thiện WBS chi tiết và phân công milestone cụ thể cho từng thành viên.
- [ ] Xây dựng Knowledge Base xe điện (VF3 - VF9) và cài đặt Vector Store (ChromaDB).
- [ ] Cài đặt core LangGraph pipeline (`triage`, `clarify`, `rag`, `brief`).
- [ ] Xây dựng khung giao diện Web Chat và Service Agent Console.

---

## Week 2: [Ngày bắt đầu] - [Ngày kết thúc]

### Mục tiêu tuần này
- [ ] [Mục tiêu 1]

### Đã hoàn thành
-

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|---|---|---|
| | | |

### Bài học
-

### Kế hoạch tuần sau
-

---

<!-- Tiếp tục copy block trên cho Week 3, 4, 5, 6 -->
