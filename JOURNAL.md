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
- [x] **Việt:** Review và đồng bộ Scope, screen spec không PII, README/backlog; chốt Figma link và 4 màn giao diện chính.
- [x] **Long:** Chốt rule matrix, ngưỡng HITL và logic LangGraph clarification bounds.
- [x] **Khôi:** Mở rộng bộ eval benchmark lên 40 test cases mô phỏng; hoàn thiện script kiểm thử tự động.
- [x] **Triển:** Khóa status enum và schema không PII; triển khai Case/Ticket lifecycle API trên FastAPI.
- [x] **Cả nhóm:** Tập trung build hoàn thiện Flow 1 (Vertical Slice Charging) trước ngày 29/09/2026.

### Kết quả rà soát WORKLOG ngày 27/09

- Đã đối chiếu từng dòng công việc trước 26/09 trong [bảng kiểm tra WORKLOG](WORKLOG.md). Các mục `Có bản thảo`/`Có tài liệu` xác nhận sự tồn tại của tài liệu, không xác nhận tính năng đã chạy hoặc kết quả khảo sát.
- Chưa thể xác minh việc nộp Mentor Duty, bản form khảo sát và dữ liệu khảo sát gốc bằng repo hiện tại. Không thêm những tài liệu có thể chứa PII vào repo khi chưa được phép và kiểm tra nội dung.
- Các điểm cần đóng tiếp: README/backlog, mâu thuẫn PII giữa screen spec và API contract, dataset 40 ca cùng script đánh giá, agent guardrails, Case lifecycle API và Flow 1 E2E.

---

## Week 3: 2026-10-01 - 2026-10-07 (Gate G2: Nghiệm thu Vertical Slice, Chuẩn hóa UI/UX Chat, Bản đồ Vị trí ADR-005 & Đánh giá Model)

### Mục tiêu tuần này
- [x] Nghiệm thu toàn diện Vertical Slice Flow 1: Sự cố sạc (`Charging/Battery`) E2E kết nối giữa Customer Chat $\rightarrow$ Clarify $\rightarrow$ Case Brief $\rightarrow$ Staff Console $\rightarrow$ Track Case.
- [x] Chuẩn hóa giao diện Chat theo nguyên tắc "Một tin nhắn chỉ một box", loại bỏ triệt để anti-pattern "box lồng box", phục hồi 70% không gian hội thoại.
- [x] Triển khai bản đồ dịch vụ & cơ chế xin quyền vị trí theo ADR-005: Docking thanh consent trên ô nhập, tính khoảng cách Haversine chính xác theo GPS thật, làm mờ ghim ngoài nhóm lọc.
- [x] Tái cấu trúc Hero Section trang chủ với tông giọng trung tính "Bạn cần hỗ trợ gì về xe điện?", cân bằng 4 nhóm ý định và xoay vòng placeholder.
- [x] Mở rộng bộ dataset đánh giá, xây dựng báo cáo kiểm thử thực tế Gate 2 ([docs/eval_evidences.md](docs/eval_evidences.md)).

### Đã hoàn thành
- **Tích hợp Full-stack & Nghiệm thu Flow 1:**
  - Hoàn thiện trọn vẹn luồng tiếp nhận từ Web Chat, tự động phân loại 4 Intent chính, kích hoạt làm rõ tối đa 2 lượt kèm Quick Replies.
  - Tổng hợp Case Brief có cấu trúc, chuyển giao an toàn lên Staff Console cho nhân viên rà soát, chỉnh sửa và phê duyệt (HITL).
- **Đột phá UI/UX Frontend (Tuân thủ screen-spec & ADR-005):**
  - Khung Chat: Tin nhắn gom gọn trong 1 box xám duy nhất, chip trích dẫn nguồn 1 dòng, sticky red banner khẩn cấp 46px ngay dưới Navbar cho ca cao tốc/rùa vàng.
  - Bản đồ Dịch vụ: Panel tỷ lệ 45% chiều cao, hiển thị trọn vẹn nút bấm Chỉ đường / Gọi hotline, tính khoảng cách Haversine chuẩn xác từ GPS của người dùng đến các trạm sạc và xưởng dịch vụ chính hãng.
  - Trang chủ Landing Page: Tông giọng trung tính, dropdown chọn dòng xe thông minh (tự điền cho Customer đã đăng nhập, không bắt buộc với Guest).
- **Hệ thống Đánh giá & RAG:**
  - Đánh giá 5 tình huống thực tế Gate 2 (TC01 - TC05) với dữ liệu thật, xác nhận cơ chế an toàn và quy tắc dừng làm rõ sau 2 lượt.
  - Mở rộng kho tri thức tra cứu lên 7 nguồn dữ liệu chính thức từ VinFast (SRC-001 đến SRC-007).

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|---|---|---|
| Bản đồ dịch vụ chiếm quá nhiều diện tích, che khuất nút hành động trên màn hình nhỏ | Giảm chiều cao panel bản đồ xuống 45%, căn chỉnh danh sách trạm sạc bên dưới | Thẻ trạm sạc gần nhất hiển thị trọn vẹn nút Gọi và Chỉ đường không bị che khuất |
| Giao diện Chat bị phân mảnh do quá nhiều box thông tin con lồng ghép | Áp dụng luật "Một tin nhắn chỉ một box", đưa chỉ dẫn an toàn vào nội dung tin, thu gọn trích dẫn nguồn | Phục hồi 70% diện tích hội thoại, trải nghiệm đọc liền mạch |
| Định kiến "chỉ báo lỗi" trên Hero trang chủ làm giảm tương tác hỏi thông tin và cẩm nang | Chuyển đổi câu hỏi thành "Bạn cần hỗ trợ gì về xe điện?", bổ sung hàng chip cân bằng 4 nhóm ý định | Đáp ứng đầy đủ cả 3 nhóm nhu cầu: sự cố, tra cứu bảo dưỡng, và thông tin ứng dụng |

### Bài học
- Sự phân định rõ ràng giữa AI đề xuất và Con người quyết định (HITL) giúp giảm thiểu rủi ro vận hành mà vẫn duy trì tốc độ tiếp nhận 24/7.
- Giao diện người dùng cần tối giản thông tin phụ để làm nổi bật nội dung trao đổi chính và các chỉ dẫn an toàn cốt lõi.

---

## Week 4: 2026-10-08 - 2026-10-15 (Gate G3: Hardening Bảo Mật Phiên ADR-006, Cô Lập Demo 2 Chiều, Phân Định Dòng Xe & Hoàn Thiện Nghiệp Vụ HITL)

### Mục tiêu tuần này
- [x] Khắc phục triệt để lỗ hổng chiếm đoạt phiên chat (Session Takeover), thiết lập kiến trúc vòng đời đa phiên ADR-006.
- [x] Nâng cấp trải nghiệm hội thoại: Chuẩn hóa xưng hô "Quý khách" - "em", bảng so sánh xe GFM Markdown, trích dẫn nguồn đầy đủ.
- [x] Thiết lập cơ chế cô lập dữ liệu Demo 2 chiều (`is_demo`), 1-click Demo Login cho Staff & Customer, hỗ trợ song song SQLite và PostgreSQL.
- [x] Xử lý dứt điểm bài toán phân định dòng xe (Vehicle Context Resolution): Tách biệt `target_model` và `owned_model`, cô lập ngữ cảnh khi chuyển intent tư vấn $\leftrightarrow$ sự cố, bổ sung trường `vehicle_source` và huy hiệu "Cần xác minh" trên Staff Console.
- [x] Khắc phục lỗi hiển thị banner an toàn trên màn hình theo dõi hồ sơ (`/track-case`) và hoàn thiện tài liệu nghiệp vụ vòng lặp bổ sung dữ kiện (`Needs Information Loop`).
- [x] Xây dựng bộ test hồi quy tự động, đảm bảo 100% test suite vượt qua trước khi đóng Gate.

### Đã hoàn thành
- **Bảo mật Phiên Chat & Vòng đời Đa phiên (ADR-006):**
  - Loại bỏ hoàn toàn truy vấn session ID tự do, chỉ cho phép claim phiên khách hợp lệ qua định dạng `guest:{uuid}`.
  - Phân tách dữ liệu an toàn khi đăng nhập/đăng ký, ngăn chặn rò rỉ IDOR bằng mã lỗi 404 nhất quán, thực hiện xóa cascade sạch sẽ các tin nhắn mồ côi.
- **Trải nghiệm Trợ lý Ảo Nâng cao:**
  - Chuẩn hóa persona thân thiện, chuyên nghiệp: "Chào Quý khách, em là trợ lý VFServ...".
  - Hỗ trợ render Markdown dạng bảng GFM cho câu hỏi so sánh thông số xe (VF3 vs VF5, VF7 vs VF8, v.v.), đính kèm đầy đủ link tài liệu nguồn có kiểm chứng.
- **Cô lập Dữ liệu Demo & Kiến trúc Database Linh hoạt:**
  - Cơ chế cô lập 2 chiều: Tài khoản demo chỉ thao tác trên dữ liệu demo (`is_demo = true`), tài khoản thật hoàn toàn cách ly với dữ liệu thử nghiệm.
  - Tích hợp nút 1-click Demo Login tiện lợi cho cả Cố vấn dịch vụ và Khách hàng trên giao diện đăng nhập.
  - Hỗ trợ driver `psycopg` v3 cho PostgreSQL cùng khả năng fallback linh hoạt về SQLite.
- **Phân định Ngữ cảnh Dòng xe & Tinh chỉnh Luồng Sự cố:**
  - Tách bạch `target_model` (xe đang hỏi tư vấn) và `owned_model` (xe của khách từ hồ sơ đăng nhập).
  - Khi chuyển đổi intent giữa tư vấn mua xe và báo sự cố kỹ thuật: tự động xóa models kế thừa, bảo đảm ngữ cảnh sự cố ưu tiên đúng xe khách sở hữu.
  - Cơ chế xác nhận nhẹ 1 lần (`profile_already_prompted`) kèm gợi ý chips `["Đúng", "Xe khác"]`.
  - Bổ sung trường `vehicle_source` (`"profile"`, `"user_stated"`, `"inferred"`) vào DB `Case` và hiển thị badge màu hổ phách **"Cần xác minh"** trên Staff Console đối với xe suy luận.
- **Khắc phục Lỗi Track-Case & Bổ sung Tài liệu Nghiệp vụ:**
  - Sửa lỗi banner khẩn cấp trên `/track-case`: chỉ hiển thị khi hồ sơ có mức ưu tiên `CRITICAL` hoặc `HIGH`, giải quyết dứt điểm lỗi 409 khi khách thao tác xác nhận an toàn trên ca `Needs Information`.
  - Cập nhật mục 1.1 trong `docs/product/user-flows.md` mô tả chi tiết chu trình xử lý ca thiếu thông tin (`Needs Information Loop`), sequence diagram và 4 quy tắc vận hành phối hợp giữa AI và Nhân viên (HITL).
- **Kiểm thử Toàn diện & Đồng bộ Mã nguồn:**
  - Bổ sung bộ 12 test tự động `test_vehicle_model_resolution.py` đạt tỷ lệ 12/12 PASS.
  - Toàn bộ test suite backend đạt **706 passed**, frontend compile thành công 10/10 routes với 0 error.
  - Đẩy code và đồng bộ hoàn toàn giữa hai remote `origin-viet` và `origin` trên nhánh `test/agent-long`.

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|---|---|---|
| Khách chat hỏi tư vấn VF7 nhưng sau đó báo "xe tôi gặp sự cố", AI bị kế thừa sai dòng xe VF7 thay vì VF8 trong hồ sơ | Tách riêng `target_model` và `owned_model`; xóa model kế thừa khi chuyển sang luồng sự cố; ưu tiên xe nêu rõ > xe hồ sơ > hỏi lại | Phân loại chính xác dòng xe sự cố, không còn nhầm lẫn ngữ cảnh |
| Banner an toàn khẩn cấp hiển thị sai trên ca thông thường (`MEDIUM`/`Needs Information`) tại trang theo dõi, gây lỗi 409 khi bấm xác nhận | Ràng buộc điều kiện hiển thị banner trên frontend strictly theo `priority in ("CRITICAL", "HIGH")` | Trải nghiệm theo dõi hồ sơ chính xác, loại bỏ hoàn toàn lỗi 409 |
| Chuyển đổi giữa SQLite môi trường local và PostgreSQL môi trường production gây lỗi driver và cú pháp migration | Chuẩn hóa driver `psycopg` v3, hàm `ensure_schema()` kiểm tra metadata cột trước khi thực thi `ALTER TABLE` | Khởi chạy mượt mà trên cả 2 hệ quản trị cơ sở dữ liệu |

### Bài học
- Ngữ cảnh hội thoại (Context Tracking) trong AI Agent cần phân định rõ ràng giữa "ngữ cảnh tham vấn" và "ngữ cảnh tài sản thực tế" để tránh suy luận sai lệch khi khách hàng chuyển ý định bất ngờ.
- Sự kết hợp chặt chẽ giữa cờ cảnh báo AI (`inferred`) và giao diện trực quan cho nhân viên ("Cần xác minh") là mô hình Human-in-the-loop lý tưởng để vừa tăng tốc độ xử lý, vừa bảo đảm an toàn dữ liệu.

### Kế hoạch tiếp theo
- [ ] Hoàn thiện slide thuyết trình (Pitch Deck) và Video Demo 5 phút theo chuẩn 10 Deliverables của BTC.
- [ ] Chuẩn bị môi trường triển khai trực tiếp (Live Deployment) và nghiệm thu tổng thể Gate G3.

