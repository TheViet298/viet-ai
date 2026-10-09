# Báo Cáo Ước Lượng Chi Phí AI Cho Hệ Thống VinFast ServiceFlow AI

* **Thời điểm tính toán:** `2026-10-07T20:33:01.291023`
* **Dự án:** P-142 — VinFast ServiceFlow AI (Web Support Hub & AI Agent)
* **Quy chuẩn đơn giá:** OpenAI Pricing (Model: `gpt-4o-mini`, `text-embedding-3-small`)

---

## Bảng 2.20. Bảng kết quả ước lượng chi phí AI cho toàn bộ kho tài liệu mẫu (8 tài liệu)

| Hạng mục | Model | Token tính phí | Đơn giá | Chi phí (USD) |
| :--- | :--- | :---: | :--- | :---: |
| **Embedding tài liệu (8 tài liệu cẩm nang)** | `text-embedding-3-small` | 431,368 | 0,020000 USD / 1 triệu input token | 0.008627 USD |
| **Embedding câu hỏi RAG (15 câu)** | `text-embedding-3-small` | 450 | 0,020000 USD / 1 triệu input token | 0.000009 USD |
| **Sinh câu trả lời RAG (15 câu)** | `gpt-4o-mini` | 18,000 input + 5,250 output | 0,150000 USD input & 0,600000 USD output / 1 triệu token | 0.005850 USD |
| **Phân loại Triage & Sinh Case Brief (30 ca)** | `gpt-4o-mini` | 24,000 input + 7,500 output | 0,150000 USD input & 0,600000 USD output / 1 triệu token | 0.008100 USD |
| **Tổng ước lượng** | — | — | — | **0.022586 USD** |

> **Ghi chú về tối ưu hóa chi phí:**  
> Hệ thống hiện tại triển khai mô hình **Local Embedding** (ChromaDB + sentence-transformers / all-MiniLM-L6-v2) trực tiếp trên máy chủ cục bộ. Vì vậy, chi phí Embedding thực tế là **0,000000 USD**. Nếu sử dụng Google Gemini Flash (Free Tier / Tier 1), chi phí sinh câu trả lời RAG & Case Brief được tối ưu thêm tới 50% so với `gpt-4o-mini`.

---

## Bảng 2.21. Bảng kết quả ước lượng chi phí AI cho 1 tài liệu cụ thể (Sổ tay hướng dẫn VinFast VF 8)

Để minh họa cụ thể, báo cáo sử dụng tài liệu **"SRC-007: Sổ tay hướng dẫn sử dụng xe VinFast VF 8"** gồm ~380 trang/chuyên mục. Tài liệu được chia thành 371 chunk với tổng cộng 259,862 token. Từ tài liệu này, hệ thống đã thực hiện 5 lượt hỏi đáp kỹ thuật và 3 lượt tạo Case Brief điều phối.

| Hạng mục | Model | Token tính phí | Chi phí (USD) |
| :--- | :--- | :---: | :---: |
| **Index tài liệu (Embedding)** | `text-embedding-3-small` | 259,862 | 0.005197 USD |
| **Embedding câu hỏi RAG** | `text-embedding-3-small` | 150 | 0.000003 USD |
| **Sinh câu trả lời RAG (5 lượt)** | `gpt-4o-mini` | 6,250 input + 1,900 output | 0.002077 USD |
| **Sinh Case Brief sự cố (3 lượt)** | `gpt-4o-mini` | 2,700 input + 900 output | 0.000945 USD |
| **Tổng chi phí tài liệu** | — | — | **0.008223 USD** |

---

## Chi tiết số lượng Token theo từng tài liệu nguồn trong Kho tri thức

| Mã tài liệu | Tên file | Kích thước (Ký tự) | Số lượng Token | Ước lượng Chunks |
| :--- | :--- | :---: | :---: | :---: |
| **SRC-001** | `SRC-001.txt` | 17,570 | 8,696 | 12 |
| **SRC-002** | `SRC-002.txt` | 19,070 | 9,309 | 13 |
| **SRC-003** | `SRC-003.txt` | 1,633 | 841 | 1 |
| **SRC-004** | `SRC-004.txt` | 1,649 | 959 | 1 |
| **SRC-005** | `SRC-005.txt` | 4,036 | 2,121 | 3 |
| **SRC-006** | `SRC-006.txt` | 22,703 | 11,625 | 16 |
| **SRC-007** | `SRC-007.txt` | 523,030 | 259,862 | 371 |
| **SRC-008** | `SRC-008.txt` | 273,982 | 137,955 | 197 |
| **Tổng cộng** | **8 tài liệu** | **863,673** | **431,368** | **614** |

---

## Kết luận & Nhận xét
1. **Chi phí lập chỉ mục (Indexing/Embedding):** Cực kỳ thấp (0.0086 USD cho hơn 430.000 token của 8 tài liệu). Chi phí này chỉ phát sinh 1 lần duy nhất khi nạp hoặc tái chỉ mục kho dữ liệu.
2. **Chi phí hội thoại thực tế:** Với trung bình khoảng ~0,0003 USD đến ~0,0005 USD cho mỗi lượt tương tác hoàn chỉnh (bao gồm cả phân loại Intent, RAG retrieval và trả lời), hệ thống có khả năng xử lý **10.000 lượt yêu cầu khách hàng chỉ với khoảng 3 đến 5 USD**.
