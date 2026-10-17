# Golden v2 — offline

Run `golden-v2-offline-79bd0f794e`. Verdicts: `{'PASS': 7, 'FAIL': 3}`.

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
| LANG-GREET-001 | PASS | 0 |  |
| LANG-EN-001 | PASS | 0 |  |
| LANG-EN-002 | PASS | 0 |  |
| LANG-EN-003 | FAIL | 1 |  |
| LANG-EN-004 | PASS | 0 |  |
| LANG-EN-005 | PASS | 0 |  |
| LANG-EN-006 | FAIL | 1 |  |
| LANG-EN-007 | FAIL | 1 |  |
| LANG-EN-008 | PASS | 0 |  |
| LANG-EN-009 | PASS | 0 |  |

Nhãn đề xuất chưa duyệt độc lập. RAG dùng fixture; ảnh tổng hợp không đo độ chính xác ảnh xe thật.
BLOCKED là thiếu provider/bằng chứng; không tính là đúng nội dung. Token là provider trả về; chưa đối chiếu hóa đơn.
Probe gọi prompt production trực tiếp; không chứng minh nhánh HTTP/UI tương ứng đã chạy. Xem kind và model_calls trong results.json.
Kết quả từng ca được lưu trước khi flush Cloud. Không tự động chạy provider thay thế.
