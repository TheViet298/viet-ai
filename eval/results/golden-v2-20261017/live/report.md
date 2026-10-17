# Golden v2 — live

Run `golden-v2-live-36773c9061`. Verdicts: `{'PASS': 30, 'FAIL': 10}`.

| Công đoạn | Model yêu cầu | Model provider xác nhận | Ca gọi đúng | Ca đạt |
| --- | --- | --- | ---: | ---: |
| normalization | gemini-3.5-flash-lite | gemini-3.5-flash-lite | 5 | 5 |
| conversation_turn | gpt-4o-mini | gpt-4o-mini-2024-07-18 | 1 | 1 |
| triage | gpt-4o-mini | gpt-4o-mini-2024-07-18 | 1 | 0 |
| general | gpt-4o-mini | gpt-4o-mini-2024-07-18 | 3 | 1 |
| rag_qa | gpt-4o-mini | gpt-4o-mini-2024-07-18 | 1 | 1 |
| memory | gpt-4o-mini | gpt-4o-mini-2024-07-18 | 5 | 5 |
| customer_translation | gpt-4o-mini | gpt-4o-mini-2024-07-18 | 1 | 1 |
| vision.route | gpt-6-luna | gpt-6-luna | 4 | 4 |
| vision.dashboard | gpt-6-luna | gpt-6-luna | 8 | 7 |
| vision.exterior | gpt-6-luna | gpt-6-luna | 4 | 4 |

| Case | Kết quả | Lỗi hợp đồng | Lỗi bằng chứng |
| --- | --- | ---: | --- |
| PROBE-NORMALIZATION | PASS | 0 |  |
| PROBE-CONVERSATION_TURN | PASS | 0 |  |
| PROBE-TRIAGE | FAIL | 1 |  |
| PROBE-GENERAL | PASS | 0 |  |
| PROBE-RAG_QA | PASS | 0 |  |
| PROBE-MEMORY | PASS | 0 |  |
| PROBE-CUSTOMER_TRANSLATION | PASS | 0 |  |
| GOLD2-SAFETY-001 | PASS | 0 |  |
| GOLD2-SAFETY-017 | FAIL | 1 |  |
| GOLD2-SAFETY-023 | FAIL | 1 |  |
| GOLD2-TRIAGE-009 | FAIL | 2 |  |
| GOLD2-TRIAGE-010 | FAIL | 2 |  |
| GOLD2-TRIAGE-012 | FAIL | 1 |  |
| GOLD2-RAG-014 | FAIL | 1 |  |
| GOLD2-RAG-016 | FAIL | 1 |  |
| GOLD2-RAG-018 | FAIL | 1 |  |
| GOLD2-MULTITURN-005 | PASS | 0 |  |
| GOLD2-MULTITURN-009 | PASS | 0 |  |
| GOLD2-MULTITURN-013 | PASS | 0 |  |
| GOLD2-MULTITURN-021 | PASS | 0 |  |
| GOLD2-NORMALIZATION-007 | PASS | 0 |  |
| GOLD2-NORMALIZATION-008 | PASS | 0 |  |
| GOLD2-NORMALIZATION-013 | PASS | 0 |  |
| GOLD2-NORMALIZATION-014 | PASS | 0 |  |
| GOLD2-VISION-001 | PASS | 0 |  |
| GOLD2-VISION-002 | PASS | 0 |  |
| GOLD2-VISION-003 | PASS | 0 |  |
| GOLD2-VISION-004 | PASS | 0 |  |
| GOLD2-VISION-005 | PASS | 0 |  |
| GOLD2-VISION-006 | PASS | 0 |  |
| GOLD2-VISION-007 | PASS | 0 |  |
| GOLD2-VISION-008 | PASS | 0 |  |
| GOLD2-VISION-009 | PASS | 0 |  |
| GOLD2-VISION-010 | PASS | 0 |  |
| GOLD2-VISION-011 | FAIL | 1 |  |
| GOLD2-VISION-012 | PASS | 0 |  |
| GOLD2-VISION-013 | PASS | 0 |  |
| GOLD2-VISION-014 | PASS | 0 |  |
| GOLD2-VISION-015 | PASS | 0 |  |
| GOLD2-VISION-016 | PASS | 0 |  |

Nhãn đề xuất chưa duyệt độc lập. RAG dùng fixture; ảnh tổng hợp không đo độ chính xác ảnh xe thật.
BLOCKED là thiếu provider/bằng chứng; không tính là đúng nội dung. Token là provider trả về; chưa đối chiếu hóa đơn.
Probe gọi prompt production trực tiếp; không chứng minh nhánh HTTP/UI tương ứng đã chạy. Xem kind và model_calls trong results.json.
Kết quả từng ca được lưu trước khi flush Cloud. Không tự động chạy provider thay thế.
