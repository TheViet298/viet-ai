# Tích hợp vào viet-ai/test/agent-long — 19/10/2026

- Nhánh đích remote: `TheViet298/viet-ai`, `test/agent-long`.
- Đầu nhánh trước tích hợp: `e6882bbe1ed561eaf819bcd4f71a029574bdb30e`.
- Nguồn: `13b34acf18692532696fdb54336519848d5d5887` cùng các commit phụ thuộc về chất lượng trả lời, dữ liệu và trí nhớ đã sửa trong phiên.
- Backend, tests, prompts, fixtures, migration và dữ liệu sau giải quyết xung đột trùng bản nguồn; giữ bản sửa ServiceMapCategory riêng của viet-ai. Không xóa artifact chưa track của checkout.

## Kiểm tra trên bản tích hợp

| Bộ kiểm tra | Kết quả | Log cục bộ |
|---|---|---|
| Backend đầy đủ | 2181 passed, 49 skipped, 9 warnings, 6 subtests passed; exit0 | `.test-runs/viet-quality-merge.log` |
| Frontend unit | 177 passed, 0 failed | `.test-runs/viet-quality-frontend.log` |
| 14 câu VI/EN, locale UI ngược ngôn ngữ hỏi | 28/28 đạt hợp đồng; mỗi ngôn ngữ 10 answered, 1 partial, 3 needs_clarification | `.test-runs/viet-quality-contract.log` |
| Holdout đóng băng | 30/30 answerable, 10/10 boundary | `.test-runs/viet-quality-contract.log` |

Gate PostgreSQL vẫn BLOCKED do chưa có database kiểm thử riêng và `TEST_POSTGRES_URL`; không dùng database thật. Các số lượng skip không phải toàn bộ đều do PostgreSQL. Không đổi active Chroma index hoặc cấu hình provider trong lượt tích hợp. Không chứng nhận trạng thái deploy từ việc push branch.

Báo cáo nguồn và các trường hợp ngoài bộ 14 còn chưa ổn định: `docs/testing/answer-gap-14-2026-10-19.md`. Các phát biểu chưa merge/push trong báo cáo gốc mô tả thời điểm trước lượt tích hợp này.
