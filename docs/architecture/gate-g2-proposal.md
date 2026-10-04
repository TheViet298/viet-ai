# Gate G2 — bản nháp hợp đồng thống nhất

**Trạng thái:** Đề xuất để nhóm rà soát, chưa phê duyệt (2026-09-27). Tài liệu này **không** thay thế đặc tả hiện hành và không chứng minh Gate G2 đã hoàn tất. Sau khi nhóm chốt, mới đồng bộ `ARCHITECTURE.md`, `docs/architecture/api-contract.md`, `docs/architecture/data-model.md`, `docs/architecture/agent-workflow.md`, `docs/design/screen-spec.md`, `docs/product/problem-and-mvp-scope.md` và những tài liệu liên quan có hợp đồng cũ.

## 1. Phạm vi và nguồn chuẩn đề xuất

- Flow 1 (tiếp nhận, phân loại, hỏi làm rõ, tạo Case Brief, bàn giao HITL) là phạm vi triển khai trước. FAQ/RAG tự trả lời là phần sau Flow 1; hợp đồng có chỗ cho nó nhưng không được coi là đã triển khai.
- `api-contract.md` là nguồn chuẩn cho HTTP request/response; `data-model.md` cho trạng thái và lưu trữ; `triage-and-hitl-rules.md` cho quy tắc AI/HITL. Các tài liệu còn lại phải tham chiếu, không định nghĩa biến thể riêng.
- Demo chỉ dùng dữ liệu giả và `mock_customer_id`; không thu thập hay lưu `name`, `phone`, thông tin khách hàng thật. `case_id` không thay cho quyền truy cập: API khách hàng phải kiểm tra case thuộc phiên `session_id`; API nhân viên cần xác thực vai trò, `staff_id` lấy từ phiên xác thực chứ không tin giá trị client gửi.

## 2. Endpoint và hợp đồng JSON đề xuất

| Endpoint | Mục đích | Request | Response thành công |
| --- | --- | --- | --- |
| `POST /api/v1/customer/chat` | Nhận lượt chat, hỏi rõ hoặc tạo case | `session_id`, `message`, `case_id` (`null` trước khi tạo case), `client_context` tùy chọn chỉ gồm mã giả/dữ liệu xe | Envelope `success/data/error/meta`; `data.response_type` = `CLARIFICATION`, `CASE_CREATED`, hoặc `FAQ_ANSWER` (sau Flow 1) |
| `GET /api/v1/customer/cases/{case_id}/status` | Xem trạng thái case của phiên | Header `X-Session-Id`; kiểm tra sở hữu phiên | `case_id`, `status`, `updated_at`, `customer_message` |
| `POST /api/v1/customer/cases/{case_id}/actions` | Xác nhận đã giải quyết hoặc mở lại | Header `X-Session-Id`; `action` = `CONFIRM_RESOLUTION` hoặc `REOPEN`; `reason` cho REOPEN | `case_id`, `status`, `updated_at` |
| `GET /api/v1/staff/tickets` và `GET /api/v1/staff/tickets/{case_id}` | Hàng đợi và chi tiết reviewer | Phiên nhân viên được xác thực; filter status/priority tùy chọn | Danh sách hoặc chi tiết case kèm Case Brief và audit |
| `POST /api/v1/staff/tickets/{case_id}/actions` | Reviewer quyết định | `action` = `APPROVE`, `EDIT_BRIEF`, `REROUTE`, `REQUEST_INFO`, `RESOLVE`, `CLOSE`, `REOPEN`; `edited_brief`/`notes`/`target_team` theo action; không nhận `updated_status` hay `staff_id` tự khai | `case_id`, `status`, `brief`, `updated_at`, `audit_event_id` |

Mọi response dùng envelope `success`, `data`, `error`, `meta`. Lỗi dùng mã rõ ràng (`VALIDATION_ERROR`, `NOT_FOUND`, `FORBIDDEN`, `INVALID_TRANSITION`, `CONFLICT`) và HTTP 400/403/404/409 tương ứng. `CLARIFICATION` luôn có `case_id: null`, không có ticket cho đến khi hệ thống tạo case. Lượt trả lời tiếp theo dùng cùng `session_id` và `case_id: null`; sau khi đã tạo case mới gửi `case_id`. `CASE_CREATED` trả `case_id`, `status`, `intent`, `priority`, `customer_message`; `FAQ_ANSWER` phải có citation nguồn đã xác minh. Không có `NO_SOURCE` response type: thiếu nguồn thì tạo case cho nhân viên và không bịa câu trả lời.

## 3. Status và chuyển trạng thái đề xuất

Giữ **một** bộ status hiển thị/lưu trữ: `New`, `Needs Information`, `Staff Reviewing`, `In Progress`, `Resolved`, `Closed`, `Reopened`. `New` chỉ là trạng thái khởi tạo nội bộ; response tạo case phải phản ánh trạng thái sau triage. Không dùng các giá trị cũ `OPEN`, `WAITING_USER`, `PENDING_REVIEW`, `ROUTED`.

| Từ | Sang | Điều kiện / tác nhân |
| --- | --- | --- |
| `New` | `Staff Reviewing` | Đủ dữ kiện, confidence thấp, có safety flag, hoặc bắt buộc HITL |
| `New` | `Needs Information` | Chưa đủ dữ kiện sau tối đa 2 lượt hỏi làm rõ; không phải tình huống nguy hiểm |
| `Needs Information` | `Staff Reviewing` | Khách bổ sung dữ kiện, hoặc reviewer quyết định xử lý với dữ kiện hiện có |
| `Staff Reviewing` | `Needs Information` | Reviewer `REQUEST_INFO` nêu rõ trường cần bổ sung |
| `Staff Reviewing` | `In Progress` | Reviewer `APPROVE`/`REROUTE` và xác nhận tuyến xử lý; `EDIT_BRIEF` đơn lẻ không đổi status |
| `In Progress` | `Resolved` | Nhân viên `RESOLVE` ghi kết quả; AI không tự giải quyết |
| `Resolved` | `Closed` | Khách `CONFIRM_RESOLUTION`, hoặc nhân viên `CLOSE` có lý do/audit |
| `Resolved` hoặc `Closed` | `Reopened` | Khách hoặc nhân viên `REOPEN` có lý do |
| `Reopened` | `Staff Reviewing` | Hệ thống đưa vào hàng chờ reviewer, không tự dispatch lại |

Các chuyển trạng thái khác trả `409 INVALID_TRANSITION`. Mọi action ghi audit với actor, thời gian, từ/sang status và lý do. Không coi việc tạo Case Brief hay gợi ý tuyến là đã dispatch.

## 4. Case Brief đề xuất

`case_brief` có các trường: `summary` (tóm tắt trung tính, không suy diễn), `captured_fields` (object dữ kiện khách cung cấp theo intent), `missing_fields` (array tên trường), `suggested_action` (đề xuất cho nhân viên, không phải lệnh tự động), `suggested_routing` (nhóm tiếp nhận đề xuất), `confidence_score` (điểm phân loại intent 0–1), `safety_flags` (array), `is_edited_by_staff` (boolean). `intent`, `priority`, `status`, `source_channel`, `case_id` nằm ở case/ticket, không lặp biến thể tên trong brief. Dữ kiện không có phải để `null`/thiếu và ghi vào `missing_fields`, không được bịa. `captured_fields` có thể chứa `vehicle_model`, `station_location`/`charger_id`, `symptom`/`error_code`, `drivable_state`, `complaint_site` tùy intent; không chứa name/phone thật. Với FAQ/RAG sau Flow 1, citation nằm trong answer/source references, không thay cho dữ kiện khách hàng.

## 5. Ngưỡng AI và HITL đề xuất

- Bộ kiểm tra an toàn chạy trước LLM. Tín hiệu nguy hiểm/khẩn cấp -> `CRITICAL`, hiển thị hướng dẫn an toàn và hotline đã xác minh, tạo case `Staff Reviewing` và báo reviewer ngay; không tuyên bố đã điều xe/cứu hộ.
- Intent confidence `< 0.60` -> case `Staff Reviewing`, không tự trả lời. Từ `0.60` trở lên, nếu thiếu dữ kiện và không nguy hiểm, hỏi tối đa **2 lượt**; sau đó tạo case `Needs Information` nếu vẫn thiếu. Ngưỡng này là quy tắc định tuyến, không phải cam kết độ chính xác.
- Mọi case `Charging/Battery`, `Service/Incident`, `Complaint/Feedback` và mọi case `HIGH`/`CRITICAL` đều qua reviewer trước dispatch. `Sales/General Info` tạo case cũng qua reviewer khi cần bàn giao.
- FAQ tự trả lời (giai đoạn sau Flow 1) chỉ khi intent confidence `>= 0.85`, retrieval similarity `>= 0.70`, nguồn/citation đã xác minh và không có safety/financial-sensitive flag. Không đủ một điều kiện -> không suy diễn câu trả lời, tạo case `Staff Reviewing`. Các ngưỡng cần hiệu chỉnh bằng tập đánh giá trước khi tuyên bố đạt KPI.
- AI chỉ đề xuất brief/tuyến; reviewer xác nhận, chỉnh sửa hoặc yêu cầu thông tin. Tất cả quyết định dispatch, cam kết tài chính, kết luận kỹ thuật và đóng case thuộc con người.

## 6. Điểm cần nhóm xác nhận

1. Có chấp nhận endpoint customer actions mới cho `CONFIRM_RESOLUTION`/`REOPEN`, và mô hình kiểm tra quyền truy cập theo phiên demo không?
2. Có chấp nhận bộ status và action ở trên, đặc biệt `New`/`Reopened` là trạng thái chuyển tiếp và `REQUEST_INFO` đưa case về `Needs Information` không?
3. Có chấp nhận cấu trúc Case Brief và loại `name/phone` khỏi screen spec lẫn data model không?
4. Có chấp nhận các ngưỡng `0.60`/`0.85`/`0.70` là giá trị khởi đầu cần đánh giá, không phải KPI đã đạt không?
5. Sau khi chốt, cần đồng bộ cả các bản vẽ/tài liệu giới thiệu có endpoint hoặc ngưỡng cũ (ví dụ `docs/architecture/system-overview.md`, `docs/architecture_diagram.md`, `README_boilerplate.md`), ngoài sáu file chính.
