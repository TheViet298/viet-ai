# Sửa chất lượng trả lời — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đóng các lỗi xử lý đã tái hiện mà không làm mất điều kiện bằng chứng,
nhận diện nguy hiểm, quyền sở hữu hoặc tính nguyên tử của lượt chat.

**Architecture:** Sửa các điểm dùng chung của classifier, context, evidence và
diagnostics. Giữ HTTP/public response enum tương thích, bổ sung trạng thái chất
lượng riêng cho từng ý và toàn phản hồi.

**Tech Stack:** Python/FastAPI, Pydantic, LangGraph, pytest, các service hiện có.

**Spec:** `docs/superpowers/specs/2026-10-19-answer-quality-and-user-memory-design.md`, phần A.

## Global Constraints

- Dùng mốc audit và constraints trong `2026-10-19-remediation-roadmap.md`.
- Không tăng budget/timeout mặc định; không thêm nguồn giả hoặc bỏ kiểm tra claim.
- Không để correction tạo yêu cầu so sánh hoặc tạo hồ sơ/hành động trùng.
- Chỉ câu hỏi thật sự tham chiếu xe trước mới kế thừa model/trim.

## Review Focus

- “bao gồm” cạnh VF8 so với “báo lỗi CC01”: task 1.
- “mẫu xe” so với “màu xe”, “can thiệp” trong VI: task 1.
- Hai bộ phận cùng con số nhưng khác điều kiện bảo hành: task 2.
- Retrieval vừa 6.000 byte nhưng tổng prompt vượt 8.000 byte: task 3.
- Compound có một ý TIMEOUT, một ý có nguồn: task 4.

## Task 1: Routing, ngôn ngữ và đính chính

**Files:** Modify `src/agents/nodes/triage_node.py`, `src/services/chat_language.py`,
`src/services/conversation_context.py`, `src/services/vehicle_catalog.py`,
`src/services/conversation_progress.py`, `src/api/customer.py`,
`src/services/warranty_questions.py`, `src/services/charging_questions.py`,
`src/services/faq_questions.py`.
Test `tests/test_api/test_answer_routing_regressions.py` (new),
`tests/test_api/test_vehicle_cards.py`, `tests/test_services/test_chat_language.py`.

**Interfaces:** Giữ `classify_request_kind(text)`, `detect_language(text, previous)`,
`understand_turn(text, context, recent_turns, budget)`, `select_vehicle_cards(...)`.
`TurnUnderstanding.move/goal/updates/retracted_fields` là đầu vào điều phối thống nhất.

- [ ] Viết test đỏ: ADAS “bao gồm” không ra incident; “xe VF8 báo CC01” vẫn là
  incident; “mẫu xe” không ra appearance; câu VI chứa “can thiệp” trả VI; EN
  thuần trả EN dù UI locale ngược. Câu “can you...” và VI không dấu được kiểm tra riêng.
- [ ] Viết test API: sự cố → P01 → SOC → hỏi trạng thái → P02 → rút CC01 → an
  toàn. Assert state **và** CaseBrief đúng; response xác nhận giá trị mới/bước
  tiếp theo, không có đoạn cẩm nang lạc nội dung hoặc fallback tra cứu.
- [ ] Viết test correction VF8→VF5/Đà Nẵng: subject/fact đúng và
  `vehicle_comparison is False`; không sinh cặp so sánh ngoài yêu cầu.
- [ ] Viết test fresh/after-VF8 cho app, phí sạc và warranty overview: câu hỏi
  chung dùng snapshot chung; câu “bảo hành pin xe VF8 của tôi” vẫn giữ model.
  “Đặt lịch bảo dưỡng qua app” chỉ render các bước đặt lịch, không thêm mục
  tính năng sạc không được hỏi.
- [ ] Run `python -m pytest tests/test_api/test_answer_routing_regressions.py tests/test_services/test_chat_language.py -q`;
  xác nhận lỗi đúng nguyên nhân trước sửa.
- [ ] Sửa nhận diện trên câu gốc có dấu rồi mới dùng fallback không dấu;
  giới hạn mẫu “báo” theo cấu trúc báo lỗi. Dùng move/goal hiện tại để xử lý
  cập nhật sự cố; tách phạm vi câu hỏi hiện tại khỏi slot chỉ được kế thừa.
- [ ] Run lại test trên và `tests/test_api/test_vehicle_cards.py`,
  `tests/test_api/test_long_multitopic_memory.py`. Tất cả assertion liên quan xanh.
- [ ] Review và commit `fix: preserve question intent and incident corrections`.

## Task 2: Bằng chứng có cấu trúc và claim

**Files:** Modify `src/services/answer_evidence.py`, `src/services/rag_service.py`,
`src/agents/nodes/rag_node.py`; Test
`tests/test_agents/test_answer_evidence_regressions.py`,
`tests/test_agents/test_policy_evidence_blocks.py` (new).

**Interfaces:** Giữ `AnswerClaim`, `catalog_fact_sections(citation) -> list[str]`,
`validate_answer_claims(claims, citations, prior_claims) -> dict`.
Các đoạn trả về của `catalog_fact_sections` phải giữ header/condition đúng block.

- [ ] Viết test đỏ từ đoạn SRC-002 đã review: tiêu đề “Pin cao áp”, điều kiện
  mua theo xe mới và dòng VF8 thời hạn ở các dòng khác nhau vẫn hỗ trợ claim
  đúng. Assert `supported is True` cho claim có đầy đủ điều kiện từ cùng block.
- [ ] Viết negative tests: đem con số bộ phận 12V sang pin cao áp; lấy điều kiện
  pin mua thay thế gắn pin theo xe; dùng model/năm không áp dụng; đảo phủ định;
  lấy giá/số từ block khác. Tất cả phải `supported is False`.
- [ ] Viết test thời gian sạc có khoảng SOC/công suất và range có chuẩn đo.
  Không bỏ điều kiện khi render. Claim “có/không có” không được gắn nhãn lỗi
  numeric một cách mặc định chỉ vì key warranty.
- [ ] Run `python -m pytest tests/test_agents/test_policy_evidence_blocks.py -q`,
  quan sát lỗi false rejection; negative controls phải phát hiện cách sửa nới
  lọc sai phạm vi, và đều xanh với cách sửa đúng.
- [ ] Sửa đơn vị evidence theo section/header thay vì tách mù mọi newline;
  ưu tiên metadata phạm vi đã xác minh. Không gộp toàn bộ tài liệu thành một block.
- [ ] Run `python -m pytest tests/test_agents/test_answer_evidence_regressions.py tests/test_agents/test_policy_evidence_blocks.py tests/test_agents/test_rag_failures.py -q`.
- [ ] Review và commit `fix: retain policy scope in claim evidence`.

Assertion mẫu để pin contract (fixture phải trích từ block đã review):

```python
def test_header_and_condition_remain_attached(policy_block, correct_claim, wrong_component_claim):
    assert validate_answer_claims([correct_claim], [policy_block], [])['supported'] is True
    assert validate_answer_claims([wrong_component_claim], [policy_block], [])['supported'] is False
```

## Task 3: Ngân sách prompt và lựa chọn đoạn

**Files:** Modify `src/agents/context_manager.py`, `src/agents/nodes/rag_node.py`,
`src/services/rag_service.py`; Test `tests/test_agents/test_rag_budgets.py`.

**Interfaces:** Giữ `build_7_layer_context(...)`,
`trim_context_layers(layers, max_bytes=8000, *, max_tokens=None) -> list[BaseMessage]`.
`rag_context_max_bytes <= agent_context_max_bytes` vẫn bắt buộc.

- [ ] Viết test đỏ cho quên mật khẩu/app sau VF8: evidence cần thiết 4.811 byte,
  total budget 8.000 byte, history dư có thể bỏ; đoạn thao tác phải còn trong prompt.
- [ ] Viết test Unicode byte, system/safety instructions không bị cắt, header
  và điều kiện chính sách không bị tách. Nếu block tối thiểu không vừa, trả
  `context_budget_exceeded` rõ ràng, không tạo câu trả lời bỏ điều kiện.
- [ ] Run `python -m pytest tests/test_agents/test_rag_budgets.py -q` trước sửa.
- [ ] Phân bổ context dựa theo phần cố định và evidence tối thiểu; bỏ lịch sử
  không liên quan trước. Chỉ chọn các block hỗ trợ đúng câu hiện tại.
- [ ] Run test budgets và routing task 1; đối chiếu cấu hình budget không đổi.
- [ ] Review và commit `fix: reserve prompt space for relevant evidence`.

## Task 4: Partial và diagnostics phản ánh nội dung

**Files:** Modify `src/agents/nodes/rag_node.py`, `src/agents/chatbot_agent.py`,
`src/services/chat_turns.py`, `src/services/request_diagnostics.py`.
Test `tests/test_api/test_compound_answer_status.py` (new),
`tests/test_agents/test_compound_faq_regressions.py`.

**Interfaces:** Mỗi phần có `label`, `status` SUCCESS/NO_SOURCE/ERROR/TIMEOUT và
diagnostics. Thêm keyword tùy chọn `answer_status` cho
`final_response_diagnostics(*, answer_path, successful, stages, answer_status=None)`.
Các giá trị theo spec A. Mapping final_outcome: answered/refused/external_action_required
→ success; partial → partial; needs_clarification → needs_clarification;
needs_data → needs_verified_data; error → error. Báo cáo factual dùng answer_status.

- [ ] Viết test đỏ: warranty có nguồn + maintenance không có → partial,
  giữ câu trả lời/nguồn của phần có, nêu rõ phần thiếu; không final success.
- [ ] Viết test hai ý đủ nguồn → answered; mọi ý thiếu → needs_data; một ý
  timeout → partial/error đúng tình trạng. Không lặp headings hay mất phạm vi xe.
- [ ] Viết controls: refusal ngoài phạm vi và hướng dẫn đặt lịch bên ngoài được
  phân biệt với fallback; không tính referral là câu trả lời đầy đủ giá/lịch thật.
- [ ] Run `python -m pytest tests/test_api/test_compound_answer_status.py -q` trước sửa.
- [ ] Truyền trạng thái từng ý qua node → agent → API → memory/history diagnostics;
  tổng hợp từ phần trả lời thực tế sau localize.
- [ ] Run tests compound, bilingual, idempotency/rollback; metadata history phải
  khớp response đã giao, partial không nhân đôi lượt khi gửi lại request ID.
- [ ] Review và commit `fix: report partial answers per requested topic`.

Assertion cần có ở fixture một ý có nguồn/một ý không:

```python
assert state['final_diagnostics']['answer_status'] == 'partial'
assert state['final_diagnostics']['final_outcome'] == 'partial'
assert '### Bảo hành pin' in data['message']
assert '### Bảo dưỡng định kỳ' in data['message']
```

## Task 5: Đóng lỗi observability đã biết

**Files:** Inspect/modify `src/services/observability.py`, `src/services/agent_llm.py`,
`src/services/llm.py` theo tái hiện. Tests `tests/test_api/test_langfuse_roots.py`,
`tests/test_observability_usage.py`, `tests/test_request_diagnostics.py`.

**Interfaces:** Giữ business HTTP errors; một root/request; usage là provider
trả về, không ghi số 0 giả khi timeout/thiếu usage. Không lộ raw upstream payload.

- [ ] Chạy ba file trên, xác nhận 7 failure baseline; lưu tên lỗi/stack an toàn.
- [ ] Giữ/bổ sung assertion: hai route legacy/critical có đúng một root;
  decorator không nuốt HTTPException; parse failure vẫn giữ usage đã nhận;
  Google non-JSON 503 vẫn được consumer retry; 10 timeout có diagnostics riêng.
- [ ] Sửa đúng lớp tracing/provider adapter từ stack, giữ disabled tracing hoạt
  động và không thực hiện network trong test dùng fake client.
- [ ] Run lại ba file: 0 fail. Chạy full backend để phân biệt hồi quy mới.
- [ ] Review và commit `fix: preserve tracing and provider failure diagnostics`.

## Task 6: Chuyển audit thành gate chất lượng

**Files:** Promote/adapt `tests/test_api/test_answer_gap_audit.py`,
`tests/test_api/test_long_multitopic_memory.py`,
`tests/test_api/test_cross_session_memory_audit.py`,
`eval/report_answer_gap_audit.py`; add `eval/datasets/answer_quality_holdout_v1.jsonl`
và report baseline/after riêng.

**Interfaces:** Cấu hình audit bằng `AUDIT_CONFIG_FILE`, `AUDIT_INDEX_DIR`, không
hardcode máy cá nhân. Chỉ bật live bằng opt-in; fixture offline luôn xác định rõ.

- [ ] Tách các case tái hiện business thành regression mặc định; không để lỗi đã
  sửa bị skip theo audit flag. Giữ live probe là phép đo, không gọi PASS chất lượng.
- [ ] Gắn nhãn đầy đủ: answered/partial/clarification/needs_data/refused/referral,
  scope, evidence và allowed abstention cho từng câu trong bộ cũ.
- [ ] Bổ sung test đối chiếu output theo từng ý, không chỉ state/HTTP/citations.
  Đánh dấu riêng chỗ thiếu field như dung lượng VF3 hoặc giá VF7 AWD.
- [ ] Tạo holdout theo spec, lưu người review/evidence/version và freeze trước
  lượt nghiệm thu; golden chưa duyệt không được làm oracle.
- [ ] Chạy deterministic suite, 27 phiên dài và live baseline/holdout; lưu output,
  model parsed/error, config không chứa key, index hash và metrics tách biệt.
- [ ] Chỉ đóng P0 khi assertions liên quan xanh, full backend/frontend xanh;
  phần thiếu data ghi blocker để bàn giao P1, không tự thay bằng câu đoán.
- [ ] Review và commit `test: gate semantic answer quality across conversation flows`.
