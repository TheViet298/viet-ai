# Danh mục Nguồn Dữ liệu Chính thức (Knowledge Base - Nhóm A)

Tài liệu này quản lý toàn bộ các nguồn dữ liệu chính thức phục vụ xây dựng Knowledge Base cho RAG MVP 1 theo quy định tại [`data-workplan-mvp.md`](file:///d:/142.AI20K/P-142/docs/data-workplan-mvp.md) (Mục 2.1 & 2.2).

> **Nguyên tắc cốt lõi (Mục 2.2)**: 
> 1. Chỉ sử dụng tài liệu từ nguồn công khai chính thức của VinFast hoặc tài liệu kỹ thuật được xác minh.
> 2. Mọi dữ liệu crawl phải được lưu bản text sạch gốc kèm URL, ngày truy cập và phiên bản tài liệu.
> 3. Tuyệt đối không dùng nguồn diễn đàn, mạng xã hội, tin đồn cho dữ liệu kỹ thuật và chính sách.
> 4. Không dùng dữ liệu nhóm này để train/fine-tune model; chỉ dùng làm knowledge base cho RAG tra cứu có citation.

---

## Danh sách Nguồn Dữ liệu Được Xác minh

| Mã Nguồn | Tên Tài Liệu & Phạm Vi | URL Chính Thức | Loại Nguồn | Trạng Thái | Ngày Xác Minh | Dòng Xe Áp Dụng |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SRC-001** | Hướng dẫn sử dụng ứng dụng VinFast (App VinFast) | `https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast` | `official_guide` | **Đã xác minh (200 OK)** | 2026-09-30 | Tất cả xe điện VinFast |
| **SRC-002** | Chính sách bảo hành xe ô tô VinFast | `https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-oto` | `official_policy` | **Đã xác minh (200 OK)** | 2026-09-30 | VF 3, VF 5, VF 6, VF e34, VF 7, VF 8, VF 9 |
| **SRC-003** | Thông tin cứu hộ 24/7 và dịch vụ cứu hộ pin | `https://vinfastauto.com/vn_vi/thong-tin-cuu-ho-oto` | `official_service` | **Đã xác minh (200 OK)** | 2026-09-30 | Toàn bộ dòng xe ô tô |
| **SRC-004** | Dịch vụ và quy trình bảo dưỡng ô tô VinFast | `https://vinfastauto.com/vn_vi/dich-vu-bao-duong-oto` | `official_service` | **Đã xác minh (200 OK)** | 2026-09-30 | Toàn bộ dòng xe ô tô |
| **SRC-005** | Dịch vụ sửa chữa và Mobile Service lưu động | `https://vinfastauto.com/vn_vi/dich-vu-sua-chua-oto` | `official_service` | **Đã xác minh (200 OK)** | 2026-09-30 | Toàn bộ dòng xe ô tô |
| **SRC-006** | Dịch vụ pin, trạm sạc & quy chuẩn sạc xe điện | `https://vinfastauto.com/vn_vi/dich-vu-pin-oto-dien` | `official_service` | **Đã xác minh (200 OK)** | 2026-09-30 | Toàn bộ dòng xe ô tô điện |
| **SRC-007** | Sổ tay hướng dẫn sử dụng VinFast VF 8 (Owner's Manual) | `https://om.vinfastauto.com/vi_vn/detail?car=VF8&year=2026` | `official_manual` | **Đã xác minh (200 OK)** | 2026-09-30 | VF 8 |
| **SRC-008** | Sổ tay hướng dẫn sử dụng VinFast VF 5 (Owner's Manual) | `https://om.vinfastauto.com/vi_vn/detail?car=VF5&year=2026` | `official_manual` | **Đã xác minh (200 OK)** | 2026-09-30 | VF 5 |
| **SRC-009** | Danh mục thông số kỹ thuật & phiên bản thương mại | `https://vinfastauto.com/vn_vi/` (Crawl từ catalog chính thức) | `official_catalog` | **Đã xác minh (200 OK)** | 2026-09-30 | Toàn bộ dòng xe (VF 3 - VF 9) |

---

## Cấu trúc Thư mục Lưu trữ

- Dữ liệu text sạch gốc: `data/raw/SRC-*.txt` và `data/raw/SRC-*_meta.json`
- Dữ liệu chunk chuẩn hóa (Mục 2.3): `data/processed/chunks.jsonl`
- Vector Store cục bộ phục vụ RAG: `data/chroma/`
- Script thực thi quy trình:
  - `scripts/crawl_official_sources.py`: Crawl tài liệu web và dịch vụ chính thức.
  - `scripts/crawl_manuals_api.py`: Crawl toàn bộ sổ tay xe chi tiết qua API hệ thống Sổ tay điện tử VinFast.
  - `scripts/process_chunks.py`: Xử lý chunking (kích thước 500 ký tự, overlap 80 ký tự) và chuẩn hóa metadata.
  - `scripts/ingest_knowledge_base.py`: Nạp chunk vào ChromaDB kèm kiểm định trích xuất nguồn.
