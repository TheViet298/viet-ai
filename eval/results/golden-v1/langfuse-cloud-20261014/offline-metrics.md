# Token, latency và chi phí

60 case; 77 lượt. Token/chi phí lấy từ generation trên Langfuse Cloud.

| Input token | Output token | Tổng token đã biết | Chi phí đã biết (USD) |
| ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0.0000000000 |

| Nhóm | Số ca | Trung bình (s) | P50 (s) | P95 (s) | Max (s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Toàn bộ | 60 | 0.108 | 0.094 | 0.235 | 0.359 |

Latency đo thời gian xử lý toàn bộ các lượt trong một ca, không gồm ghi/đọc Cloud; P95 dùng nearest rank. Không phải latency từng tin nhắn hoặc SLA production.

Coverage Cloud đầy đủ: `True`. Generation thiếu usage: 0; thiếu cost: 0.
Giá trị thiếu được ghi null/trống trong JSON/CSV, không thay bằng 0. Ca có trace nhưng không có generation ghi nhận 0 token/chi phí model.

Chi phí là số Cloud ghi nhận, chưa đối chiếu hóa đơn provider. Chi tiết từng ca: [offline-case-metrics.csv](offline-case-metrics.csv).
