# Weekly Journal — Team VFO2O-18 (VinFast ServiceFlow AI)

> Ghi lại mỗi tuần: học được gì, khó khăn gì, quyết định gì, kế hoạch tiếp.

> **Rà soát bằng chứng ngày 2026-09-27:** Các mục hoàn thành bên dưới chủ yếu là đầu ra tài liệu. Bảng đối chiếu đủ 16 đầu việc trước 26/09 nằm trong [WORKLOG](WORKLOG.md). Repo chưa xác minh được bản form khảo sát, dữ liệu khảo sát gốc hoặc biên nhận Mentor Duty; không suy luận các việc đó đã/không được thực hiện bên ngoài repo.

---

## Week 1: 2026-09-17 - 2026-09-23 (Gate G1: Discovery & Architecture)

### Mục tiêu tuần này
- [x] Viết bản định vị bài toán VFO2O-18; hồ sơ đối chiếu độc lập với app VinFast chưa có trong repo.
- [x] Chốt phạm vi MVP web-based và out-of-scope.
- [x] Tạo bản thảo tài liệu nền tảng: Brief/Scope, AI Components, Guardrails, Metrics; nhiều tài liệu vẫn In Review.
- [x] Có cấu hình AI logging, WORKLOG và JOURNAL trong repo; việc gửi log từ mọi máy chưa được xác minh.
- [ ] Hoàn thiện README dự án, backlog và checklist Gate G1 có thể đối chiếu.
- [ ] Xác minh bản câu hỏi/form khảo sát; repo hiện không chứa bản form.

### Đã có đầu ra tài liệu
- **Định vị sản phẩm:** Tài liệu đề xuất VinFast ServiceFlow AI tiếp nhận và điều phối yêu cầu, dùng Contextual Clarification và Case Brief để giảm việc thiếu dữ kiện. Web Chat là kênh MVP; các kênh khác mới ở mức đề xuất mô phỏng.
- **Rà soát tính năng:** Tài liệu ghi nhận hướng tập trung vào intake và routing; chưa có hồ sơ nghiên cứu độc lập trong repo để xác nhận toàn bộ phần đối chiếu.
- **Tài liệu dự án & AI Architecture:** Có bản thảo Scope, LangGraph workflow (Intake -> Triage -> Clarify -> RAG -> Brief -> HITL), rule ưu tiên và an toàn; đây chưa phải tính năng hoạt động.
- **Hệ thống đánh giá:** Có định nghĩa mục tiêu chỉ số; [báo cáo đánh giá](eval/results/report.md) chưa có baseline thực chạy.
- **Repo & Tooling:** Có cấu hình hook AI, WORKLOG và JOURNAL; README chính còn là template. Chưa xác minh hook chạy và gửi log trên máy từng thành viên.

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|---|---|---|
| Nguy cơ trùng lặp tính năng với app VinFast chính hãng | Tài liệu đề xuất tập trung vào intake và routing thay vì tự xây booking/cứu hộ | Định vị MVP đã được ghi lại; khoảng trống đa kênh chưa có bằng chứng nghiên cứu độc lập trong repo |
| Chưa có quyền truy cập API/CRM nội bộ của VinFast | Thiết kế Web Chat là kênh tương tác thật và đề xuất Mock Channel Simulator | Simulator chưa có trong code; đây là phương án demo dự kiến |
| Tránh chia WBS task theo giả định chủ quan | Tạm hoãn phân rã WBS chi tiết cho đến khi có thêm tín hiệu khảo sát | Chưa thấy backlog/WBS chi tiết trong repo |

### Bài học
- Cần làm rõ ranh giới MVP (In-scope vs Out-of-scope) ngay từ đầu để không bị phân tán nguồn lực vào các tính năng như chẩn đoán CAN-bus/OBD-II hay booking xưởng thật.
- Thiết kế Agent theo kiến trúc LangGraph giúp kiểm soát chặt chẽ trạng thái hội thoại và dễ dàng can thiệp bằng Human-in-the-loop (HITL) khi có rủi ro an toàn.

---

## Week 2: 2026-09-24 - 2026-09-30 (Gate G2: Core Engine & Vertical Slice Flow 1)

### Mục tiêu tuần này
- [x] Cập nhật scope và user flows theo tín hiệu khảo sát n=4 do nhóm ghi nhận; dữ liệu gốc chưa được xác minh trong repo.
- [x] Viết quy tắc không PII và Clarification tối đa 2 lượt trong tài liệu.
- [ ] Đồng bộ screen spec với quy tắc không PII và triển khai/kiểm thử giới hạn hai lượt trong code.
- [x] Tạo dataset mô phỏng `eval/datasets/triage_cases_v1.jsonl` gồm 12 ca; chưa đủ 40 ca hoặc có baseline.
- [ ] Build hoàn chỉnh Vertical Slice Flow 1: Sự cố sạc (`Charging/Battery`) E2E từ Customer Chat $\rightarrow$ Clarify $\rightarrow$ Case Brief $\rightarrow$ Staff Review $\rightarrow$ Customer Status.
- [ ] Mở rộng thu thập khảo sát chủ xe VinFast để củng cố dữ liệu nghiên cứu.

### Đã ghi nhận trong tài liệu (chưa đồng nghĩa đã triển khai)
- **Điều chỉnh Scope từ Khảo sát Thăm dò:**
  - Tài liệu ghi nhận 4 phản hồi ban đầu là "khảo sát thăm dò ban đầu" (exploratory survey), dùng làm giả thuyết định hướng MVP, không khẳng định đại diện cho toàn bộ khách hàng. Dữ liệu gốc không được đối chiếu trong repo.
  - Quy tắc bảo mật: Không commit bản khảo sát gốc có thể chứa PII lên repo công khai; repo hiện không có dữ liệu gốc để kiểm tra.
  - Chốt 2 Value Proposition chính trên Customer Chat: (1) Giải thích cảnh báo/lỗi dễ hiểu, (2) Tóm tắt Case Brief để khách không phải mô tả lại.
  - Khẳng định HITL là yêu cầu cốt lõi.
- **Chuẩn hóa Quy tắc & Schema:**
  - Chuẩn hóa quy tắc Clarification: Tối đa 2 lượt Agent chủ động hỏi làm rõ, mỗi lượt 1 tin nhắn gom dữ kiện + Quick Replies. Sau 2 lượt, nếu vẫn thiếu thông tin thì tạo case `Needs Information`.
  - Chuẩn hóa Hard Rule Critical: Bắt buộc tổ hợp tín hiệu ("rùa vàng" + "trên cao tốc/mất kiểm soát/giảm công suất nguy hiểm") hoặc cháy/khói/mất phanh. "Rùa vàng" điều kiện bình thường xếp loại High + Staff Review.
  - API contract và data model dùng `session_id`, `mock_customer_id`, `vehicle_model`, `vehicle_code_mock`; [screen spec](docs/design/screen-spec.md) vẫn còn trường `name`/`phone`, cần đồng bộ trước khi triển khai.
  - Loại bỏ hướng dẫn kỹ thuật chưa kiểm chứng trong bot response; bổ sung liên kết đến Ứng dụng VinFast chính thức cho luồng dịch vụ.
  - Tài liệu ngày 24/09 ghi URL [hướng dẫn ứng dụng VinFast](https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast); không có bằng chứng trong repo cho lần kiểm tra ngày đó. Metadata đã được [rà soát lại ngày 27/09](docs/change-report-2026-09-27-rag-metadata.md).
  - **Tạo Dataset Đánh giá:** Khởi tạo `eval/datasets/triage_cases_v1.jsonl` với 12 ca và cập nhật mục tiêu đo lường trong `eval/results/report.md`; chưa có script chạy benchmark hoặc kết quả đo.

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|---|---|---|
| Tài liệu nhóm ghi nhận khảo sát n=4 và có thông tin cá nhân | Chỉ đưa case mô phỏng vào repo; giữ dữ liệu gốc ngoài repo | Giảm nguy cơ lộ PII trong dữ liệu demo; chưa đánh giá được dữ liệu khảo sát gốc hoặc PII trong tin nhắn tự do |
| Nguy cơ Agent đưa ra hướng dẫn kỹ thuật không an toàn / chưa kiểm chứng | Tài liệu quy định phản hồi an toàn và chuyển Staff Review | Chưa có code/test để xác nhận guardrail hoạt động |
| Mâu thuẫn giữa giới hạn 1-2 câu hỏi làm rõ và việc thu thập 3 trường bắt buộc của sự cố sạc | Tài liệu cho phép 1 câu hỏi gom nhiều dữ kiện kèm Quick Replies; tối đa 2 lượt hỏi | Chưa kiểm thử trải nghiệm người dùng hoặc enforcement trong code |

### Bài học
- Tín hiệu khảo sát thăm dò gợi ý thứ tự ưu tiên tính năng, nhưng chưa đủ để xác thực cho toàn bộ khách hàng.
- Cần tách biệt rõ ràng giữa "Mục tiêu đánh giá" (Evaluation Targets) và "Kết quả đã đạt được" trong tài liệu kỹ thuật để giữ tính trung thực khoa học.

### Kế hoạch tiếp theo
- [ ] **Việt:** Review và đồng bộ Scope, screen spec không PII, README/backlog; chốt Figma link và 4 màn giao diện chính.
- [ ] **Long:** Chốt rule matrix, ngưỡng HITL và logic LangGraph clarification bounds.
- [ ] **Khôi:** Mở rộng bộ eval benchmark lên 40 test cases mô phỏng; hoàn thiện script kiểm thử tự động.
- [ ] **Triển:** Khóa status enum và schema không PII; triển khai Case/Ticket lifecycle API trên FastAPI.
- [ ] **Cả nhóm:** Tập trung build hoàn thiện Flow 1 (Vertical Slice Charging) trước ngày 29/09/2026.

### Kết quả rà soát WORKLOG ngày 27/09

- Đã đối chiếu từng dòng công việc trước 26/09 trong [bảng kiểm tra WORKLOG](WORKLOG.md). Các mục `Có bản thảo`/`Có tài liệu` xác nhận sự tồn tại của tài liệu, không xác nhận tính năng đã chạy hoặc kết quả khảo sát.
- Chưa thể xác minh việc nộp Mentor Duty, bản form khảo sát và dữ liệu khảo sát gốc bằng repo hiện tại. Không thêm những tài liệu có thể chứa PII vào repo khi chưa được phép và kiểm tra nội dung.
- Các điểm cần đóng tiếp: README/backlog, mâu thuẫn PII giữa screen spec và API contract, dataset 40 ca cùng script đánh giá, agent guardrails, Case lifecycle API và Flow 1 E2E.
