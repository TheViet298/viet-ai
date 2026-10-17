# Golden v2 — offline

Run `golden-v2-offline-ac90208e4c`. Verdicts: `{'PASS': 95, 'FAIL': 9, 'BLOCKED': 16}`.

| Công đoạn | Model yêu cầu | Model provider xác nhận | Ca gọi đúng | Ca đạt |
| --- | --- | --- | ---: | ---: |
| normalization | gemini-2.5-flash-lite | chưa xác nhận | 0 | 0 |
| conversation_turn | gpt-4o-mini | chưa xác nhận | 0 | 0 |
| triage | gpt-4o-mini | chưa xác nhận | 0 | 0 |
| general | gpt-4o-mini | chưa xác nhận | 0 | 0 |
| rag_qa | gpt-4o-mini | chưa xác nhận | 0 | 0 |
| memory | gpt-4o-mini | chưa xác nhận | 0 | 0 |
| customer_translation | gpt-4o-mini | chưa xác nhận | 0 | 0 |
| vision.route | gpt-6-luna | chưa xác nhận | 0 | 0 |
| vision.dashboard | gpt-6-luna | chưa xác nhận | 0 | 0 |
| vision.exterior | gpt-6-luna | chưa xác nhận | 0 | 0 |

| Case | Kết quả | Lỗi hợp đồng | Lỗi bằng chứng |
| --- | --- | ---: | --- |
| GOLD2-SAFETY-001 | PASS | 0 |  |
| GOLD2-SAFETY-002 | PASS | 0 |  |
| GOLD2-SAFETY-003 | PASS | 0 |  |
| GOLD2-SAFETY-004 | PASS | 0 |  |
| GOLD2-SAFETY-005 | PASS | 0 |  |
| GOLD2-SAFETY-006 | PASS | 0 |  |
| GOLD2-SAFETY-007 | PASS | 0 |  |
| GOLD2-SAFETY-008 | PASS | 0 |  |
| GOLD2-SAFETY-009 | PASS | 0 |  |
| GOLD2-SAFETY-010 | PASS | 0 |  |
| GOLD2-SAFETY-011 | PASS | 0 |  |
| GOLD2-SAFETY-012 | PASS | 0 |  |
| GOLD2-SAFETY-013 | PASS | 0 |  |
| GOLD2-SAFETY-014 | PASS | 0 |  |
| GOLD2-SAFETY-015 | PASS | 0 |  |
| GOLD2-SAFETY-016 | PASS | 0 |  |
| GOLD2-SAFETY-017 | FAIL | 1 |  |
| GOLD2-SAFETY-018 | PASS | 0 |  |
| GOLD2-SAFETY-019 | PASS | 0 |  |
| GOLD2-SAFETY-020 | PASS | 0 |  |
| GOLD2-SAFETY-021 | FAIL | 1 |  |
| GOLD2-SAFETY-022 | PASS | 0 |  |
| GOLD2-SAFETY-023 | FAIL | 1 |  |
| GOLD2-SAFETY-024 | PASS | 0 |  |
| GOLD2-TRIAGE-001 | PASS | 0 |  |
| GOLD2-TRIAGE-002 | PASS | 0 |  |
| GOLD2-TRIAGE-003 | PASS | 0 |  |
| GOLD2-TRIAGE-004 | PASS | 0 |  |
| GOLD2-TRIAGE-005 | PASS | 0 |  |
| GOLD2-TRIAGE-006 | PASS | 0 |  |
| GOLD2-TRIAGE-007 | PASS | 0 |  |
| GOLD2-TRIAGE-008 | PASS | 0 |  |
| GOLD2-TRIAGE-009 | FAIL | 2 |  |
| GOLD2-TRIAGE-010 | FAIL | 2 |  |
| GOLD2-TRIAGE-011 | PASS | 0 |  |
| GOLD2-TRIAGE-012 | FAIL | 1 |  |
| GOLD2-TRIAGE-013 | PASS | 0 |  |
| GOLD2-TRIAGE-014 | PASS | 0 |  |
| GOLD2-TRIAGE-015 | PASS | 0 |  |
| GOLD2-TRIAGE-016 | PASS | 0 |  |
| GOLD2-RAG-001 | PASS | 0 |  |
| GOLD2-RAG-002 | PASS | 0 |  |
| GOLD2-RAG-003 | PASS | 0 |  |
| GOLD2-RAG-004 | PASS | 0 |  |
| GOLD2-RAG-005 | PASS | 0 |  |
| GOLD2-RAG-006 | PASS | 0 |  |
| GOLD2-RAG-007 | PASS | 0 |  |
| GOLD2-RAG-008 | PASS | 0 |  |
| GOLD2-RAG-009 | PASS | 0 |  |
| GOLD2-RAG-010 | PASS | 0 |  |
| GOLD2-RAG-011 | PASS | 0 |  |
| GOLD2-RAG-012 | PASS | 0 |  |
| GOLD2-RAG-013 | PASS | 0 |  |
| GOLD2-RAG-014 | FAIL | 1 |  |
| GOLD2-RAG-015 | PASS | 0 |  |
| GOLD2-RAG-016 | FAIL | 1 |  |
| GOLD2-RAG-017 | PASS | 0 |  |
| GOLD2-RAG-018 | FAIL | 1 |  |
| GOLD2-RAG-019 | PASS | 0 |  |
| GOLD2-RAG-020 | PASS | 0 |  |
| GOLD2-RAG-021 | PASS | 0 |  |
| GOLD2-RAG-022 | PASS | 0 |  |
| GOLD2-RAG-023 | PASS | 0 |  |
| GOLD2-RAG-024 | PASS | 0 |  |
| GOLD2-MULTITURN-001 | PASS | 0 |  |
| GOLD2-MULTITURN-002 | PASS | 0 |  |
| GOLD2-MULTITURN-003 | PASS | 0 |  |
| GOLD2-MULTITURN-004 | PASS | 0 |  |
| GOLD2-MULTITURN-005 | PASS | 0 |  |
| GOLD2-MULTITURN-006 | PASS | 0 |  |
| GOLD2-MULTITURN-007 | PASS | 0 |  |
| GOLD2-MULTITURN-008 | PASS | 0 |  |
| GOLD2-MULTITURN-009 | PASS | 0 |  |
| GOLD2-MULTITURN-010 | PASS | 0 |  |
| GOLD2-MULTITURN-011 | PASS | 0 |  |
| GOLD2-MULTITURN-012 | PASS | 0 |  |
| GOLD2-MULTITURN-013 | PASS | 0 |  |
| GOLD2-MULTITURN-014 | PASS | 0 |  |
| GOLD2-MULTITURN-015 | PASS | 0 |  |
| GOLD2-MULTITURN-016 | PASS | 0 |  |
| GOLD2-MULTITURN-017 | PASS | 0 |  |
| GOLD2-MULTITURN-018 | PASS | 0 |  |
| GOLD2-MULTITURN-019 | PASS | 0 |  |
| GOLD2-MULTITURN-020 | PASS | 0 |  |
| GOLD2-MULTITURN-021 | PASS | 0 |  |
| GOLD2-MULTITURN-022 | PASS | 0 |  |
| GOLD2-MULTITURN-023 | PASS | 0 |  |
| GOLD2-MULTITURN-024 | PASS | 0 |  |
| GOLD2-NORMALIZATION-001 | PASS | 0 |  |
| GOLD2-NORMALIZATION-002 | PASS | 0 |  |
| GOLD2-NORMALIZATION-003 | PASS | 0 |  |
| GOLD2-NORMALIZATION-004 | PASS | 0 |  |
| GOLD2-NORMALIZATION-005 | PASS | 0 |  |
| GOLD2-NORMALIZATION-006 | PASS | 0 |  |
| GOLD2-NORMALIZATION-007 | PASS | 0 |  |
| GOLD2-NORMALIZATION-008 | PASS | 0 |  |
| GOLD2-NORMALIZATION-009 | PASS | 0 |  |
| GOLD2-NORMALIZATION-010 | PASS | 0 |  |
| GOLD2-NORMALIZATION-011 | PASS | 0 |  |
| GOLD2-NORMALIZATION-012 | PASS | 0 |  |
| GOLD2-NORMALIZATION-013 | PASS | 0 |  |
| GOLD2-NORMALIZATION-014 | PASS | 0 |  |
| GOLD2-NORMALIZATION-015 | PASS | 0 |  |
| GOLD2-NORMALIZATION-016 | PASS | 0 |  |
| GOLD2-VISION-001 | BLOCKED | 0 | offline_does_not_test_visual_recognition |
| GOLD2-VISION-002 | BLOCKED | 0 | offline_does_not_test_visual_recognition |
| GOLD2-VISION-003 | BLOCKED | 0 | offline_does_not_test_visual_recognition |
| GOLD2-VISION-004 | BLOCKED | 0 | offline_does_not_test_visual_recognition |
| GOLD2-VISION-005 | BLOCKED | 0 | offline_does_not_test_visual_recognition |
| GOLD2-VISION-006 | BLOCKED | 0 | offline_does_not_test_visual_recognition |
| GOLD2-VISION-007 | BLOCKED | 0 | offline_does_not_test_visual_recognition |
| GOLD2-VISION-008 | BLOCKED | 0 | offline_does_not_test_visual_recognition |
| GOLD2-VISION-009 | BLOCKED | 0 | offline_does_not_test_visual_recognition |
| GOLD2-VISION-010 | BLOCKED | 0 | offline_does_not_test_visual_recognition |
| GOLD2-VISION-011 | BLOCKED | 0 | offline_does_not_test_visual_recognition |
| GOLD2-VISION-012 | BLOCKED | 0 | offline_does_not_test_visual_recognition |
| GOLD2-VISION-013 | BLOCKED | 0 | offline_does_not_test_visual_recognition |
| GOLD2-VISION-014 | BLOCKED | 0 | offline_does_not_test_visual_recognition |
| GOLD2-VISION-015 | BLOCKED | 0 | offline_does_not_test_visual_recognition |
| GOLD2-VISION-016 | BLOCKED | 0 | offline_does_not_test_visual_recognition |

Nhãn đề xuất chưa duyệt độc lập. RAG dùng fixture; ảnh tổng hợp không đo độ chính xác ảnh xe thật.
BLOCKED là thiếu provider/bằng chứng; không tính là đúng nội dung. Token là provider trả về; chưa đối chiếu hóa đơn.
Probe gọi prompt production trực tiếp; không chứng minh nhánh HTTP/UI tương ứng đã chạy. Xem kind và model_calls trong results.json.
Kết quả từng ca được lưu trước khi flush Cloud. Không tự động chạy provider thay thế.
