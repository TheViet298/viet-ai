# Kiểm thử memory theo toàn bộ intent — 19/10/2026

## Phạm vi

Mã nền: `P-142/feature/agent-long`, commit `4a52e27`.
Chạy trong checkout riêng, SQLite tạm theo từng test và người dùng giả lập.
Không dùng dữ liệu khách hàng hay tạo lịch/hồ sơ trên production.

Áp dụng `python-testing`, `test-driven-development`, `systematic-debugging`,
`security-review` và `verification-before-completion`.

Ma trận mới có **396 ca kiểm thử**: 225 hướng chuyển giữa **15 mục tiêu**,
17 kịch bản đại diện cho đủ **5 intent** khai báo trong `IntentType`, cùng
các ca đính chính, phủ định, vị trí, phiên dài và tính nguyên tử của lượt chat.
Kiểm tra tập intent bằng assertion so với enum thật để phát hiện khi enum mở rộng.

## Các chuỗi câu hỏi đại diện

| Mục tiêu | Câu đầu | Câu tiếp theo / yêu cầu memory |
| --- | --- | --- |
| Tư vấn xe | Tư vấn VF8 | Còn VF5 thì sao? → đổi chủ thể sang VF5 |
| Giá/lăn bánh | Giá lăn bánh VF8 Plus mua kèm pin tại Hà Nội? | VF8 Eco, mua kèm pin, đăng ký ở Đà Nẵng → cập nhật phiên bản và nơi đăng ký |
| Lái thử | Tôi muốn đăng ký lái thử VF8 ở Hà Nội | Chiều ngày mai → giữ VF8/Hà Nội, nhớ thời gian, không tự xác nhận đặt lịch |
| Bảo hành | Bảo hành pin VF8 bao lâu? | Còn VF5 thì sao? → giữ chủ đề, không dùng thông số VF8 |
| Bảo dưỡng | Lịch bảo dưỡng định kỳ VF8 là gì? | Còn VF5 thì sao? → giữ chủ đề cho VF5 |
| Đặt bảo dưỡng | Tôi muốn đặt lịch bảo dưỡng VF8 | Ở Đà Nẵng vào chiều ngày mai → giữ mẫu xe và thông tin mới |
| Quãng đường | VF8 đi được bao xa một lần sạc? | Còn VF5 thì sao? |
| Thời gian sạc | VF8 sạc bao lâu? | Còn VF5 thì sao? |
| Dung lượng pin | Dung lượng pin VF8 là bao nhiêu? | Còn VF5 thì sao? |
| Màu sắc | VF8 Plus có màu gì? | Còn VF5 thì sao? → không kế thừa bản Plus của VF8 |
| Khái niệm | SOH là gì? | SOC là gì? → cập nhật đúng khái niệm |
| Ứng dụng | Ứng dụng VinFast có tính năng gì? | Giải thích cụ thể hơn được không? |
| Phí/mạng lưới sạc | Biểu phí sạc tại trạm sạc công cộng | Giải thích cụ thể hơn được không? |
| Khiếu nại | Tôi muốn khiếu nại thái độ nhân viên showroom | Tôi ở Hà Nội → giữ khiếu nại và mã hồ sơ |
| Sự cố sạc | Xe VF8 của tôi không sạc được, mã lỗi CC01 | Trụ P02 tại Vincom Metropolis → không mất mục tiêu sự cố |
| Khẩn cấp | Xe VF8 của tôi đang bốc khói | Tôi đã ở nơi an toàn → chưa tự kết luận xe an toàn hay hủy cảnh báo |
| Ngoài phạm vi | Thời tiết ngày mai thế nào? | Tư vấn VF5 → trở lại đúng mục tiêu trong phạm vi |

Dataset đầy đủ: `eval/datasets/memory_intent_audit_v1.json`.

## Các ranh giới kiểm tra

- Chuyển mục tiêu không giữ slot, hành động đã hủy, câu hỏi chờ hoặc bằng chứng
  câu trả lời của mục tiêu cũ. Đổi mẫu xe không dùng phiên bản, đời xe và phương
  án pin của mẫu trước.
- Câu đính chính có giá trị cũ đứng trước/sau giá trị mới. Ví dụ:
  “Không phải Plus, tôi chọn Eco”; “Không phải Hà Nội, đăng ký ở Đà Nẵng”;
  “Không phải pin cao áp, tôi hỏi ắc quy 12V”; “Không phải đời 2024, xe đời 2025”.
- Rút lại thông tin mà chưa cung cấp thay thế: trạng thái `retracted`, không
  tiếp tục đưa giá trị cũ vào câu truy vấn. Slot bắt buộc bị rút lại được hỏi bổ
  sung; slot khách đã nói `unknown` không bị hỏi lặp.
- Sự cố nhận câu chỉ có mã trụ, tên trạm hoặc địa chỉ. Tên trạm không tự chuyển
  thành câu hỏi về mạng lưới sạc.
- Vị trí: giữ loại điểm, khu vực và loại xe khi hỏi nối tiếp; cập nhật khi khách
  đổi loại xe hoặc yêu cầu gần đây; không lấn sang câu hỏi dịch vụ hay yêu cầu
  đã phủ định.
- Mọi kịch bản API đọc lại state từ DB giữa lượt, đối chiếu câu trả lời với
  memory và lịch sử, giữ đúng mã hồ sơ nếu đã có.
- Mọi intent được kiểm tra phiên mới không nhận memory phiên cũ, người dùng
  khác không lấy được dữ liệu qua cache, request trùng không thêm lượt và cùng
  request ID với nội dung khác trả 409 mà không sửa state.
- Lỗi sau khi đã flush một tin nhắn được mô phỏng với từng intent: rollback
  toàn bộ state/tin nhắn và giải phóng lease. Fault injection sửa cả
  `ChatSession.memory_states` trước khi flush và ném lỗi, không chỉ sửa tin nhắn.
- Hội thoại dài kích hoạt compact vẫn giữ bằng chứng, mẫu xe và phiên bản mới nhất.
- Bộ hiện có tiếp tục kiểm tra ảnh ngoại thất/dashboard, đổi xe và chứng cứ
  ảnh cũ, GPS/consent, guest/claim, xóa phiên, safety, hai ngôn ngữ và nhiều ý.

## Lỗi phát hiện và sửa

1. Bộ lấy slot lấy giá trị đã phủ định trước giá trị mới. Đã bỏ giá trị bị
   phủ định khỏi bước lấy thông tin mới, gồm cả cấu hình “VF8 Plus” và tên
   thành phố viết tắt “TP.HCM”.
2. Rút lại một giá trị nhưng không thay thế vẫn giữ nó như fact hợp lệ.
   Đã đánh dấu `retracted`, bỏ khỏi phần ngữ cảnh bổ sung cho truy vấn và bỏ
   chủ thể nếu khách rút lại mẫu xe.
3. Câu chỉ cung cấp mã trụ/vị trí không được nhận là bổ sung sự cố; mục tiêu bị
   xóa. Đã dùng bộ lấy trường sự cố sẵn có cho các slot này.
4. Câu tên trạm được hiểu thành mục tiêu mạng lưới sạc. Đã phân biệt câu bổ sung
   địa điểm với câu hỏi/tìm kiếm mới.
5. `last_answer` giữ chứng cứ thuộc mục tiêu cũ sau khi đổi intent. Đã xóa cùng
   với slot/hành động cũ.
6. Slot `retracted` bị tính như đã có thông tin. Đã phân biệt với `unknown`
   trong bước xác định thông tin còn thiếu.
7. Bổ sung/đính chính phương án pin trong báo giá làm chuyển sang dịch vụ thuê
   pin và mất phiên bản/nơi đăng ký. Đã giữ mục tiêu báo giá cho câu điền slot,
   đồng thời vẫn cho phép chuyển sang câu hỏi giá/chính sách/dịch vụ thuê pin mới.
   Các câu chuyển rõ sang bảo dưỡng, lái thử hoặc bảo hành vẫn được ưu tiên dù
   có nhắc “mua kèm pin”.

Sửa một test cũ có mock sai chữ ký `answer_sales_question`: mock nay chấp nhận
các tham số model/session truyền theo vị trí. Giữ nguyên các assertion về xe,
chủ đề và quyền truy cập.

## Bằng chứng chạy

- Baseline backend: **1.519 đạt, 8 lỗi, 4 bỏ qua**, 6 subtest đạt.
- Nhóm memory/hội thoại sau sửa và review: **426 đạt**
  (396 ca mới và 30 ca hiện có).
- Frontend: **177 đạt**, không có test lỗi hoặc bỏ qua sau khi cấu hình đúng
  dependencies của checkout.
- Toàn bộ backend trên bản review cuối: **1.916 đạt, 7 lỗi, 4 bỏ qua**, 6 subtest đạt.
  Bảy test lỗi đều thuộc observability/tracing và đã lỗi trong baseline.
- Bốn test bỏ qua vì checkout thiếu snapshot điểm dịch vụ (2 test), thư mục
  crawl (1 test) và notebook huấn luyện ảnh (1 test); không tính các ca này là đạt.
- Lượt chạy coverage toàn suite cho cùng kết quả trên, thời gian 183,36 giây.

Review độc lập đã tái hiện các góc cạnh cấu hình xe, alias thành phố và mục tiêu
thuê pin; mỗi finding có kiểm thử tái hiện trước khi sửa. Sau vòng kiểm tra cuối,
không còn finding cần xử lý trong phần thay đổi được review.

Các lỗi observability/tracing đã tồn tại trong baseline được ghi riêng trong
kết quả toàn suite, không đổi kỳ vọng test để che lỗi.

Các test còn lỗi:

- `test_each_legacy_request_has_one_root_even_for_emergency` (hai route).
- `test_root_decorator_preserves_business_http_error`.
- `test_usage_survives_consumer_parse_failure`.
- `test_timeout_generation_has_error_without_fake_zero_usage`.
- `test_google_non_json_503_still_reaches_retry_consumer`.
- `test_ten_concurrent_model_timeouts_are_identified_independently`.

## Coverage của memory

Đo bằng `coverage.py 7.16.2` với branch coverage trên đúng tám module memory;
đây không phải tỷ lệ coverage của toàn bộ repository.

- Dòng lệnh: **97,00%** (1.003/1.034).
- Nhánh: **92,63%** (415/448).
- Chỉ số tổng hợp dòng và nhánh: **95,68%**.

| Module | Coverage tổng hợp |
| --- | ---: |
| `src/agents/context_manager.py` | 97% |
| `src/services/application_memory.py` | 100% |
| `src/services/chat_turns.py` | 94% |
| `src/services/conversation_context.py` | 97% |
| `src/services/conversation_progress.py` | 97% |
| `src/services/memory_buffer.py` | 100% |
| `src/services/session_store.py` | 92% |
| `src/services/vehicle_context.py` | 97% |

Kết quả chi tiết: `.test-runs/memory-coverage.json`; JUnit:
`.test-runs/memory-accepted-full.xml`; log toàn suite:
`.test-runs/memory-accepted-full.log`. Không tính các test skip là đã kiểm chứng.

## Chạy lại

```powershell
python -m pytest tests/test_services/test_memory_intent_matrix.py tests/test_api/test_memory_all_intents.py -q
python -m pytest -q -rs
cd frontend
node --test tests/*.test.cjs
```

Log chạy nằm trong `.test-runs/memory-*.log` (không commit cache/log).
Các kiểm thử tự động chủ yếu tắt/mock provider theo fixture hiện có, nên đo
được logic, persistence và fallback; chưa chứng nhận chất lượng nhận diện của
provider thật, PostgreSQL thật hoặc bản triển khai Vercel. Các test vision dùng
quan sát giả lập, không phải đánh giá lại mô hình nhận diện ảnh.
