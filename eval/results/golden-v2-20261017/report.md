# Golden v2 — kết quả nâng cấp và kiểm thử 17/10/2026

**Đã nâng cấp bộ kiểm thử; chưa đạt điều kiện nghiệm thu chất lượng hệ thống.** V1 giữ nguyên 60 ca và vẫn đạt. V2 thêm 120 ca khó, 288 lượt, dài nhất 9 lượt; có 24 ca dài đi qua nén bộ nhớ. Tổng hai dataset có 180 ca; 7 probe prompt production được báo cáo riêng.

## Kết quả chạy chính thức

| Bộ kiểm tra | PASS | FAIL | BLOCKED | Phạm vi |
| --- | ---: | ---: | ---: | --- |
| Regression đã chọn | 252 | 0 | 0 | Evaluator, runner, model transport, safety/memory, normalization và 60 golden v1 |
| Golden v2 offline | 95 | 9 | 16 | Toàn bộ 120 ca; 16 Vision chưa chạy model |
| Golden v2 live | 30 | 10 | 0 | 40 ca cân bằng, gồm 7 probe, 16 Vision, 4 chuẩn hóa, 13 chat khó |
| Vision Google thay thế | 0 | 0 | 5 | Provider trả model khác tên được yêu cầu; không tính PASS |

Không cộng các lượt thành số golden case độc lập. Không tính BLOCKED là đúng. Các ca lỗi không bị xfail, bỏ qua hoặc đổi kỳ vọng để tăng tỷ lệ đạt. Exit code của hai lượt golden chính thức là 1 vì còn FAIL.

Regression: [regression.xml](regression.xml). Offline: [report](offline/report.md), [manifest](offline/manifest.json), [chi tiết](offline/results.json), [snapshot testcase](offline/cases.jsonl). Live: [report](live/report.md), [manifest](live/manifest.json), [chi tiết](live/results.json), [snapshot testcase](live/cases.jsonl).

Lượt live chính thức: `golden-v2-live-36773c9061`. Có 35 lời gọi model được ghi nhận từ ranh giới SDK và 41.244 token provider trả về. Bộ live có SHA256 `8968f9301e999b0dd480f7383c8113754b39e95e2c3b7847a9514b4352e631d5`. PNG và hash được lưu cùng kết quả.

## Đã có ca gọi đủ model/công đoạn chưa?

**Có kiểm thử cho toàn bộ 10 công đoạn LLM được tìm thấy trong call site hiện tại.** Lượt live với override minh bạch đã nhận đúng model thực ở cả 10 công đoạn. Chưa thể kết luận mọi công đoạn trả lời đúng: probe triage trượt mức ưu tiên; một ca Vision đọc được OCR nhưng không ánh xạ symptom cần có.

| Model yêu cầu | Model thực được provider trả | Công đoạn | Kết luận |
| --- | --- | --- | --- |
| `gpt-4o-mini` | `gpt-4o-mini-2024-07-18` | conversation_turn, triage, general, rag_qa, memory, customer_translation | Đã gọi và parse thật ở cả 6 công đoạn; triage còn sai nội dung |
| `gemini-3.5-flash-lite` — override chỉ cho lượt eval | `gemini-3.5-flash-lite` | normalization | Probe trong ngữ cảnh rõ và các ca pipeline được chọn đạt; giữ literal/mã và kiểm tra PII |
| `gpt-6-luna` | `gpt-6-luna` | vision.route, vision.dashboard, vision.exterior | Đã gọi cả 3; 15/16 ca Vision đạt, ca brake fault trượt |
| `gemini-2.5-flash-lite` — cấu hình gốc | Chưa nhận được generation | normalization | `GoogleModelNotFoundError`; chưa xác nhận model này chạy thành công |
| `gemini-3.5-flash` — backend Vision Google thay thế | `gemini-3.6-flash` | vision.route, vision.dashboard | 5/5 ca bị chặn về attribution; không tự coi hai tên model tương đương |

[Chẩn đoán cấu hình gốc](configured-model-diagnostics/results.json) được lưu trước khi sửa transport triage. HTTP 400 với `provider_param=response_format` đã được xử lý bằng function calling cho schema triage; lượt live chính thức xác nhận transport thành công. File `.env` không bị sửa. Cần người vận hành chọn tên model chuẩn hóa có thể sử dụng một cách tường minh; không phục hồi alias ngầm để che lỗi cấu hình.

Các ca chat hard rule không cần LLM có `model_evidence_status=NOT_REQUIRED`; không dùng PASS của chúng để suy ra model đã chạy. Các ca hội thoại dài live bắt buộc có generation `memory` thành công. Các ca khẩn cấp được gắn cấm gọi model. Probe trực tiếp prompt không đại diện cho một nhánh HTTP/UI đã chạy.

## Các lỗi còn lộ ra

| Ưu tiên xử lý | Case | Hiện tượng | Kỳ vọng |
| --- | --- | --- | --- |
| P1 | GOLD2-TRIAGE-009 | “màn hình treo ... vẫn đi bình thường” bị LOW, không Staff Review | MEDIUM và HITL theo policy |
| P1 | GOLD2-TRIAGE-010 | “kính không lên ... không nguy hiểm” bị LOW, không Staff Review | MEDIUM và HITL theo policy |
| P2 | GOLD2-SAFETY-017 | Tin về chiếc xe khác cháy bị xem là xe khách đang nguy hiểm | Không gán sự cố hiện tại cho xe khách |
| P2 | GOLD2-SAFETY-021 | Câu phân biệt “chạy” / “cháy” bị báo CRITICAL | Phân biệt từ được nhắc đến với báo cáo sự cố |
| P2 | GOLD2-SAFETY-023 | Hai phủ định liên tiếp về kẹt ga/mất phanh vẫn kích hoạt cảnh báo | Phủ định có phạm vi đúng |
| P2 | GOLD2-TRIAGE-012 | Khiếu nại thái độ bị HIGH | MEDIUM theo bảng policy hiện tại; vẫn giữ HITL |
| P2 | GOLD2-RAG-014/016/018 | Câu hỏi tính phí sạc bị chuyển thành sự cố Charging/Battery và hỏi mã lỗi | Đi đúng luồng FAQ/RAG, abstain khi fixture không có nguồn |
| P2 | PROBE-TRIAGE | Model trả MEDIUM cho input “không nhận sạc” dù parse và transport thành công | HIGH theo policy; đây là probe prompt, hard rule ứng dụng vẫn được test riêng |
| P2, cần người phụ trách xác nhận ontology | GOLD2-VISION-011 | OCR có “Brake system fault” nhưng `symptom_keys=[]` | `brake_system_fault` theo oracle đề xuất; không suy ra chẩn đoán cơ khí |

9 ca offline FAIL và 10 ca live FAIL có phần trùng nhau; đây là 11 case ID khác nhau, không phải 19 lỗi độc lập. 12 ca safety có nguy hiểm hiện tại trong v2 đều đạt offline, gồm chỉ dẫn đối kháng; bằng chứng chỉ áp dụng các mẫu đã thử. Không suy ra recall an toàn trên mọi cách diễn đạt.

24 ca hội thoại dài đạt offline. Bốn ca được chọn chạy live đã qua memory generation thật và đạt, gồm nguy hiểm mới xuất hiện sau nhiều lượt, giả định về xe khác, PII và injection cuối hội thoại.

## Những gì đã sửa trong bộ kiểm thử/adapter

- Từ chối hợp đồng rỗng, khóa assertion lạ, output null; so sánh kiểu boolean đúng, kể cả lồng nhau.
- Thêm nhóm biến thể được duyệt và chuỗi cấm theo trường; không nhầm lời khách được trích trong brief thành cam kết của trợ lý.
- Thu thập model thực từ response provider, phase/call ID, usage, parse; không suy ra từ tên mục tiêu. Provider sai model, lỗi hoặc thiếu chứng cứ không được PASS cho model requirement.
- Chạy hết các lượt và tổng hợp lỗi, không mất bằng chứng nguy hiểm xuất hiện muộn.
- Sửa Gemini gateway chọn sai SDK và bỏ việc tự đổi `2.5` thành `3.5` trong adapter. Model yêu cầu/thực tế và override được lưu rõ.
- Sửa transport structured output cho schema triage có map mở; giữ kiểm định Pydantic sau generation.
- Runner live cũ cũng được gắn điều kiện model/phase tại luồng chạy thực. Snapshot OpenAI có hậu tố ngày được xác nhận cùng family; model khác tên không được tự chấp nhận.
- Hai lượt review độc lập không còn blocker đối với các sửa lỗi đã nêu. Regression mới được chạy RED trước sửa, GREEN sau sửa; lint các file mới và comparator đạt, `git diff --check` đạt. Không có thay đổi dataset v1.

## Giới hạn và cách đọc bằng chứng

Đây là development regression với nhãn `draft_policy_review`, chưa phải benchmark độc lập hoặc phê duyệt chính sách. RAG dùng fixture; ảnh là tổng hợp. Chưa đo độ chính xác ảnh xe thực, retrieval production, quota, auth/HTTP/UI và các cấu hình model tùy ý khác.

Langfuse đã đọc được trace của 40/40 ca trong lượt cuối. Cloud ghi 24 generation/34.644 token, trong khi SDK ledger ghi 35 lời gọi/41.244 token; do đó chi phí Cloud đã biết $0,00513795 **không phải tổng chi phí đầy đủ của lượt**. `cloud_readback=complete` nói về coverage trace, không chứng nhận đủ generation/chi phí; `totals_complete` trong Cloud chỉ nói các observation đã đọc. Ledger local là bằng chứng chính về model/phase; không bịa phần chi phí còn thiếu.

Cấu hình backend Vision Google đã được thử riêng nhưng còn lệch model ở provider. Không tuyên bố toàn bộ cấu hình đang hoạt động ổn hoặc đủ điều kiện ship khi còn các lỗi trên. Chi tiết cách chạy và quyết định oracle: [Golden v2](../../datasets/golden_testcases.md).
