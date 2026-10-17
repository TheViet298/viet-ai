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

## Canonical catalog remediation — 16 October 2026

Active retrieval collection: `data/chroma-catalog-colors-v1` (unchanged). The old `data/chroma/` path above describes the initial build only. Scripts named in the original workplan may no longer exist; inspect the repository before using an old acquisition command.

Card/comparison/ranking facts and quote snapshots use `data/verified/vehicle_facts.json`, exposed by `src.services.vehicle_catalog.catalog_facts`, `catalog_cards`, `catalog_citations` and `public_price_snapshots`. `fixtures/verified_public_prices.json` and `data/verified/public_prices.json` are compatibility exports, not independent review authorities. The runtime quote loader must read the canonical helper. A scoped evidence record identifies model, variant, market, drivetrain, range standard, battery capacity, section, review date and unknown year/package fields. Unknown is not N/A. Technical-spec dates were preserved; only price sections actually re-read on 16 October receive that price review date.

Price-review sources: [VF3](https://vinfastauto.com/vn_vi/dat-coc-xe-dien-vf3), [VF5](https://vinfastauto.com/vn_vi/dat-coc-xe-dien-vf5), [VF6](https://vinfastauto.com/vn_vi/dat-coc-xe-dien-vf6), [VF7](https://vinfastauto.com/vn_vi/dat-coc-xe-dien-vf7), [VF8](https://vinfastauto.com/vn_vi/dat-coc-xe-vf8), [VF9](https://vinfastauto.com/vn_vi/dat-coc-xe-vf9). Sections explicitly label these as list prices. The VF7 technical table separately identifies Plus 150 kW and Plus AWD 260 kW, and NEDC 500.5/469 km. No AWD-specific price was inferred from the generic Plus hero section. List prices are not rolling costs or discount eligibility. No model year, effective date or battery-package conclusion was invented.

Knowledge Hub now publishes navigation summaries rather than unverified technical recipes. Synthetic support insights are withheld until each action has reviewed evidence and applicability. Warranty and maintenance must be checked by model/year/component/purpose, never generalized across a page that also contains combustion-engine tables. The [maintenance page](https://vinfastauto.com/vn_vi/dich-vu-bao-duong-oto) includes both electric and combustion vehicles, explaining why a document-level citation alone cannot justify an oil-change instruction for an EV.

See [knowledge-coverage.md](knowledge-coverage.md) for manual acquisition candidates, corpus review queues, image rights/split gates and independently reviewed evaluation requirements. This remediation does not alter the active index, delete images, invent labels or certify release.

A further official-source conflict was confirmed on 16 October: the [VF8 FAQ](https://vinfastauto.com/vn_vi/cau-hoi-thuong-gap/cau-hoi-xe-o-to/san-pham/vf-8) lists different range figures/standards from the current VF8 product page. The registry retains the current product-page 635/475 km NEDC values; it does not import the FAQ range figures. The FAQ's explicit 31-minute 10–70% charging answer was reviewed separately and is linked in per-claim evidence. This is a source-consistency review gap, not evidence that those range figures describe the same model year/configuration.
