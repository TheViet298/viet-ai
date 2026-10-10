# P-142 Agent Memory Index

Mục đích: giảm đọc lặp lại nhưng không thay thế bằng chứng trong repo. Nạp `CORE.md` cho task mới; chỉ mở `MAP.md` khi cần tìm nguồn/module và `DECISIONS.md` khi task chạm quyết định.

## Các lớp memory

| Lớp | Nguồn gọn | Dùng khi |
|---|---|---|
| Semantic — mục tiêu và ranh giới | [CORE.md](CORE.md) | Mọi task P-142 |
| Structural — bản đồ thư mục/nguồn chuẩn | [MAP.md](MAP.md) | Cần tìm module hoặc tài liệu đúng |
| Decision — quyết định đã chốt | [DECISIONS.md](DECISIONS.md) | Thay đổi sản phẩm, agent, dữ liệu, auth, ảnh, vị trí hoặc lifecycle |
| Episodic — tiến độ và kết quả theo thời điểm | WORKLOG.md, JOURNAL.md, [docs/eval_evidences.md](../../docs/eval_evidences.md), báo cáo cụ thể trong `eval/results/` | Chỉ khi hỏi trạng thái, kết quả, hoặc task phụ thuộc lịch sử |
| Procedural — cách làm | [AGENTS.md](../../AGENTS.md), `../rules/`, workflow/skill liên quan | Khi làm theo quy trình hoặc thay đổi trong phạm vi có rule |

## Quy tắc nạp tiết kiệm

1. Nạp memory vừa đủ; prompt đã chỉ rõ file thì mở trực tiếp file đó.
2. Mở nguồn gốc liên quan; xác nhận hành vi hiện tại trong code/test.
3. Chỉ đọc WORKLOG/JOURNAL/eval report khi cần lịch sử hoặc trạng thái.
4. Khi mâu thuẫn, phân loại bằng chứng: code/test = hành vi; ADR Accepted = quyết định; scope/architecture = thiết kế; README/log có thể chậm cập nhật. Nêu rõ điểm chưa xác minh.

## Ghi và bảo trì memory

- Memory chỉ giữ sự thật ổn định và đường dẫn nguồn. Không chép lại report, prompt, hội thoại hay tiến độ theo ngày.
- Chỉ cập nhật khi quyết định được chấp thuận hoặc cấu trúc nguồn đổi; link tới nguồn chuẩn.
- Không ghi secret, PII, raw chat, transcript, API key hoặc thông tin suy đoán.
- Không coi mục tiêu đo lường là kết quả đạt được. Không khẳng định tính năng chạy được chỉ từ README hoặc sơ đồ.
