# Golden v2 — live

Run `golden-v2-live-49f6c7d554`. Verdicts: `{'BLOCKED': 5}`.

| Công đoạn | Model yêu cầu | Model provider xác nhận | Ca gọi đúng | Ca đạt |
| --- | --- | --- | ---: | ---: |
| normalization | gemini-2.5-flash-lite | chưa xác nhận | 0 | 0 |
| conversation_turn | gpt-4o-mini | chưa xác nhận | 0 | 0 |
| triage | gpt-4o-mini | chưa xác nhận | 0 | 0 |
| general | gpt-4o-mini | chưa xác nhận | 0 | 0 |
| rag_qa | gpt-4o-mini | chưa xác nhận | 0 | 0 |
| memory | gpt-4o-mini | chưa xác nhận | 0 | 0 |
| customer_translation | gpt-4o-mini | chưa xác nhận | 0 | 0 |
| vision.route | gemini-3.5-flash | chưa xác nhận | 0 | 0 |
| vision.dashboard | gemini-3.5-flash | chưa xác nhận | 0 | 0 |
| vision.exterior | gpt-6-luna | chưa xác nhận | 0 | 0 |

| Case | Kết quả | Lỗi hợp đồng | Lỗi bằng chứng |
| --- | --- | ---: | --- |
| GOLD2-VISION-001 | BLOCKED | 0 | model_evidence_missing:vision.route:gemini-3.5-flash |
| GOLD2-VISION-003 | BLOCKED | 0 | model_evidence_missing:vision.route:gemini-3.5-flash |
| GOLD2-VISION-005 | BLOCKED | 0 | model_evidence_missing:vision.dashboard:gemini-3.5-flash |
| GOLD2-VISION-006 | BLOCKED | 0 | model_evidence_missing:vision.dashboard:gemini-3.5-flash |
| GOLD2-VISION-011 | BLOCKED | 1 | model_evidence_missing:vision.dashboard:gemini-3.5-flash |

Nhãn đề xuất chưa duyệt độc lập. RAG dùng fixture; ảnh tổng hợp không đo độ chính xác ảnh xe thật.
BLOCKED là thiếu provider/bằng chứng; không tính là đúng nội dung. Token là provider trả về; chưa đối chiếu hóa đơn.
Probe gọi prompt production trực tiếp; không chứng minh nhánh HTTP/UI tương ứng đã chạy. Xem kind và model_calls trong results.json.
Kết quả từng ca được lưu trước khi flush Cloud. Không tự động chạy provider thay thế.
