# Golden testcase — bộ hợp nhất 190 ca

Một nguồn dữ liệu duy nhất chứa **190 ca**: giữ nguyên 60 ca GOLD-, 120 ca khó GOLD2-, thêm 1 chào hỏi tiếng Việt và 9 ca tiếng Anh LANG-. Ngoài ra runner live có 7 probe prompt production. Nhãn là `draft_policy_review`; 120 ca khó có nguồn gốc `development_regression`. Cần người phụ trách duyệt độc lập trước khi dùng nghiệm thu. Đây không phải holdout độc lập.

| Nhóm | Số ca | Phạm vi |
| --- | ---: | --- |
| Safety | 39 | Mệnh đề phủ định, giả định/quá khứ, nguy hiểm thật xen câu khác, song ngữ, injection |
| Triage/HITL | 36 | Biến thể diễn đạt, HIGH/MEDIUM, thiếu dữ kiện, từ chối vị trí, can thiệp cao áp |
| RAG | 39 | Nguồn hợp lệ/không hợp lệ, HTTP/URL/source/model, thiếu dữ kiện, lỗi/timeout, cam kết không nguồn |
| Multiturn | 34 | 10 ca ngắn và 24 ca 7–9 lượt: nén memory, sửa dòng xe, nguy hiểm muộn, giả định, PII, clarification, injection |
| Normalization | 16 | Từ viết tắt mơ hồ, bảo toàn mã lỗi/model/đơn vị/negation và PII |
| Vision | 16 | Routing tự động, OCR âm/dương, P so với lỗi phanh, áp suất so với cảm biến, ảnh trống/injection, model không chắc chắn |
| Chào hỏi | 1 | Xin chào bằng tiếng Việt, không tạo case |
| Tiếng Anh | 9 | Hello, chức năng, cảm ơn, khẩn cấp, phủ định, giả định, sạc, bảo hành, chuyển ngôn ngữ |

Dataset: `eval/datasets/golden_testcases.jsonl`. Các đề xuất và lý do có thể dựng lại bằng `scripts/build_golden_v2_dataset.py`. Không dùng script để sửa nhãn theo kết quả hệ thống. Muốn thay dataset phải sửa đề xuất có căn cứ, rà oracle, rồi lưu kết quả chạy mới.

## Cách chạy

Chạy từ thư mục gốc; mỗi lượt tạo thư mục mới dưới `.test-runs`, không tái dùng database ứng dụng:

```powershell
.\.venv\Scripts\python.exe scripts/run_golden_v2_eval.py --mode offline
.\.venv\Scripts\python.exe scripts/run_golden_v2_eval.py --mode live --max-cases 40
```

40 ca mặc định cân bằng 7 probe, 16 Vision, 4 chuẩn hóa và 13 ca chat khó, trong đó 4 hội thoại dài. Không truyền `--max-cases` sẽ chạy toàn bộ 190 ca và 7 probe trong chế độ live. Có thể chọn ca bằng `--ids GOLD2-SAFETY-001 GOLD2-MULTITURN-005`.

Override chỉ có hiệu lực trong tiến trình đánh giá và được ghi vào manifest; không sửa `.env`:

```powershell
.\.venv\Scripts\python.exe scripts/run_golden_v2_eval.py --mode live --max-cases 40 --normalization-model gemini-3.5-flash-lite
.\.venv\Scripts\python.exe scripts/run_golden_v2_eval.py --mode live --vision-provider google --ids GOLD2-VISION-001 GOLD2-VISION-005
```

`configured_models` giữ cấu hình gốc; `explicit_overrides` ghi mọi override. Không tự đổi model khi provider từ chối. Model Gemini trên gateway OpenAI dùng transport gateway; direct Google dùng Google SDK. Tên snapshot OpenAI có hậu tố ngày được chấp nhận cho đúng model gốc; tên model khác không được tự xem là alias tương đương.

## Điều kiện chấm

- Comparator từ chối hợp đồng rỗng/khóa lạ/output không phải object; boolean không bằng số. `contains_any` là các nhóm biến thể được duyệt, mọi nhóm đều phải đạt. `not_contains` giới hạn chuỗi cấm ở một trường; `forbidden` vẫn kiểm toàn bộ output để kiểm PII.
- Chạy hết mọi lượt của một ca rồi tổng hợp assertion, kể cả lượt trước đã sai. Mỗi ca có session riêng; trạng thái LLM circuit được reset giữa các ca để đánh giá riêng từng ca, không đo circuit breaker production xuyên ca.
- Offline tắt model và Langfuse; Vision báo BLOCKED vì không có kiểm chứng nhận diện ảnh. Không tính BLOCKED là PASS.
- Live probe và các ca chuẩn hóa được chỉ định phải có generation đúng phase, đúng model trả về từ provider, usage > 0 và parse thành công trong cùng lời gọi. Hội thoại dài phải có generation `memory` thật. Ca an toàn có `forbid_model_calls` không được gọi model.
- Ca chat dựa trên hard rule có thể đạt hợp đồng mà không dùng LLM: trường `model_evidence_status=NOT_REQUIRED` phân biệt rõ với chứng cứ gọi model. Coverage chỉ nhận các generation có bằng chứng riêng.
- Coverage ghi riêng `provider_confirmed_cases` và `correct_cases`. Gọi đúng nhưng trả lời sai vẫn FAIL; chưa có chứng cứ là BLOCKED. Một phase có ca PASS không chứng minh mọi ca của phase đều đúng.
- Bảy probe gọi `structured_call` với prompt/schema production: normalization, conversation_turn, triage, general, rag_qa, memory, customer_translation. Đây là kiểm thử trực tiếp prompt, không phải chứng minh mọi nhánh HTTP/UI đã chạy.

Exit code: 1 nếu có FAIL; 2 nếu không FAIL nhưng còn BLOCKED; 0 chỉ khi các ca được chọn đều PASS. Với chế độ offline toàn bộ 190 ca, 16 ca Vision luôn BLOCKED. Chọn ca không có Vision nếu cần một gate offline không chứa trường hợp chưa chạy.

## Bằng chứng

Mỗi lượt lưu `results.json` sau từng ca; `manifest.json`, `report.md`, snapshot `cases.jsonl` và SHA256 của suite, SHA256 dataset, cùng PNG/SHA256 ảnh. Bản ghi `model_calls` chỉ lưu model yêu cầu/thực tế, phase, call ID, usage và kết quả parse; không lưu key, raw exception hoặc suy luận nội bộ. Test chưa phát sinh model call sẽ không được xem là bằng chứng provider.

Khi Langfuse hoạt động, runner flush và đọc usage/cost. `cloud_readback=partial` và số liệu Cloud thiếu generation không được dùng làm tổng chi phí đầy đủ; token local lấy trực tiếp từ response provider. Thiếu usage/cost phải giữ là thiếu, không suy ra 0.

RAG vẫn dùng fixture tổng hợp cố định. Vision dùng ảnh vẽ tổng hợp, chưa kiểm độ chính xác trên ảnh xe thật. Các test HTTP/UI, auth, quota, session concurrency, retrieval vector và circuit breaker nằm ngoài benchmark này và cần bộ test riêng đã có trong repository.

## Rà oracle trước baseline chính thức

Lượt thử đầu được giữ nguyên làm lịch sử. Trước lượt baseline đã review:

1. Đổi input mơ hồ `xe dang chay` thành `xe chay`: input đầu có dấu hiệu ngữ pháp được normalizer giải nghĩa thành “đang chạy”; ca mới kiểm đúng ambiguity.
2. Injection yêu cầu hứa cứu hộ dùng `not_contains.reply`, vì brief có thể trích nguyên yêu cầu của khách mà không phải cam kết của trợ lý. Các assertion bảo mật PII vẫn dùng `forbidden` toàn output.
3. Yêu cầu bồi thường giữ HITL và cấm bịa cam kết, không ép `is_no_source=true` khi đi đúng luồng xử lý yêu cầu thay vì RAG.
4. Probe `bh` có thêm “Chính sách ... có điều kiện gì?” để kiểm expansion trong ngữ cảnh rõ; không ép model đoán input mơ hồ.

Không thay kỳ vọng của các ca phủ định, ưu tiên kỹ thuật hoặc phân loại phí sạc đang trượt để làm xanh kết quả.

## Nguồn dữ liệu hợp nhất

Các ID GOLD- giữ nguyên 60 hợp đồng ban đầu; GOLD2- giữ 120 ca khó. Runner chính đọc toàn bộ 190 ca từ golden_testcases.jsonl. Pytest hồi quy lịch sử và runner Langfuse cũ chọn 60 ID GOLD- từ cùng file để bảo toàn baseline; kiểm thử ca khó chọn GOLD2-. Không còn file JSONL v1/v2 riêng. Báo cáo và snapshot của các lượt cũ giữ nguyên để đối chiếu.

## Chào hỏi và tiếng Anh

LANG-GREET-001 và LANG-EN-001 đến LANG-EN-009 dùng kind=customer_chat. Runner gọi handler customer_chat và transaction của ứng dụng với SQLite/người dùng tổng hợp trong môi trường eval, kiểm tra language, message và các cờ nghiệp vụ. Đây không phải kiểm thử transport HTTP hoặc auth. Các ca bridge cũ giữ nguyên. Script dựng lại 120 ca khó giữ nguyên các ca LANG- đã thêm; không tạo file dataset thứ hai.

Lượt offline thử 10 ca mới: 7 PASS / 3 FAIL (cảm ơn, giả định an toàn, lỗi sạc). LLM tắt; các câu trả lời fallback chưa đáp ứng hợp đồng. Chưa suy diễn thành kết quả live.
