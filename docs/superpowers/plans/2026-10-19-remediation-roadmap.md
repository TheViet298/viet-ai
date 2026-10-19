# Kế hoạch cải thiện VFServ

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement the selected subplan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Khắc phục các ca trả lời sai/thiếu đã đo, bổ sung data có bằng chứng và
đưa memory xuyên phiên vào hoạt động với khả năng sửa/xóa đúng chủ sở hữu.

**Architecture:** Ba gói nghiệm thu độc lập. Giữ session memory cho ngữ cảnh hiện
tại; bổ sung fact SQL theo user cho thông tin đã được cho phép lưu. Index mới
được xây và kiểm tra riêng trước khi thay active index.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy/Alembic, SQLite/PostgreSQL, Chroma,
pytest, frontend Node tests hiện có. Không yêu cầu thêm vector DB cho user memory.

**Spec:** `docs/superpowers/specs/2026-10-19-answer-quality-and-user-memory-design.md`.

Trạng thái: kế hoạch đề xuất; chưa thực hiện các bước triển khai.

## Global Constraints

- Baseline audit: P-142 `99119c7`, viet-ai `e6882bb`; kiểm tra remote và cây làm
  việc tại lúc bắt đầu. Không ghi đè công việc UI đang có ở checkout gốc.
- VI/EN theo câu hỏi; giữ chứng cứ và điều kiện; không xác nhận hành động thiếu receipt.
- Giữ ngân sách timeout/context đã cấu hình; model lỗi ghi BLOCKED, không giả PASS.
- Mỗi thay đổi chạy chu kỳ test đỏ → sửa tối thiểu → test xanh → review → commit.
- Dữ liệu chưa được thu/xác minh vẫn là missing; giá trị thiếu không được suy diễn.
- Git merge/push/deploy là các bước sau khi có kết quả reviewable và đúng phạm vi.

## Review Focus

1. Số bảo hành đúng nhưng điều kiện/tiêu đề nằm dòng trước — plan chất lượng task 2.
2. Hỏi trạng thái rồi đính chính trụ/mã lỗi — plan chất lượng task 1.
3. Một ý đủ nguồn, một ý thiếu nhưng báo success — plan chất lượng task 4.
4. Quên ở phiên B trong khi request cũ ở A đang chạy — plan memory task 2/3.
5. Profile model cũ và memory model mới mâu thuẫn — plan memory task 2/3.

## Thứ tự thực hiện

| Đợt | Deliverable | Điều kiện nghiệm thu | Plan |
| --- | --- | --- | --- |
| P0 | Sửa routing, VI/EN, evidence, budget, partial và đo lường | Các ca có nguồn được trả lời; các ca thiếu cấu hình hỏi lại; giữ safety/auth | [Chất lượng trả lời](2026-10-19-answer-quality-plan.md) |
| P1 | Bộ data có phạm vi/nguồn được review và index ứng viên | Báo cáo coverage theo ô; câu kiểm chứng trích đúng điều kiện; rollback index có sẵn | [Dữ liệu](2026-10-19-knowledge-data-plan.md) |
| P2 | Memory SQL theo người dùng, consent, sửa/xóa, recall xuyên phiên | 11 capability đạt, các ca quên/cách ly/concurrency đạt, migration hai DB đạt | [Memory](2026-10-19-user-memory-plan.md) |
| Release | Đo toàn bộ và tích hợp hai repo | Các gate bên dưới đạt; ghi rõ phần data còn blocked | Mục cuối tài liệu này |

P1 thu thập có thể làm song song P0. P2 chỉ tích hợp sau khi P0 kiểm soát được
phạm vi câu hỏi, evidence và budget. Mỗi gói có thể tách commit để review/quay lui.

## Gate kết thúc và tích hợp

- [ ] Đưa các phép đo opt-in trong audit thành regression tự động có assertion
  semantic cho ca lỗi đã sửa; tách test provider cần cấu hình khỏi unit test.
- [ ] Chạy 27 phiên dài/540 lượt/36 replay; kiểm tra nội dung, fact, nguồn,
  ngôn ngữ, đúng mã hồ sơ, không tạo hành động trùng.
- [ ] Chạy 63 lượt provider baseline và 40 holdout đã review. Báo riêng answer
  completeness, groundedness, partial, refusal, latency và lỗi provider.
- [ ] Thử chuỗi A→B→C cùng user với tiến trình mới: lưu VF8 Plus/Hà Nội,
  sửa VF5/Đà Nẵng, quên; user khác không nhận được các fact này.
- [ ] Chạy full backend/frontend; đóng 7 lỗi observability cũ. Không gộp lỗi
  có sẵn và lỗi mới thành một số PASS gây hiểu nhầm.
- [ ] Review diff, migrations, index manifest và báo cáo; ghi commit/hash index.
- [ ] Tích hợp P-142 `feature/agent-long` và viet-ai `test/agent-long` khi được
  cho phép thực hiện; fetch trước, giữ thay đổi mới ở nhánh đích, không force-push.
- [ ] Môi trường thật: xác minh biến cấu hình/provider/index, chạy smoke bằng
  tài khoản test, rồi bật user memory sau migration; chưa có xác minh thì ghi rõ.

## Các phụ thuộc cần chốt khi review

- Chấp nhận sáu key memory, cơ chế cho phép ghi nhớ và hành vi xóa trong spec.
- Nguồn/manual chính thức và người xác minh nhãn holdout. Không thể cam kết
  lấp đầy ô không tiếp cận được dữ liệu chỉ bằng sửa code.
- Chọn cách thực hiện: inline trong phiên hiện tại hoặc giao từng task có review.
