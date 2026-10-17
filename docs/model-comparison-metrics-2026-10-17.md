# Bảng metrics đánh giá và so sánh model của hệ thống P-142

Ngày lập: **17/10/2026**. Phạm vi: chuẩn hóa tiếng Việt, agent hội thoại/triage/RAG, vision và embedding.

Tài liệu tổng hợp cấu hình, bằng chứng có sẵn trong repo và giá chính thức được tra cứu tại ngày lập. **Chưa có benchmark đối chứng cùng bộ dữ liệu để chứng minh model hiện tại tốt hơn các model khác.** Các ô “chưa đo” là khoảng trống cần bổ sung, không phải điểm 0. Không chạy thêm API trả phí để lập tài liệu này.

## 1. Model hệ thống đang cấu hình và model đã chạy thực tế

| Thành phần | Cấu hình hiện tại | Bằng chứng thực thi có sẵn | Nhận định |
| --- | --- | --- | --- |
| Agent hội thoại, phân loại sự cố, RAG, bộ nhớ, diễn đạt lại | `MODEL_NAME=gpt-4o-mini` trong `.env` | Golden v2 live xác nhận `gpt-4o-mini-2024-07-18` tại 6 công đoạn; 14 lời gọi thành công và parse được | Có bằng chứng tích hợp; vẫn còn lỗi nội dung/định tuyến ở hệ thống |
| Chuẩn hóa tiếng Việt và từ viết tắt | Mặc định `gemini-2.5-flash-lite` trong `src/config.py` | Chẩn đoán cấu hình gốc ghi `GoogleModelNotFoundError`; lượt live chính thức dùng override `gemini-3.5-flash-lite`, 5 lời gọi được xác nhận | Không dùng kết quả của 3.5 để chứng minh cấu hình 2.5 đang hoạt động |
| Phân luồng ảnh, OCR táp-lô, ngoại thất | Mặc định `VISION_PROVIDER=openai`, `VISION_MODEL=gpt-6-luna` | Golden v2 live xác nhận 16 lời gọi `gpt-6-luna`, bao phủ 3 công đoạn vision | Đã tích hợp; kết quả hiện có chỉ trên ảnh tổng hợp |
| Backend vision Google thay thế | `DASHBOARD_VISION_MODEL=gemini-3.5-flash`; không phải backend mặc định | Lượt thử Google nhận model thực `gemini-3.6-flash`; 5 ca BLOCKED vì lệch tên yêu cầu | Chưa có kết quả hợp lệ để so trực tiếp với OpenAI |
| Embedding truy hồi | `.env` trỏ `CHROMA_PERSIST_DIR=./data/chroma-catalog-colors-v1` | Code có adapter local `MultilingualE5`, model ONNX `multilingual-e5-small`; collection được tải lại từ cấu hình đã lưu | Chưa xác nhận embedding của collection đang dùng trong lần rà soát này; không suy từ file download hoặc tài liệu cũ |
| CarDD | Mặc định `cardd_enabled=False` | Không có bằng chứng bật trong phạm vi rà soát | Không đưa vào số đo của pipeline đang hoạt động |

Nguồn: [cấu hình](../src/config.py), [LLM factory](../src/services/llm.py), [embedding adapter](../src/services/multilingual_embeddings.py), [RAG service](../src/services/rag_service.py), [manifest live](../eval/results/golden-v2-20261017/live/manifest.json), [báo cáo Golden v2](../eval/results/golden-v2-20261017/report.md). Cấu hình ở đây là snapshot workspace, chưa phải kiểm kê môi trường production đang triển khai. Không sao chép khóa API vào báo cáo.

## 2. Bảng metrics dùng để chứng minh chất lượng

Các ngưỡng dưới đây là **đề xuất nghiệm thu**, cần chủ dự án duyệt; không phải SLA hoặc thành tích đã đạt. Báo cáo riêng theo tác vụ và nhóm khó, tránh để nhóm dễ che lỗi nghiêm trọng.

| Nhóm | Metric | Định nghĩa/cách đo | Chiều tốt | Ngưỡng đề xuất hoặc cách sử dụng |
| --- | --- | --- | --- | --- |
| Bằng chứng | Model attribution coverage | Lời gọi xác nhận đúng model thực / số lời gọi bắt buộc; lưu requested/actual model, phase, call ID | Cao | 100%; BLOCKED nếu thiếu hoặc lệch model chưa được duyệt |
| Bằng chứng | Usage coverage | Lời gọi có usage hợp lệ / toàn bộ lời gọi đã thực hiện | Cao | 100% trước khi kết luận tổng token/chi phí đầy đủ |
| Tổng thể | Task success rate | Số ca đạt toàn bộ tiêu chí / tổng ca dự kiến; báo riêng PASS/FAIL/BLOCKED | Cao | ≥95% trên test set độc lập; ca nhiều lượt chỉ đạt khi toàn bộ lượt đạt |
| Chuẩn hóa | Meaning preservation | Tỷ lệ câu giữ đúng ý, phủ định, mức nguy hiểm, tên xe và mã lỗi theo nhãn người duyệt | Cao | ≥99%; mọi thay đổi sai ý nguy hiểm phải được xử lý |
| Chuẩn hóa | Expansion precision/recall/F1 | Đối chiếu từ viết tắt được mở rộng với đáp án; `F1=2PR/(P+R)` | Cao | F1 ≥0,95; báo riêng viết tắt mơ hồ và tỷ lệ hỏi xác nhận |
| Triage | Macro-F1 | Tính F1 từng lớp ưu tiên rồi lấy trung bình không trọng số | Cao | ≥0,95; kèm confusion matrix và số mẫu mỗi lớp |
| An toàn | Critical recall | `TP/(TP+FN)` trên ca nguy hiểm thực sự cần xử lý khẩn cấp | Cao | Không bỏ sót ca trong bộ nghiệm thu; kèm khoảng tin cậy, không suy ra recall thực tế bằng 100% |
| An toàn | False alarm rate | `FP/(FP+TN)` trên ca không nguy hiểm, gồm phủ định/giả định/xe khác | Thấp | ≤5%; đánh giá song song critical recall |
| An toàn | HITL compliance | Ca chuyển nhân viên đúng policy / ca policy yêu cầu chuyển | Cao | 100% trên ca bắt buộc; đo thêm chuyển nhân viên không cần thiết |
| RAG retrieval | Recall@5, MRR | Tỷ lệ bằng chứng đúng xuất hiện trong top 5; trung bình nghịch đảo vị trí kết quả đúng đầu tiên | Cao | Recall@5 ≥0,90; MRR dùng so thứ hạng giữa candidate |
| RAG trả lời | Grounded claim rate | Mệnh đề kiểm chứng được được nguồn hỗ trợ / tổng mệnh đề kiểm chứng được | Cao | ≥98%; chấm nguồn đúng dòng xe, phiên bản và điều kiện áp dụng |
| RAG trả lời | Citation precision | Trích dẫn thật sự hỗ trợ phát biểu / toàn bộ trích dẫn | Cao | ≥98%; có link đúng nhưng nội dung không hỗ trợ vẫn tính sai |
| RAG thiếu dữ liệu | Correct abstention | Ca từ chối/hỏi thêm đúng / ca không đủ bằng chứng | Cao | ≥95%; đo thêm tỷ lệ từ chối nhầm trên câu có đáp án |
| Bộ nhớ | Fact retention / contradiction rate | Tỷ lệ dữ kiện cần thiết còn đúng sau nén / tỷ lệ phát biểu mâu thuẫn lịch sử | Cao / thấp | Giữ ≥98% dữ kiện; không mất tín hiệu nguy hiểm hoặc phát sinh PII bị cấm |
| Vision OCR | CER, WER | Khoảng cách chỉnh sửa ký tự/từ chia độ dài đáp án, báo riêng từng tập ảnh | Thấp | CER ≤5% trên ảnh rõ; ảnh mờ/tối báo thành nhóm riêng |
| Vision cảnh báo | Macro-F1 symptom | F1 theo từng nhãn triệu chứng, kể cả `low_pressure`, `sensor_fault`, lỗi phanh | Cao | ≥0,95 trên ảnh thật có nhãn; không coi OCR đúng là symptom đúng |
| Vision ngoại thất | Accuracy + coverage khi abstain | Độ chính xác trên ảnh model có kết luận; tỷ lệ ảnh model dám kết luận | Cao, xét đồng thời | Chọn ngưỡng confidence theo đường accuracy–coverage; không nâng accuracy bằng cách từ chối mọi ảnh |
| Vision âm tính | False identification rate | Ảnh không có xe nhưng bị khẳng định có dòng xe / tổng ảnh không có xe | Thấp | ≤1%; kèm khoảng tin cậy và số mẫu |
| Hợp đồng | Schema/parse success | Output hợp lệ và qua validator / số lời gọi đã hoàn tất | Cao | ≥99%; parse được không đồng nghĩa nội dung đúng |
| Độ bền | Provider error, timeout, fallback rate | Số request lỗi provider, timeout hoặc dùng fallback / tổng request; tách từng loại | Thấp | Tổng lỗi/timeout ≤1% ở tải mục tiêu; fallback không tự tính thành model PASS |
| Tốc độ | Latency P50/P95/P99 | Thời gian từ gửi đến trả kết quả; đo riêng generation, HTTP turn và toàn ca nhiều lượt | Thấp | P95 chuẩn hóa ≤3s; HTTP chat ≤20s; phân luồng ảnh ≤12s; táp-lô/ngoại thất ≤25s |
| Tốc độ streaming | TTFT, output tokens/s | Thời gian token đầu; token output chia thời gian sinh sau token đầu | Thấp / cao | Chỉ báo nếu pipeline thực sự stream; không suy từ latency toàn ca |
| Tải | Successful throughput | Request đạt chuẩn / giây ở concurrency 1, 5, 10; kèm P95 và error rate | Cao | Chọn mức tải theo nhu cầu; không so RPS khác concurrency/quota |
| Giá thành | USD/request, USD/1.000 request | Tổng phí mọi generation, retry và tool / request; chuẩn hóa theo cùng workload | Thấp | Báo mean/P95 và coverage; thiếu cost ghi N/A |
| Hiệu quả | Cost per successful task | Tổng phí của cả ca thành công lẫn thất bại / số ca thành công | Thấp | Dùng sau khi qua điều kiện an toàn và chất lượng |
| Vận hành | TCO, RAM/VRAM, cold start | API + compute + lưu trữ + giám sát + vận hành; đo peak memory và thời gian nạp model | Thấp | Bắt buộc khi so local với API; phí API bằng 0 không có nghĩa TCO bằng 0 |
| Riêng tư | PII/injection violation rate | Ca lộ dữ liệu bị cấm hoặc làm theo lệnh độc hại / tổng ca đối kháng có nhãn | Thấp | Không có vi phạm trong bộ nghiệm thu; kiểm tra cả output lẫn telemetry |

Các mức latency gợi ý dựa trên timeout đang cấu hình, chưa chứng minh hệ thống đáp ứng SLA. P99 cần đủ mẫu; không diễn giải percentile đuôi từ vài ca như số đo production.

## 3. Kết quả đo đã có trong repo

### 3.1. Golden v2 live — bằng chứng chính

Run: `golden-v2-live-36773c9061`. Dữ liệu: [results.json](../eval/results/golden-v2-20261017/live/results.json), [manifest](../eval/results/golden-v2-20261017/live/manifest.json), [report](../eval/results/golden-v2-20261017/live/report.md).

| Nhóm ca | Số ca | PASS / FAIL / BLOCKED | Tỷ lệ đạt | Mean (s) | P50 (s) | P95 (s) |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Probe trực tiếp prompt | 7 | 6 / 1 / 0 | 85,71% | 1,935 | 1,360 | 4,281 |
| Hội thoại nhiều lượt | 4 | 4 / 0 / 0 | 100% | 3,722 | 2,813 | 4,843 |
| Chuẩn hóa qua pipeline | 4 | 4 / 0 / 0 | 100% | 1,160 | 1,063 | 1,391 |
| RAG khó | 3 | 0 / 3 / 0 | 0% | 0,151 | 0,156 | 0,157 |
| Safety khó | 3 | 1 / 2 / 0 | 33,33% | 0,156 | 0,140 | 0,203 |
| Triage khó | 3 | 0 / 3 / 0 | 0% | 1,401 | 1,406 | 2,625 |
| Vision trên ảnh tổng hợp | 16 | 15 / 1 / 0 | 93,75% | 2,226 | 2,235 | 3,234 |
| **Toàn bộ** | **40** | **30 / 10 / 0** | **75%** | — | — | — |

Latency lấy từ `duration_s` của **toàn testcase**, không phải thời gian riêng của model hoặc HTTP production; ca nhiều lượt có nhiều turn. P50/P95 tính bằng nearest-rank: sắp xếp n mẫu, lấy phần tử thứ `ceil(p × n)`. Với n nhỏ, P95 thường chính là max. Lượt này có override chuẩn hóa sang 3.5; không đại diện nguyên trạng cấu hình gốc.

| Model thực được SDK ghi nhận | Số lời gọi | Tổng token provider trả | Thành công transport + parse | Chất lượng được chứng minh đến đâu? |
| --- | ---: | ---: | --- | --- |
| `gpt-4o-mini-2024-07-18` | 14 | 16.428 | 14/14 | Gọi đủ 6 công đoạn; probe triage sai ưu tiên. Không dùng 14/14 làm accuracy |
| `gemini-3.5-flash-lite` | 5 | 1.126 | 5/5 | 1 probe + 4 ca chuẩn hóa đạt; mẫu nhỏ, chưa có đối chứng |
| `gpt-6-luna` | 16 | 23.690 | 16/16 | 15/16 ca vision đạt; lỗi ánh xạ `Brake system fault` thành symptom |
| **Tổng** | **35** | **41.244** | **35/35** | Thành công kỹ thuật và thành công tác vụ là hai metric khác nhau |

Không quy toàn bộ lỗi hệ thống cho LLM: hard rule, router, retrieval, ontology và prompt đều có thể tạo lỗi. Các ca RAG sai nhanh chủ yếu phản ánh định tuyến, không chứng minh model sinh câu trả lời nhanh hoặc kém. Ca khẩn cấp có thể được thiết kế không gọi LLM.

Cloud chỉ có 24 generation/34.644 token so với ledger SDK 35 lời gọi/41.244 token. Chi phí Cloud đã biết **0,00513795 USD là phần quan sát được**, chưa phải tổng phí lượt chạy; không chia cho 40 để công bố giá thực đầy đủ mỗi ca.

### 3.2. Kết quả khác và giới hạn

| Nguồn | Quan sát | Cách sử dụng đúng |
| --- | --- | --- |
| [Chẩn đoán cấu hình gốc](../eval/results/golden-v2-20261017/configured-model-diagnostics/report.md) | 2/2 probe BLOCKED; chưa xác nhận generation tương ứng | Bằng chứng cấu hình có vấn đề tại lượt đó; không tính accuracy=0% của năng lực model |
| [Vision Google thay thế](../eval/results/golden-v2-20261017/google-vision-alternative/report.md) | 5/5 BLOCKED do lệch model attribution | Chưa thể xếp hạng chất lượng/tốc độ của model được yêu cầu |
| [Demo 3 model](../tmp/eval-3models-20261017-102911.json) | Chuẩn hóa 0,78–1,20s; vision 1,72–3,45s; chat 0,25–6,11s | Chỉ tham khảo luồng demo: model target gắn sẵn, HTTP 200 chưa chứng minh gọi đúng model |
| [Tổng hợp chi phí demo](../tmp/eval_costs_summary.json) | Có usage/cost bằng 0 và dòng có input + output khác total chưa được giải thích | Chưa dùng làm tổng phí chuẩn; cần đối soát generation, cached/reasoning usage và loại bỏ tính trùng |
| [Golden v2 tổng hợp](../eval/results/golden-v2-20261017/report.md) | Nhãn còn `draft_policy_review`, RAG dùng fixture, ảnh tổng hợp | Chưa là benchmark độc lập; chưa chứng minh retrieval production, ảnh xe thật hoặc mọi cách diễn đạt tiếng Việt |

## 4. Bảng so sánh model hiện tại với các lựa chọn khác

“Ưu điểm” của model chưa benchmark là lợi thế về giá, kiến trúc hoặc khả năng được nhà cung cấp mô tả; không phải chiến thắng thực nghiệm trên P-142. Các ứng viên sau được chọn theo cùng tác vụ, không nhằm liệt kê toàn bộ thị trường.

| Model / phương án | Vai trò so sánh | Ưu điểm có căn cứ | Nhược điểm / điểm cần kiểm chứng | Tốc độ tại P-142 | Trạng thái đánh giá |
| --- | --- | --- | --- | --- | --- |
| `gpt-4o-mini` | Baseline agent hiện tại | Đã tích hợp và có ledger thật; đơn giá nhỏ [O1] | Còn lỗi tác vụ; trang chính thức gắn Deprecated [O1]; không suy ra ngày ngừng từ nhãn này | Chưa tách latency generation; xem bảng toàn ca ở mục 3 | Có baseline, chưa có A/B |
| `gpt-6-luna` | Baseline vision; ứng viên agent/chuẩn hóa | Vision có 15/16 ca tổng hợp đạt; giá text Standard thấp hơn baseline chat trong ví dụ mục 5; nhận ảnh [O2] | Chưa thử agent đối chứng; còn lỗi symptom; đổi sang chat phải kiểm tra hợp đồng API/function calling [O2] | Vision toàn ca mean 2,226s trên 16 mẫu | Đã đo vision; chat/chuẩn hóa chưa đo |
| `gemini-2.5-flash-lite` | Baseline cấu hình chuẩn hóa | Giá niêm yết thấp [G1] | Từng lỗi không tìm thấy model trong đường gọi đang dùng; giá công khai không chứng minh tài khoản/gateway truy cập được | Chưa có số đo hợp lệ từ lượt Golden v2 cấu hình gốc | Cần giải quyết availability trước A/B |
| `gemini-3.5-flash-lite` | Chuẩn hóa thay thế; ứng viên agent/vision | Lượt override xác nhận 5/5 lời gọi; nhà cung cấp hướng đến tác vụ khối lượng lớn [G1] | Giá cao hơn 2.5 Flash-Lite; 5 ca chưa đủ chứng minh ưu thế tiếng Việt | 4 ca pipeline mean 1,160s; probe riêng 4,281s | Có thử nghiệm nhỏ; chưa A/B |
| `gpt-4.1-mini` | Đối chứng lịch sử cho agent/vision | Hỗ trợ tác vụ instruction/tool calling [O3] | Đơn giá cao hơn 4o-mini; trang chính thức gắn Deprecated [O3], chỉ nên dùng đối chiếu nếu còn truy cập được | Chưa đo | Không ưu tiên làm đích triển khai mới |
| `gpt-6.1-sol` | Đối chứng agent/vision ở mức ngân sách cao hơn | Có model API chính thức và bảng giá để lập đối chứng [O4, O5] | Chi phí ví dụ cao hơn nhiều; chưa có bằng chứng giảm lỗi P-142 tương ứng | Chưa đo | Đo trên cùng ca khó trước quyết định |
| Hard rule / từ điển viết tắt | Ablation chuẩn hóa và xử lý khẩn cấp | Không cần generation cho luật xác định; không có phí token cho nhánh đó | Hạn chế với ngữ cảnh, phủ định, viết tắt mơ hồ; vẫn có chi phí phần mềm/compute | Chưa đo riêng; ca safety toàn hệ thống không thay thế phép đo này | Giữ làm đối chứng để đo giá trị bổ sung của LLM |

### Embedding: so sánh riêng với truy hồi, không dùng metric sinh câu trả lời

| Phương án | Ưu điểm | Nhược điểm / chi phí | Metrics quyết định |
| --- | --- | --- | --- |
| Embedding của collection hiện tại | Baseline phản ánh index đang sử dụng | Cần đọc cấu hình collection và ghi version trước khi benchmark | Recall@5, MRR, retrieval P95, index size |
| `multilingual-e5-small` local ONNX | Đã có adapter trong repo; không trả phí API cho embedding local | Compute/RAM, giới hạn adapter 256 token; cần passage/query prefix đúng và re-index | Recall@5/MRR trên câu hỏi tiếng Việt, cold start, RAM, USD/1.000 query gồm compute |
| `text-embedding-3-small` API | Đơn giá công khai 0,02 USD/1M token input [O6] | Phụ thuộc mạng/provider, phát sinh phí query và re-index; chưa benchmark tại đây | Cùng corpus/chunk/top-k; thêm chi phí tạo index và latency mạng |

Không trộn vector của các embedding khác nhau trong một index. Để so chất lượng encoder, cố định corpus/chunk; nếu tối ưu chunk riêng cho từng model, báo thành thí nghiệm pipeline riêng.

## 5. Giá niêm yết và phép tính chi phí có thể kiểm tra lại

Đơn vị: **USD / 1 triệu token**, Standard trả phí; input không cache, không Batch/Flex/Fast, không tool, không thuế/phí gateway. GPT-6 dùng short-context, không áp dụng phụ phí vùng. Giá ở đây là tham chiếu hãng, chưa phải hợp đồng của gateway dự án.

| Model | Input | Output | USD / 1.000 lời gọi mẫu | Nguồn |
| --- | ---: | ---: | ---: | --- |
| `gemini-2.5-flash-lite` | 0,10 | 0,40 | 0,18 | [G1] |
| `gpt-6-luna` | 0,10 | 0,50 | 0,20 | [O2, O5] |
| `gpt-4o-mini` | 0,15 | 0,60 | 0,27 | [O1] |
| `gpt-4.1-mini` | 0,40 | 1,60 | 0,72 | [O3] |
| `gemini-3.5-flash-lite` | 0,30 | 2,50 | 0,80 | [G1] |
| `gpt-6.1-sol` | 2,00 | 10,00 | 4,00 | [O5] |

Mỗi lời gọi mẫu giả định **1.000 token input + 200 token output tính phí**, không có token tính phí bổ sung. Đây là phép tính cùng lượng token, không phải ước lượng lượng token thực sẽ giống nhau giữa các tokenizer/model. Output tính phí phải tính cả thinking/reasoning theo quy định model. Với ảnh, số token phụ thuộc model, độ phân giải và cách xử lý; không lấy bảng mẫu text này làm giá mỗi ảnh.

```text
Phí generation = (token_input_không_cache × giá_input
                + token_input_cache × giá_cache
                + token_output_tính_phí × giá_output) / 1.000.000
                + phí_tool + phí_cache_write/storage_nếu_có

Phí request = tổng phí các generation, retry, fallback và tool của request
Phí / ca thành công = tổng phí toàn lượt benchmark / số ca thành công
TCO = phí API + compute + storage + observability + công vận hành
```

Nếu usage không tách cached token thì không tự áp giá cache. Không cộng cost span cha đã tổng hợp với cost generation con. Miễn phí trong một tier không được dùng làm giá nền cho dự báo production. Chỉ đổi sang VND khi ghi rõ tỷ giá, ngày và nguồn; tài liệu này giữ USD.

## 6. Thiết kế phép so sánh để kết luận có căn cứ

1. **Khóa baseline và dữ liệu:** lưu model yêu cầu/thực tế, provider/gateway, prompt hash, dataset hash, corpus/index version, temperature, token limit, reasoning setting, timeout và quota. Chốt nhãn với người phụ trách nghiệp vụ trước khi xem kết quả ứng viên.
2. **Thay từng thành phần:** chuẩn hóa giữ nguyên agent/vision; agent giữ normalization và retrieval; vision giữ ảnh/độ phân giải; embedding giữ corpus/chunk/top-k. Với RAG, đo riêng retrieval thật và generator nhận cùng evidence. Không thay đồng thời model, prompt và corpus rồi quy mọi cải thiện cho model.
3. **Tách hai kiểu benchmark:** (a) prompt/contract cố định để so model; (b) pipeline tối ưu riêng cho model để chọn cấu hình triển khai. Báo riêng chi phí công sức và thay đổi ở (b).
4. **Dữ liệu đối chứng:** tái dùng 60 ca v1 + 120 ca v2 cho regression, bổ sung tập holdout chưa dùng sửa prompt. Điểm bắt đầu đề xuất: ≥100 mẫu độc lập mỗi tác vụ, thêm ≥300 mẫu âm tính nếu cần kiểm tra tỷ lệ bịa thấp; có ảnh xe thật, ảnh tối/mờ, phủ định, mã lỗi, nhiều lượt, thiếu nguồn và injection. Chạy lặp ≥3 lần để đo biến thiên; không coi các lần lặp là ca độc lập.
5. **Chạy công bằng:** xen kẽ/ngẫu nhiên thứ tự model để giảm lệch theo thời điểm; cùng máy, vùng mạng, tải và ngân sách output hợp lý. Báo cold/warm/cache riêng. Lưu đủ lỗi/timeout, không loại mẫu lỗi để tăng tốc độ trung bình. Model không truy cập được ghi BLOCKED.
6. **Chấm mù:** người chấm không thấy tên model; dùng rubric thống nhất. LLM judge chỉ là phụ trợ, cần kiểm tra thiên lệch và người duyệt ca safety/RAG. Báo kết quả theo tác vụ và confusion matrix, không chỉ một điểm tổng.
7. **Phân tích độ chắc chắn:** báo khoảng tin cậy 95% cho tỷ lệ và chênh lệch trên cặp testcase; bootstrap theo testcase/session cho ca nhiều lượt. Không coi 100% trên 4–5 mẫu là bằng chứng tổng quát. Ví dụ, 0 lỗi trên 300 mẫu âm tính độc lập chỉ cho cận trên một phía xấp xỉ 1% theo quy tắc 3/n.
8. **Ra quyết định:** loại ứng viên vi phạm điều kiện an toàn hoặc thiếu attribution. Trong nhóm đạt chất lượng, chọn theo cost per successful task, P95, độ ổn định và TCO. Có thể giữ nhiều model theo tác vụ nếu đo được lợi ích.

Runner hiện tại có [Golden v2](../scripts/run_golden_v2_eval.py) và [live model eval](../scripts/run_live_model_eval.py), nhưng **chưa phải harness A/B đầy đủ**. Golden v2 hỗ trợ override chuẩn hóa và backend vision; cần cấu hình/runner bổ sung để đối chiếu tùy ý model agent/vision. Tài liệu này không thay cấu hình hoặc bổ sung runner.

### Mẫu bảng kết quả để điền sau benchmark đối chứng

| Tác vụ | Model thực / version | N độc lập × lần lặp | Success % + CI95% | Safety FN / FP | P50 / P95 (s) | USD/1.000 request | USD/ca đạt | Error % | Attribution / usage coverage | Kết luận |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Agent | `gpt-4o-mini-2024-07-18` baseline | Chưa đo đối chứng | Chưa đo | Chưa đo | Chưa đo riêng | Chưa đủ cost | Chưa đủ cost | Chưa đo tải | Chưa đo trên tập đối chứng | Chờ benchmark |
| Agent | `gpt-6-luna` | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chờ benchmark |
| Agent | `gpt-6.1-sol` | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chờ benchmark |
| Chuẩn hóa | `gemini-2.5-flash-lite` baseline cấu hình | Chưa có lượt đối chứng hợp lệ | BLOCKED ở lượt chẩn đoán | — | — | — | — | — | Thiếu generation | Xác nhận availability |
| Chuẩn hóa | `gemini-3.5-flash-lite` | Chưa đo đối chứng | Có pilot mục 3; chưa có CI đối chứng | Chưa đo | Có pilot mục 3 | Chưa đủ cost | Chưa đủ cost | Chưa đo tải | Có ledger pilot | Chờ benchmark |
| Vision | `gpt-6-luna` baseline | Chưa đo đối chứng ảnh thật | Có 15/16 ảnh tổng hợp | Chưa đo ảnh thật | Có pilot mục 3 | Chưa đủ cost | Chưa đủ cost | Chưa đo tải | Có ledger pilot | Chờ ảnh thật + đối chứng |
| Vision | `gemini-3.5-flash-lite` hoặc `gpt-6.1-sol` | Chưa đo từng model | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chạy riêng từng ứng viên |

## 7. Kết luận có thể dùng trong báo cáo

| Nhận định | Mức bằng chứng hiện tại |
| --- | --- |
| Hệ thống có phân công model theo tác vụ | Có căn cứ từ code, manifest và ledger |
| Agent và vision đã gọi model thật | Có, trong phạm vi lượt Golden v2 và các công đoạn được ghi nhận |
| Chuẩn hóa cấu hình gốc đang chạy ổn | Chưa chứng minh; lượt có kết quả dùng override rõ ràng |
| Vision đạt 93,75% | Đúng trên 16 ca ảnh tổng hợp đã chọn; chưa đại diện ảnh xe thực |
| Hệ thống đạt chất lượng nghiệm thu | Chưa; lượt live có 10/40 ca FAIL và nhãn chưa duyệt độc lập |
| Model hiện tại nhanh/rẻ/tốt hơn mọi ứng viên | Chưa có benchmark cùng điều kiện; mới có so đơn giá và dữ liệu baseline |
| Có thể bảo vệ lựa chọn model bằng metrics | Có khung đo và bằng chứng nền; cần hoàn thành các phép đối chứng ở mục 6 để bảo vệ kết luận lựa chọn |

## 8. Nguồn chính thức cho thông số và giá

Tra cứu ngày 17/10/2026. Cần kiểm tra lại giá, khả năng truy cập và vòng đời model trước mỗi đợt benchmark hoặc quyết định triển khai.

- **[O1]** [OpenAI — GPT-4o mini](https://developers.openai.com/api/docs/models/gpt-4o-mini): giá, modality, trạng thái Deprecated.
- **[O2]** [OpenAI — GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna): giá, nhận ảnh, reasoning và ràng buộc function calling theo API.
- **[O3]** [OpenAI — GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini): giá, instruction/tool calling và trạng thái Deprecated.
- **[O4]** [OpenAI — GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol): model đối chứng.
- **[O5]** [OpenAI — API pricing](https://developers.openai.com/api/docs/pricing): Standard và các tier giá GPT-6.
- **[O6]** [OpenAI — text-embedding-3-small](https://developers.openai.com/api/docs/models/text-embedding-3-small): đơn giá embedding.
- **[G1]** [Google — Gemini Developer API pricing](https://ai.google.dev/gemini-api/docs/pricing): Standard paid tier của 2.5 Flash-Lite và 3.5 Flash-Lite.
