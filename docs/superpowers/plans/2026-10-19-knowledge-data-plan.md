# Bổ sung dữ liệu và index — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lấp ô dữ liệu thực sự thiếu bằng nguồn được review; cung cấp evidence
đủ phạm vi cho RAG và hiển thị rõ các ô còn blocked.

**Architecture:** Nguồn chính thức → raw được giữ cấu trúc → fact/section có
metadata → index ứng viên → gate truy xuất/trả lời → đổi active index riêng.

**Tech Stack:** Pipeline ingest/Chroma và script coverage hiện có, JSON registry,
pytest. OCR chỉ dùng khi xác nhận bảng trong tài liệu chính thức là hình ảnh.

**Spec:** `docs/superpowers/specs/2026-10-19-answer-quality-and-user-memory-design.md`, phần B.

## Global Constraints

- Không sửa active index trực tiếp; không chuyển record chưa review thành verified.
- Duy trì nguồn/model/năm/điều kiện; HTTP 200 không tự gia hạn verified_at.
- Trang dịch vụ chung không được thay bảng chu kỳ hoặc giá/khả dụng thực tế.
- Phụ thuộc P0 evidence/partial để nghiệm thu câu trả lời, thu thập có thể bắt đầu trước.

## Review Focus

- Bảng lịch là ảnh hoặc có footnote nằm trang sau — task 1/2.
- “10 năm” của dung dịch làm mát bị hiểu là chu kỳ toàn xe — task 2.
- Màu cấp mẫu xe bị trình bày như màu xác nhận của trim/đời/tồn kho — task 2.
- Ô capacity null bị điền bằng số của model gần giống — task 2.
- Candidate cải thiện một nhóm nhưng làm lệch warranty/safety nguồn cũ — task 3.

## Task 1: Inventory và thu nguồn theo ưu tiên

**Files:** Modify `docs/data-sources.md`, `docs/knowledge-coverage.md`;
Create `data/verified/knowledge_gap_register.json`; use
`scripts/audit_knowledge_coverage.py` và pipeline raw hiện có.

**Interfaces:** Mỗi gap có model, variant, year, topic, required_scope,
status (missing/acquired/pending_review/verified/blocked), source_id nếu có,
evidence location, blocker và người/ngày review thực tế.

- [ ] Chạy lại coverage read-only ở active index đã xác minh đường dẫn; lưu
  hash/count. Con số 85/162 từ 16/10 chỉ là lịch sử, không dùng như phép đo mới.
- [ ] Lập gap register: schedules từng mẫu/năm; màu ngoài VF8; capacity VF3/VF5;
  e34/năm/cấu hình; hướng dẫn app; giá/khả dụng dịch vụ.
- [ ] Đọc nguồn chính thức, đăng ký source ID theo registry hiện tại. Với manual,
  kiểm tra text lẫn bảng/ảnh/footnote trước khi kết luận không có nội dung.
- [ ] Lưu raw + phạm vi/version/ngày lấy; ghi blocked khi portal/tài liệu/quyền
  tiếp cận không cho lấy. Không tạo manual/fact để bù ô thiếu.
- [ ] Review gap register và commit metadata đã kiểm chứng; các nguồn chưa review
  chưa được đưa vào runtime authority.

## Task 2: Chuẩn hóa bảng và fact được review

**Files:** Modify `data/verified/vehicle_facts.json`, `data/verified/catalog_colors.json`,
`fixtures/knowledge/charging_guides.json`, `fixtures/knowledge/warranty_maintenance.json`
khi có nguồn đủ; Create `fixtures/knowledge/maintenance_schedules.json`;
adapt `scripts/ingest_knowledge_base.py`, `src/services/rag_index.py` nếu cần.
Test `tests/test_agents/test_reviewed_knowledge_scopes.py` (new).

**Interfaces:** Schedule record gồm source_id/section, model/year, operation,
interval_km/interval_months nullable, conditions, verified_at/review status.
Canonical vehicle facts hiện có tiếp tục là authority chung cards/quote/RAG.

- [ ] Viết test đỏ từ nguồn đã review: giữ model/năm/header/footnote với ô km/tháng;
  phần điều kiện nặng là record riêng hoặc condition rõ ràng.
- [ ] Viết negative tests: coolant interval không thành lịch tổng quát; màu mẫu
  xe không thành màu trim/year; null capacity không được suy ra; review date
  không thay đổi chỉ vì fetch lại; không áp lịch VF8 cho mẫu khác.
- [ ] Run `python -m pytest tests/test_agents/test_reviewed_knowledge_scopes.py -q`.
- [ ] Điền chỉ record được xác minh; giữ null và blocker cho ô còn thiếu.
  App guide ghi version/thời điểm áp dụng, không trình bày UI 2022 như đã kiểm tra hôm nay.
- [ ] Run lại tests scope, catalog/cards/quote và claim regression P0.
- [ ] Reviewer đối chiếu nguồn, review rồi commit dữ liệu + test cùng nhau.

## Task 3: Candidate index và gate trước đổi cấu hình

**Files:** Use `scripts/ingest_knowledge_base.py`, `scripts/audit_knowledge_coverage.py`,
`eval/rag_engineering.py`, `eval/rag_measurement.py`; save candidate manifest và
report trong `eval/results/knowledge-remediation/`.

**Interfaces:** Manifest có source/content hash, embedding/config, parent-map hash,
reviewed records và danh sách gap chưa xử lý. Active path không thay đổi trong build.

- [ ] Build candidate vào thư mục riêng từ nguồn được review. Kiểm tra integrity
  parent-map/header/conditions và không mất provenance khi khử trùng lặp.
- [ ] Đo coverage theo ô và retrieval theo câu; test đúng source/span/phạm vi,
  không nghiệm thu bằng chunk count tăng.
- [ ] Chạy 63 probe, holdout được freeze và 27 phiên dài với P0. So baseline
  cùng cấu hình; báo rõ latency/provider errors và các ý chỉ trả một phần.
- [ ] Kiểm tra safety/warranty/app/technical negative controls; đủ nguồn nhưng
  trả sai phải fail, thiếu nguồn có abstention đúng được báo riêng.
- [ ] Lưu hash candidate + đường dẫn active cũ + lệnh quay về cấu hình cũ.
  Chỉ đề nghị đổi index khi các gate đạt; ô chưa lấy được được bàn giao blocked.
- [ ] Review và commit manifest/report; thay cấu hình môi trường thật là bước
  phát hành có xác minh riêng, không đồng nghĩa build candidate đã deploy.
