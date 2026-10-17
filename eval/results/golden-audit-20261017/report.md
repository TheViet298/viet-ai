# Audit Golden testcase — 17/10/2026

Đây là báo cáo audit trước khi duyệt triển khai. Người dùng đã duyệt nâng cấp sau đó; xem [kết quả Golden v2 đã triển khai và chạy offline/live](../golden-v2-20261017/report.md) để biết trạng thái cuối.

## Kết luận

**Chưa đủ bằng chứng để coi golden hiện tại là cổng nghiệm thu chất lượng hoặc xác nhận phủ đủ model.** Bộ v1 hữu ích cho hồi quy hợp đồng đầu ra. Các ca hiện tại đạt không chứng minh các nhánh LLM đã thực sự được gọi.

Đã kiểm tra workspace hiện tại, bao gồm những thay đổi có sẵn của người dùng trong `src/services/{agent_llm,image_routing,llm,observability}.py`. Không sửa các thay đổi đó trong quá trình audit. Báo cáo cũ ngày 14/10 không đại diện kết quả hiện tại.

## Kiểm chứng thực tế

- Dataset: 60 case, 77 lượt, dài nhất 3 lượt; safety 15, triage 20, RAG 15, multiturn 10. Tất cả nhãn là `draft_policy_review`; các file `policy_ref` đều tồn tại.
- Baseline ngày 17/10: **174 PASS, 1 FAIL** trong 175 test được chọn; thời gian pytest 21,53 giây. Riêng `test_golden_cases.py`: **62 PASS**, gồm 60 ca và 2 kiểm tra dataset/comparator.
- Failure: `tests/test_services/test_chat_normalization.py::test_normalization_client_uses_separate_google_model`. Cấu hình yêu cầu `gemini-2.5-flash-lite` nhưng factory tạo `gemini-3.5-flash-lite`.
- XML: `.test-runs/golden-audit-unrestricted-20261017.xml`.
- Đợt kiểm tra sâu thêm: **159 PASS** trong 18,20 giây, gồm bilingual/hypothetical safety, các mệnh đề có ngữ cảnh, memory remediation, answer evidence, LLM/RAG budgets, localization, conversation context, dashboard/exterior Vision và auto routing. XML: `.test-runs/golden-hard-audit-20261017.xml`.
- Tổng hai lượt: **333 PASS, 1 FAIL / 334 test**. Đây là các test được chọn theo phạm vi audit, không phải toàn bộ repository và không phải 334 golden case.
- Lần đầu chạy trong sandbox kẹt tại `socket._fallback_socketpair -> asyncio` trước khi vào thân async test. Đã hủy và chạy lại ngoài sandbox; không quy hiện tượng đó thành lỗi ứng dụng.
- Các lượt pytest dùng fixture tắt LLM/Langfuse, database và Chroma tạm. Chưa chạy provider thật trong đợt audit này.

## Model và công đoạn

| Vai trò | Cấu hình hiện tại | Nơi gọi | Lỗ hổng bằng chứng hiện tại |
| --- | --- | --- | --- |
| Chat, triage, RAG, hiểu lượt, tóm tắt, dịch | `gpt-4o-mini` | `get_llm` / `structured_call` | Golden offline không gọi model; live không buộc đúng model hoặc từng prompt |
| Chuẩn hóa viết tắt theo ngữ cảnh | `gemini-2.5-flash-lite` | `get_normalization_llm` | Adapter đổi thành `gemini-3.5-flash-lite`; regression hiện đang FAIL |
| Phân loại ảnh, đọc dashboard, nhận diện ngoại thất | `gpt-6-luna` | `vision.route`, `vision.dashboard`, `vision.exterior` | Live truyền loại ảnh trực tiếp nên không phủ đường `image_kind=auto`; chưa buộc generation đúng công đoạn |
| Vision Google thay thế | `gemini-3.5-flash` | Khi chọn `vision_provider=google` | Cấu hình hiện chọn OpenAI; có test transport giả lập nhưng chưa có bằng chứng live cho cấu hình Google |

Các prompt thực sự có call site cần kiểm tra riêng: `normalization`, `conversation_turn`, `triage`, `general`, `rag_qa`, `memory`, `customer_translation`. Không coi tên model ghi trong metadata mục tiêu là bằng chứng provider đã chạy model đó. Model Google thay thế cần báo cáo là cấu hình thay thế, không gộp vào độ phủ của cấu hình đang hoạt động.

## Phát hiện có thể tái hiện

### P1 — Bộ chấm live có thể PASS với sai model, sai công đoạn

`scripts/run_live_model_eval.py:27` chỉ cần một generation thành công có token; `:35` chỉ cần một outcome `parsed` bất kỳ. Không ràng buộc outcome với generation, prompt, turn hoặc model.

Đã gọi evaluator trực tiếp với generation `model=wrong-model`, outcome chỉ thuộc `normalization`, response `reply=fallback generic`: kết quả **PASS** cho một case chat yêu cầu model `gpt-4o-mini`. Vì vậy normalization thành công có thể che việc generation câu trả lời không chạy.

### P1 — Tên model chuẩn hóa thực tế khác cấu hình

`src/services/llm.py:29` tự đổi `gemini-2.5-flash-lite` thành `gemini-3.5-flash-lite`. Không được dùng trace gắn tên cấu hình để khẳng định model cũ đã được kiểm thử. Cần thống nhất model cấu hình, model gửi provider và model trả về; nếu alias có chủ ý phải ghi minh bạch và kiểm tra alias đó.

### P1 — Script “3 models” chưa phải kiểm thử chất lượng

`scripts/run_three_models_eval.py` có 10 ca nhưng nhánh normalization gọi prompt viết riêng thay vì pipeline chuẩn hóa thật; vision/chat chấm thành công theo HTTP 200. Kết quả lưu trong `tmp/eval-3models-20261017-102911.json` không có verdict/assertion từng ca. Tên `model` lấy từ mục tiêu khai báo. Chưa đủ để kết luận coverage ba model hoặc độ chính xác nội dung.

### P2 — Comparator chấp nhận sai kiểu boolean

`eval/golden.py:25` dùng `actual == expected`. Đã xác nhận `is_safety_trigger=1` được tính PASS với kỳ vọng `true`. Cần so sánh hợp đồng có kiểu, kể cả giá trị lồng nhau; không đổi ý nghĩa nhãn chỉ để tăng tỷ lệ đạt.

### P2 — Hợp đồng rỗng có thể PASS

`evaluate_conversation({'turns':[{}]}, {'turns':[{'expected':{}}]})` chỉ sinh kiểm tra đủ số lượt và PASS. Validator dataset v1 ngăn được hợp đồng này trong dataset hiện tại, nhưng evaluator dùng chung chưa từ chối. Cần validator chung cho dataset/Cloud và fail closed khi không có assertion hoặc có khóa assertion không được hỗ trợ.

### P2 — Chưa kiểm thử nén bộ nhớ bằng golden

`src/services/memory_buffer.py` chỉ nén khi quá 10 message hoặc 8.000 byte. Golden v1 tối đa 3 lượt; cần thêm ít nhất 6–10 lượt hoặc context đủ dài, rồi xác minh dữ kiện được sửa, thông tin đã rút lại, đổi xe, PII và nguy hiểm xuất hiện sau nén. Repository đã có regression memory riêng; nên tái sử dụng bằng chứng đó khi thiết kế golden, không gọi chúng là holdout độc lập.

### P2 — Runner khóa cứng 60 ca và kiểm chứng online quá yếu

`scripts/run_golden_cloud_eval.py:170` từ chối số ca khác 60; nhiều bước readback cũng cố định 60. `online_generation_confirmed` chỉ kiểm tra có generation bất kỳ, kể cả không thành công; chưa phải xác nhận độ phủ model/công đoạn cho từng ca. Mở rộng phải sửa đồng bộ payload, validator, readback, metrics và regression.

### P2 — Câu trả lời tương đương có thể bị chấm trượt

`contains` chỉ kiểm chuỗi nguyên văn sau `casefold`. Báo cáo Cloud cũ đã ghi false negative “nhân viên xác nhận” / “nhân viên sẽ xác nhận”. Cần nhóm biến thể được duyệt hoặc assertion ngữ nghĩa có phạm vi rõ; không dùng fuzzy matching rộng cho số tiền, mã lỗi, mức ưu tiên hoặc khẳng định an toàn.

### P2 — Offline dừng ca ngay khi assertion lượt đầu trượt

`tests/test_eval/test_golden_cases.py:60` assert trong vòng lặp. Khi lượt đầu trượt sẽ không chạy các lượt sau của ca đó, có thể mất bằng chứng cho lần nâng mức nguy hiểm muộn. Harness nâng cấp cần tiếp tục hội thoại, tổng hợp lỗi theo lượt và vẫn trả exit code lỗi.

## Thiết kế nâng cấp để duyệt

Giữ nguyên v1 và báo cáo lịch sử. Bổ sung **120 ca khó đề xuất** ở v2, đưa tổng hai bộ lên 180; không thay nhãn cũ để làm xanh test.

| Nhóm mới | Số ca đề xuất | Tình huống khó cần có |
| --- | ---: | --- |
| Safety đối kháng | 24 | Phủ định theo mệnh đề, quá khứ rồi nguy hiểm hiện tại, giả định xen sự cố thật, tiếng Anh/không dấu, nhiều nguy hiểm, injection yêu cầu hạ CRITICAL |
| Triage/HITL | 16 | Nhiều intent, đổi ý, từ chối cung cấp vị trí, đủ/thiếu dữ kiện ở biên hai lượt hỏi, yêu cầu can thiệp cao áp, không bịa đã điều phối/đặt lịch |
| RAG/grounding | 24 | Sai dòng xe, sai phiên bản/điều kiện, URL ngoài registry, nguồn mâu thuẫn, thiếu citation, số/đơn vị không có nguồn, injection trong snippet, timeout/error, sửa câu hỏi giữa lượt |
| Hội thoại dài | 24 | 6–10 lượt, nén memory, đổi xe thật so với sửa tên xe, rút mã lỗi, đổi mục tiêu, nguy hiểm muộn, PII qua nhiều lượt, tách session/owner |
| Chuẩn hóa | 16 | `bh`/`kh`/`chay` mơ hồ, đơn vị `kWh`/`12V`, mã `CC01`, phủ định, model cố thay số/model/hazard, không được phát sinh hành động |
| Vision | 16 | Auto route, ảnh trống/mờ/lẫn loại, chữ injection, TPMS so với lỗi cảm biến, P so với brake, sai màu cảnh báo, xe không rõ model, PII, không suy đoán hư pin/chi phí |

Case v2 phải có ID ổn định, căn cứ kỳ vọng, `draft_policy_review`, difficulty/risk tags và mô tả nhánh mục tiêu. Ca lấy ý từ regression hiện tại phải được đánh dấu development regression; chưa được xem là holdout độc lập.

Tái sử dụng các runner hiện có để chạy offline và một tập live được chọn có chủ đích. Live cần:

1. Ràng buộc generation thành công với đúng model được yêu cầu, prompt/công đoạn và lượt tương ứng; có usage và output parse/validation thành công. Thiếu bằng chứng trả BLOCKED, sai nội dung trả FAIL.
2. Có ca đi qua đủ 7 prompt chat và đủ `vision.route`/`vision.dashboard`/`vision.exterior`; có ca an toàn bắt buộc **không** gọi model. Ghi rõ nhánh chưa kích hoạt thay vì suy diễn từ tên testcase.
3. Tách điểm correctness, coverage và provider availability; lỗi 401/429/timeout không được tính model đã kiểm thử thành công.
4. Tách database/attachment/Chroma, lưu kết quả từng ca trước readback; có giới hạn số ca/lượt gọi, không chạy ma trận tất cả model với mọi ca một cách lãng phí.
5. Xuất model yêu cầu/thực tế, công đoạn, PASS/FAIL/BLOCKED, assertion lỗi, token/chi phí, latency và đường dẫn bằng chứng. Cấu hình Vision Google chỉ được đánh dấu live-covered khi có lượt chạy riêng thành công.

Điều kiện chấp nhận: các regression của evaluator phải phát hiện được false positive nêu trên; các ca an toàn rủi ro cao đều đạt, không có bypass; danh sách mọi ca thất bại được giữ nguyên và phân loại lỗi sản phẩm/lỗi nhãn/lỗi provider; không tuyên bố đã đủ model khi còn thiếu generation đúng công đoạn.

**Trạng thái triển khai:** Chưa sửa mã/dataset; đang chờ duyệt thiết kế theo skill `brainstorming`. Báo cáo này là kết quả audit và thiết kế để xem xét, không phải kết quả đã nâng cấp.
