# Memory xuyên phiên — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ghi nhớ, nhắc lại, sửa và quên các fact người dùng đã cho phép lưu qua
phiên mới và tiến trình mới; giữ đúng cách ly người dùng và ngữ cảnh sự cố.

**Architecture:** Fact có cấu trúc trong app DB theo user, snapshot có revision,
ghi/xóa bằng compare-and-swap trong transaction. Dùng session context cho goal,
case và nguy hiểm hiện tại. Chưa cần thêm kho vector hoặc replay chat cũ.

**Tech Stack:** SQLAlchemy, Alembic, SQLite/PostgreSQL, Pydantic, FastAPI/pytest.

**Spec:** `docs/superpowers/specs/2026-10-19-answer-quality-and-user-memory-design.md`, phần C.

## Global Constraints

- Chỉ sáu key trong spec; thông tin sở hữu khác với chiếc xe đang quan tâm.
- Có nguồn/cho phép lưu; không học từ assistant/RAG/ảnh/tài liệu hoặc user ID trong chat.
- Không hydrate goal, cảnh báo nguy hiểm, vị trí tức thời, mã lỗi/trụ hay lịch cũ.
- Source data và memory chỉ lấy theo principal đã xác thực; guest không có LTM.
- Feature flag `user_memory_enabled` mặc định false; deploy migration trước code.
- Xác nhận đã nhớ/quên chỉ sau khi ghi thành công; conflict/rollback không phát ack sai.
- Không backfill toàn bộ transcript, không tự cập nhật version/đời xe từ model khác.

## Review Focus

- Hai phiên cập nhật cùng key, một phiên quên khi request cũ đang chạy: task 2/3.
- Profile VF8 cũ và fact mới VF5 hoặc fact đã quên: task 2/3.
- “Tư vấn VF8”, phủ định sở hữu, câu trích dẫn, instruction trong tài liệu: task 2.
- Đổi xe giữ nhầm Plus/năm/phương án pin: task 2.
- Xóa nguồn phiên hoặc xóa toàn lịch sử rồi snapshot cũ ghi lại fact: task 3/4.

## Task 1: Schema bổ sung và feature flag

**Files:** Modify `src/models/db_models.py`, `src/config.py`;
Create `migrations/versions/4e01_user_memory.py`,
`tests/test_api/test_user_memory_migration.py`.

**Interfaces:** `User.memory_revision: int` server/default 0.
`UserMemoryFact` theo schema spec, composite PK `(user_id, key)`;
user FK CASCADE, source IDs nullable. `Settings.user_memory_enabled: bool = False`.
Revision dự kiến `4e01_user_memory`, down_revision `3d01_service_points` nếu đây
vẫn là head tại lúc thực hiện; nếu head đổi thì tạo migration tiếp head thực tế.

- [ ] Viết test đỏ upgrade DB có user/chat/case cũ: dữ liệu cũ giữ nguyên,
  revision=0, bảng fact trống, key/user duy nhất. Không tự tạo fact từ transcript.
- [ ] Viết test constraints/foreign key và roundtrip schema trên SQLite; cùng
  tests chạy PostgreSQL qua `TEST_POSTGRES_URL` dành riêng cho test. Không dùng
  URL production hoặc xóa schema production để thử migration.
- [ ] Run `python -m pytest tests/test_api/test_user_memory_migration.py -q` trước sửa.
- [ ] Tạo additive migration và ORM. Không sửa migration đã phát hành, không
  trộn backfill chat vào DDL; ghi hướng rollback app/flag giữ schema bổ sung.
- [ ] Run migration tests hai DB, ghi môi trường thiếu PostgreSQL là BLOCKED;
  chạy auth/session regression với flag off để kiểm tra tương thích.
- [ ] Review và commit `feat: add versioned user memory storage`.

## Task 2: Service fact, consent, provenance và revision

**Files:** Create `src/services/user_memory.py`,
`tests/test_services/test_user_memory.py`; Modify `src/api/auth.py` tại các
đường ghi profile/đăng ký model để đồng bộ khi feature bật.

**Interfaces trong `user_memory.py`:**

- `MemoryFact(value: str | int | None, status: Literal['confirmed','unknown','retracted'], source_kind: Literal['chat','profile'], source_session_id: str | None, source_message_id: str | None, updated_at: datetime)`.
- `MemorySnapshot(revision: int, facts: dict[str, MemoryFact])`;
  fact có value/status/source_kind/source IDs/updated_at theo spec.
- `MemoryChange(key: str, value: str | int | None, status: str)` với whitelist,
  giá trị/nguồn phải validate trước ghi.
- `MemoryWriteResult(status: Literal['written','unchanged','conflict'], revision: int)`.
- `load_user_memory(db: Session, user: User) -> MemorySnapshot`.
- `extract_memory_changes(text: str, snapshot: MemorySnapshot, context: ConversationContext) -> list[MemoryChange]`.
- `apply_user_memory_changes(db: Session, user: User, changes: list[MemoryChange], *, expected_revision: int, source_kind: Literal['chat','profile'], source_session_id: str | None, source_message_id: str | None) -> MemoryWriteResult`.
- `resolve_personal_memory(text: str, snapshot: MemorySnapshot) -> dict`: chỉ
  fact liên quan tới personal recall hoặc profile xe cần xác nhận; không sửa goal.

- [ ] Viết test đỏ: “Hãy nhớ xe của tôi là VF8 Plus, tôi ở Hà Nội” lưu đúng
  model/version/home_city với source; load cùng user ở phiên mới trả các fact đó.
- [ ] Viết test không ghi: tư vấn VF8, nói xe người khác, phủ định sở hữu, câu
  trích dẫn, RAG/assistant bảo “hãy nhớ”, guest; “tôi đang ở trạm…” không đổi home_city.
  Reject key ngoài whitelist, giá trị sai type/control characters; fact đưa vào
  prompt được phân định là dữ liệu, không thể trở thành instruction hệ thống.
- [ ] Viết correction tests: xe đã lưu VF8 Plus sửa VF5 → model VF5, phiên bản/
  năm/phương án pin cũ bị vô hiệu; home_city/registration_city tách biệt; quote
  cho xe khác không đổi xe sở hữu. Câu mơ hồ cần xác nhận.
- [ ] Viết CAS tests: revision đúng tăng một lần; stale revision → conflict và
  không đổi fact; replay → unchanged; quên rồi request cũ ghi → conflict.
  Forget xóa value, không để bản sao giá trị cũ trong bảng fact/history phụ.
- [ ] Run `python -m pytest tests/test_services/test_user_memory.py -q` trước sửa.
- [ ] Implement service bằng SQL hiện có, không commit riêng trong helper.
  Đồng bộ `User.vehicle_model` khi sửa/quên model; profile update cũng tăng
  revision, vô hiệu children và cập nhật provenance, tránh projection cũ hồi sinh.
- [ ] Run lại service tests cùng rollback/concurrent update trên hai DB.
  Memory operation diagnostics chỉ key/revision/status/timing, không thêm raw value.
- [ ] Review và commit `feat: manage consented user facts with revision checks`.

Assertion tối thiểu cho test CAS (snapshot ban đầu revision 0):

```python
assert written.status == 'written'
assert written.revision == 1
assert stale.status == 'conflict'
assert load_user_memory(db, user).facts['owned_vehicle.model'].value == 'VF8'
```

## Task 3: Nối vào chat, recall và API xem/quên

**Files:** Modify `src/services/chat_turns.py`, `src/api/customer.py`,
`src/services/customer_localization.py`, `src/services/help_localization.py`,
`src/models/schemas.py`, `src/main.py`;
Create `src/api/customer_memory.py`, `tests/test_api/test_customer_memory.py`.

**Interfaces:** Dùng các hàm task 2. Router mới dùng `require_customer` và envelope
ApiResponse hiện có. `GET /customer/memory` trả revision + fact/provenance của
user hiện tại; `DELETE /customer/memory/{key}` và `DELETE /customer/memory`
trả 200 với deleted/revision, idempotent. Prefix đầy đủ `/api/v1` do main mount.
Unknown key → 400; chưa đăng nhập → 401; không nhận owner tùy chọn trong body/query.

- [ ] Viết test đỏ API cùng user A→B: lưu VF8 Plus/Hà Nội ở A, B recall đúng
  trong VI/EN và không gọi đó là sự cố; explicit model hiện tại thắng memory.
- [ ] Viết test personal recall độc lập với scope màu sắc; app/generic overview
  không bị ép theo xe sở hữu; mới báo sự cố có xe đã lưu thì hỏi xác nhận nhẹ
  như profile hiện có, chưa tự chẩn đoán.
- [ ] Viết test quên qua chat và DELETE, xóa một phiên có fact nguồn chat, xóa
  toàn lịch sử, projection/profile nguồn riêng, revision fence và stale snapshot.
  Không xóa gián tiếp hồ sơ sự cố nghiệp vụ khi chỉ quên fact cá nhân.
- [ ] Viết auth tests: user B không lấy/sửa fact A qua session_id/param/key;
  guest không tạo fact; role sai bị chặn; không có leak qua cache/error/telemetry.
- [ ] Viết fault injection sau flush: user memory, profile projection, revision,
  messages và session state cùng rollback; không có ack “đã nhớ/quên” sai.
  Request ID trùng không ghi memory hai lần.
- [ ] Run `python -m pytest tests/test_api/test_customer_memory.py -q` trước sửa.
- [ ] Load snapshot theo user lúc xử lý request, dùng chọn lọc sau khi hiểu ý;
  không đặt subject/goal đại trà. Ghi changes từ lượt user đã chấp nhận trong
  transaction hiện có; nếu CAS conflict, giữ fact mới nhất và báo chưa lưu thay đổi.
- [ ] Dùng chung service cho API/chat/profile/delete history. Response acknowledgement
  theo kết quả ghi cuối cùng; đầy đủ VI/EN. Không cần thêm màn settings để nghiệm thu API/chat.
- [ ] Run tests API, transaction/auth/guest, long-session và bilingual; flag off
  cho hành vi cũ, flag on cho hành vi mới đều không hồi quy safety.
- [ ] Review và commit `feat: recall and forget user facts across chat sessions`.

## Task 4: Đóng capability gaps và gate phát hành

**Files:** Promote deterministic cases trong
`tests/test_api/test_cross_session_memory_audit.py`,
`eval/cross_session_probe_worker.py` thành
`tests/test_api/test_cross_session_user_memory.py`;
Modify report audit; create deployment/rollback notes cho user memory.

**Interfaces:** Worker dùng process mới/request, cấu hình test qua tham số/env
portable, `user_memory_enabled=true` cho suite feature; không đọc secret máy cá
nhân mặc định. Provider live vẫn opt-in và được ghi rõ số parsed/error.

- [ ] Chuyển 11 capability đã đo thành assertion nội dung + state, bỏ skip opt-in
  đối với deterministic regressions đã đủ fixture. Câu recall không có “mẫu xe”
  để chứng minh hydrate; giữ riêng regression “mẫu xe” của P0.
- [ ] Chạy A→B→C cùng user qua process mới: lưu model/trim/city; sửa model/city;
  quên; mở lại phiên cũ và mới; không resurrect value. Thử cả profile cũ mâu thuẫn.
- [ ] Hai user chạy 10/20/30 lượt nhiều chủ đề xen kẽ, request trùng và rollback;
  không lẫn owner/goal/case/hazard. Giữ control hỏi mua không thành xe sở hữu.
- [ ] Chạy SQLite/PostgreSQL, default flag off/on, provider offline/live riêng;
  11 capability đạt và các security/concurrency/forget controls đạt trước release.
- [ ] Chạy gate release trong roadmap, review migration và fallback khi không
  bật feature. DDL trước code, bật flag sau smoke; quay lui bằng flag/app trước,
  giữ schema. Không tự deploy môi trường thật khi mới xong test local.
- [ ] Commit report triển khai có output/hash/config đã dùng và các blocker thật.
