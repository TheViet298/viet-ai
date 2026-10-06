# Bộ dữ liệu dịch vụ ô tô VinFast

Cập nhật: 2026-09-30. Đây là dữ liệu tình huống mô phỏng phục vụ hai luồng sẽ xây dựng sau; chưa phải kết quả chạy RAG hoặc Agent.

| Bộ dữ liệu đang sử dụng | Chủ đề | Định dạng | Số case | Case mới |
| --- | --- | --- | ---: | ---: |
| [after_sales_customer_care_v1.csv](after_sales_customer_care_v1.csv) | Hậu mãi và chăm sóc khách hàng | CSV UTF-8 | 61 | 40 |
| [triage_service_support_v1.jsonl](triage_service_support_v1.jsonl) | Thông tin cứu hộ, hỗ trợ trên đường, Dịch vụ > Cảnh báo | JSONL UTF-8 | 50 | 40 |

## 1. Hậu mãi và chăm sóc khách hàng — chuẩn bị cho RAG

CSV chứa câu hỏi và câu trả lời tham chiếu về liên hệ CSKH, phản ánh dịch vụ, tìm xưởng, đặt/đổi lịch, tiến độ và thanh toán dịch vụ, bảo dưỡng, sửa chữa lưu động, bảo hành xe/phụ tùng, pin mua và hợp đồng pin thuê còn áp dụng. Không chứa các nhãn phân loại như `expected_intent`, `expected_priority`, `is_critical`, `expected_action` hoặc `requires_staff_review`.

| Cột | Nội dung |
| --- | --- |
| `id` | `TEST-*` cho case chuyển từ bộ cũ; `AFTERSALES-001` đến `AFTERSALES-040` cho case mới |
| `user_message` | Câu hỏi hoặc phản ánh giả lập bằng tiếng Việt |
| `answer` | Nội dung tham chiếu để đối chiếu câu trả lời sau này; không phải phê duyệt quyền lợi cá nhân |
| `citations` | Mảng JSON trong một ô CSV, có thể đọc bằng `json.loads`; không phải chuỗi URL ghép tùy ý |
| `as_of`, `market` | Ngày kiểm tra nội dung và thị trường VN |
| `notes` | Phạm vi áp dụng và ghi chú nguồn gốc câu hỏi |

Mỗi hàng có ít nhất một citation với `source_id`, `title`, `url`, `verified_at`, `status_code`, `applicable_models`, `source_type` và `relevant_snippet`. Các đoạn mô tả nguồn được diễn giải (`snippet_type: PARAPHRASE`). `status_code: null` vì đọc được nội dung qua trình duyệt chưa xác nhận mã HTTP đáng tin cậy. `applicable_models: []` nghĩa là chưa kiểm chứng phạm vi theo từng model; không có nghĩa mọi dòng xe đều hỗ trợ.

Đã đọc [rag-and-data-sources.md](../../docs/architecture/rag-and-data-sources.md) tại `origin/feature/documents-crud`, revision `2b7b3ae0caeb57eb08ef5375a75f07458499f0f8`. Áp dụng yêu cầu nguồn VinFast công khai, metadata và fallback. Không sao chép các ví dụ HTTP 200 hoặc phạm vi toàn bộ model khi chưa xác minh. Nguồn được mở lại ngày 2026-09-30; khi nạp tài liệu thật cần lưu trạng thái HTTP và phiên bản của chính lần nạp đó.

Các FAQ cũ có thể khác chính sách hiện hành. Đối chiếu trang chính sách/sổ đúng dòng xe và hợp đồng; không dùng hướng dẫn app cũ để khẳng định có thể đăng ký thuê pin mới. Không coi thời hạn dự kiến, biểu mẫu gửi yêu cầu hoặc mục giới thiệu quyền lợi là xác nhận lịch hẹn, tồn kho, điều phối hay phê duyệt bảo hành cho một khách cụ thể.

CSV này là tập QA tham chiếu. Khi đánh giá RAG, nạp tài liệu nguồn riêng; không nạp đáp án của chính tập đánh giá làm tài liệu truy xuất. Kiểm thử fallback không có nguồn/điểm dưới 0.70 theo tài liệu kiến trúc vẫn cần bổ sung vào harness sau này.

## 2. Hotline xưởng dịch vụ — chuẩn bị cho Agent

Bộ 50 case dịch vụ của feature/ai-khoi được lưu riêng tại `triage_service_support_v1.jsonl`; không thay thế master benchmark `triage_cases_v1.jsonl` trên develop. Mỗi dòng là một JSON object độc lập, như định dạng gốc; đây không phải một mảng JSON trong file `.json`.

Case mới dùng ID `HOTLINE-001` đến `HOTLINE-040`, với ba nhóm `topic`:

- `RESCUE_INFORMATION`: kênh cứu hộ, phạm vi thông tin, SOS/eCall và tình huống cần cứu hộ khẩn cấp.
- `ROADSIDE_ASSISTANCE`: xe hết năng lượng, nguồn 12V, lỗi sạc, hỗ trợ xưởng và theo dõi yêu cầu trên đường.
- `SERVICE_WARNINGS`: cảnh báo trên ứng dụng/taplo, rùa vàng, báo lỗi chưa rõ, ngữ cảnh và phủ định tín hiệu nguy hiểm.

Giữ `user_message`, `expected_intent`, `expected_priority`, `requires_clarification`, `clarification_fields`, `is_critical`, `notes` và các trường tùy chọn vốn có như `context_history`, `expected_brief`, `citations`. Bộ JSONL có nhãn vì dùng để đánh giá Agent triage. Các nhãn ưu tiên dựa trên [quy tắc triage của dự án](../../docs/architecture/triage-and-hitl-rules.md), không phải định nghĩa mức độ lỗi của VinFast.

Các trường bổ sung cho việc đánh giá sau này:

- `expected_action`: `ANSWER_WITH_CITATIONS`, `CLARIFY`, `CREATE_TICKET` hoặc `ESCALATE_EMERGENCY`.
- `requires_staff_review`, `expected_routing`, `expected_status`: kỳ vọng bàn giao; tên routing là nhãn đánh giá đề xuất, chưa phải danh mục bộ phận đã triển khai. `expected_status` được bỏ trống khi Agent còn đang hỏi làm rõ hoặc chỉ trả lời thông tin.
- `clarification_turns_used`: số lượt Agent đã chủ động hỏi. Sau hai lượt còn thiếu dữ kiện, không hỏi lượt ba; tạo hồ sơ `Needs Information` cùng `missing_fields`.
- `expected_quick_replies`, `expected_clarification_message_count`: một tin nhắn hỏi gom dữ kiện, kèm lựa chọn nhanh.
- `expected_brief`: chỉ kiểm tra các dữ kiện khách đã cung cấp; là tập trường tham chiếu, không phải toàn bộ response API. Không điền giá trị phỏng đoán.
- `expected_hotline`, `safety_trigger`, `triage_policy_ref`: kiểm tra xử lý khẩn cấp trước khi hỏi làm rõ.

Các tình huống khẩn cấp phải bỏ qua clarification và bàn giao Staff ngay. Tình huống phủ định từ nguy hiểm, chuyển từ HIGH sang CRITICAL trong hội thoại, mã lỗi hư cấu và yêu cầu cam kết chi phí/thời gian dùng để kiểm tra suy diễn sai. `DEMO-W01`, các địa điểm/trạm mô phỏng và nội dung hội thoại không chứng minh mã lỗi hay ca dịch vụ có thật. Agent không tự chẩn đoán, xóa cảnh báo, yêu cầu mật khẩu/OTP hoặc cam kết đã điều phối cứu hộ khi chưa có xác nhận của công cụ/nhân viên.

Hướng dẫn giao diện app chỉ mô tả khả năng trong tài liệu được trích dẫn; cần kiểm tra dòng xe và phiên bản thực tế. Citation nguồn công khai không thay cho nhận định chuyên môn hoặc xác nhận của xưởng.

## 3. Chuyển đổi từ bộ hỗn hợp cũ

[archive/triage_cases_v1_mixed_2026-09-30.jsonl](archive/triage_cases_v1_mixed_2026-09-30.jsonl) lưu nguyên byte toàn bộ 52 case ban đầu trước khi tách, từ nhánh `feature/ai-khoi` tại commit `397deef`. Không dùng archive cùng hai bộ mới trong một lần benchmark vì có case lặp.

| Case cũ | Xử lý |
| --- | --- |
| `TEST-006`, `TEST-008`, `TEST-013`–`TEST-016`, `TEST-035`–`TEST-048`, `TEST-050` | Chuyển 21 case sang CSV; bỏ nhãn triage; sửa câu trả lời phản ánh thành hướng dẫn kênh tiếp nhận |
| `TEST-001`–`TEST-005`, `TEST-007`, `TEST-009`–`TEST-012` | Giữ 10 case trong JSONL hotline; bổ sung metadata và kỳ vọng bàn giao |
| `TEST-017`–`TEST-034`, `TEST-051` | Chỉ giữ trong archive: tư vấn mua xe, mẫu mã, màu và tồn kho nằm ngoài hai chủ đề dịch vụ |
| `TEST-049`, `TEST-052` | Chỉ giữ trong archive: báo giá chưa có nguồn và điều khiển điểm RAG không phải QA có citation; dành cho harness fallback sau này |

Hai bộ đang sử dụng có tổng cộng 111 case, gồm 31 case chuyển đổi và 80 case mới. Chưa chạy baseline Agent/RAG; kiểm tra dữ liệu chỉ xác nhận định dạng, số lượng, tính duy nhất, metadata citation và tính nhất quán của nhãn.


<!-- update info from feature/ai-khoi branch -->
## 4. Tích hợp vào develop và ranh giới benchmark

- `triage_cases_v1.jsonl` và `triage_train_v1.jsonl`, `triage_dev_v1.jsonl`, `triage_test_v1.jsonl` giữ nguyên bộ benchmark của Long.
- `triage_service_support_v1.jsonl`: 50 case cứu hộ/cảnh báo/hỗ trợ trên đường của Khôi, giữ nguyên schema `user_message`; cần harness riêng hoặc adapter trước khi dùng với runner đọc trường `input`.
- `after_sales_customer_care_v1.csv`: 61 case QA hậu mãi của Khôi, cần harness RAG riêng.
- Archive 50 case trước merge và archive 52 case hỗn hợp được giữ nguyên để truy vết; không đưa archive vào benchmark để tránh trùng dữ liệu.
- Báo cáo `eval/results/report.md` và kết quả benchmark trên develop được giữ nguyên. PR chỉ bổ sung dữ liệu, không công bố kết quả đánh giá mới.
