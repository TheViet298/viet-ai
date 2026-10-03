# Kế hoạch cải thiện chất lượng hệ thống Agent để đạt MVP

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đưa hệ thống Agent đạt đủ bảy mục tiêu eval đã thống nhất, đồng thời giữ nguyên quy tắc an toàn, quyền truy cập và nguồn chính thức.

**Architecture:** Giữ luồng sáu node hiện có. Tách quyết định phân loại, routing và kiểm tra chính sách khỏi sinh văn bản; cải thiện truy xuất và quản lý lời gọi Gemini theo ngân sách toàn lượt. Mọi cải thiện phải có bằng chứng từ tập dev và lần đánh giá nghiệm thu độc lập.

**Tech Stack:** Python 3.12, FastAPI, LangGraph, Pydantic, SQLite, Chroma, Gemini qua adapter hiện có, pytest, Ruff.

**Spec:** `docs/superpowers/plans/2026-10-01-complete-agent-system.md`; `docs/decisions/ADR-002-triage-and-hitl.md`; `docs/decisions/ADR-003-data-and-evaluation.md`; `docs/decisions/ADR-005-roles-location-and-customer-confirmation.md`.

**Ngày lập:** 03/10/2026, Asia/Saigon. **Trạng thái:** Kế hoạch; chưa triển khai các thay đổi bên dưới.

## 1. Tiêu chí thành công

| Chỉ số | Offline hiện tại | Online + dự phòng hiện tại | Điều kiện nghiệm thu |
|---|---:|---:|---:|
| Nhận diện nguy hiểm nghiêm trọng | 100% | 100% | 100% |
| Phân loại intent | 76,67% | 70% | ≥ 85% |
| Routing | 60% | 56,67% | ≥ 80% |
| Câu trả lời có trích dẫn đáp ứng tiêu chí | 20% | 20% | ≥ 85% |
| Xử lý đúng thiếu nguồn/từ chối | 100% | 100% | ≥ 80% |
| Độ trễ trung bình toàn lượt | 0,201 giây | 11,228 giây | ≤ 2,5 giây |
| Khớp quyết định chuyển nhân viên | 70% | 70% | ≥ 85% |

Với bộ cũ: intent cần ít nhất 26/30 đúng; routing 24/30; trích dẫn 9/10; chuyển nhân viên 26/30. Safety hiện chỉ có một mẫu critical, vì vậy cần tập bổ sung trước khi kết luận.

Mục tiêu bổ sung của kế hoạch: không bỏ sót bất kỳ trường hợp bắt buộc HITL nào trong tập nghiệm thu; mọi lỗi timeout/quota đều có trạng thái đo được; không còn sự cố hiện tại bị trả lời như FAQ thuần. Đây là điều kiện bảo vệ bổ sung, không thay đổi mẫu số của bảy KPI gốc.

## 2. Ràng buộc chung

- Hard Safety Rules chạy trước LLM; phản hồi khẩn cấp không đợi Gemini, vị trí, quota hoặc ghi trace thành công.
- Giữ giới hạn hai lượt hỏi làm rõ và năm lượt trải nghiệm Guest; chỉ Customer đã xác thực được lưu case thực.
- Ticket kỹ thuật, khiếu nại và confidence < 0,60 giữ yêu cầu HITL theo ADR-002. FAQ thông tin phải được phân biệt với ticket thực tế; mọi sửa nhãn cần ghi căn cứ chính sách.
- Chỉ dùng tài liệu công khai chính thức; kiểm tra URL, phiên bản, dòng xe và nội dung. Không thêm kiến thức kỹ thuật từ trí nhớ model.
- Đầu ra tool tối đa ba chunk, ngân sách hiện hành 1.200 đơn vị ước lượng bảo thủ; các lớp System/Policy được giữ nguyên.
- Hiện code dùng Chroma distance ≤ 0,70, còn ADR-003 ghi similarity ≥ 0,70. Hai đại lượng không tương đương. Phải ghi rõ metric/embedding và thống nhất cách áp dụng; chưa có căn cứ thì giữ bộ lọc bảo thủ, không nới ngưỡng để tăng điểm.
- Không sửa trực tiếp dataset v1 hoặc ghi đè báo cáo gốc; mọi nhãn sửa có phiên bản, lý do và người rà soát.
- Không đưa khóa API, nội dung nhạy cảm hay suy luận nội bộ vào trace/báo cáo.
- Giữ nguyên thay đổi có sẵn của người dùng. Các bước kiểm chứng dùng DB/thư mục kết quả riêng; không ghi lại Chroma đang dùng trước khi có bản candidate được kiểm tra.

## 3. Bằng chứng và thứ tự ưu tiên

| Nhóm | Quan sát đã xác nhận | Quyết định |
|---|---|---|
| Triage | `TRIAGE-020/030/044` bỏ sót cách diễn đạt sự cố; `TRIAGE-029` nhầm pin smart key với pin xe | Chuẩn hóa nhận diện đối tượng và trạng thái sự cố trước phân loại |
| Routing | Code hiện ánh xạ cố định theo intent, chưa có `mobile_service`; brief tính lại routing, ghi đè routing từ safety | Dùng một hàm routing chung; brief giữ quyết định đã được kiểm tra |
| FAQ | `RAG-006/009` đi sang CLARIFICATION; câu hỏi về dịch vụ/điều khiển chưa có sự cố thực tế | Quyết định FAQ dựa trên trạng thái yêu cầu, không chỉ từ khóa |
| RAG | 8/10 tình huống cần nguồn chưa đạt; một số có FAQ_ANSWER nhưng thiếu tiêu chí nội dung | Đo riêng chọn nguồn, chọn đoạn và đủ nội dung câu trả lời |
| Catalog | File chunk có 59 chunk `SRC-009`; `RAG-004/005` vẫn NO_SOURCE | Kiểm tra nội dung/model/filter/truy xuất; không kết luận thiếu toàn bộ nguồn |
| Gemini | Sáu sự kiện parsed; kiểm tra sau eval trả `GoogleRateLimitError` | Đo kết quả mọi lần gọi; giới hạn thời gian toàn lượt và ngắt tạm khi quota |
| Nhãn eval | `TRIAGE-014/029` yêu cầu review=false dù có sự cố/HIGH; `TRIAGE-009/054` cần rà soát cách phân loại | Audit chính sách trước tối ưu; báo cáo v1 và bản adjudicated riêng |

Ưu tiên: **độ tin cậy phép đo → safety/triage/routing → RAG → tích hợp model/độ trễ → nghiệm thu**. Dữ liệu nguồn đủ hay chưa và nguyên nhân từng lỗi RAG còn cần kiểm chứng.

## 4. Phương án lựa chọn

1. **Khuyến nghị — sửa theo lỗi đo được, giữ kiến trúc:** quy tắc quyết định cho safety/routing; Gemini hỗ trợ trường hợp khó trong ngân sách; truy xuất tốt hơn nhưng vẫn có nguồn kiểm chứng. Có thể nghiệm thu từng phần và giữ chất lượng khi provider lỗi.
2. **Chỉ đổi prompt/model:** ít sửa code nhưng không giải quyết routing bị ghi đè, FAQ đi sai nhánh, thiếu quan sát lỗi và quota.
3. **Thay toàn bộ embedding/kiến trúc:** chỉ xem xét sau khi audit chứng minh truy xuất hiện tại không đáp ứng; chi phí đổi dữ liệu và kiểm chứng lớn hơn.

Không thực hiện fine-tuning hoặc thay cả kiến trúc trong đợt này.

## 5. Phân chia file và hợp đồng

| File | Vai trò dự kiến |
|---|---|
| `scripts/run_agent_eval.py` | Đo graph, hỗ trợ dataset/run mode rõ ràng, báo cáo tiếng Việt |
| `scripts/audit_agent_eval.py` — mới | Tổng hợp lỗi từng case, phiên bản nhãn và coverage nguồn |
| `eval/datasets/agent_label_review_v2.jsonl` — mới | Ghi nhãn cũ/mới, căn cứ, trạng thái rà soát |
| `eval/datasets/agent_acceptance_v2.jsonl` — mới | Tập nghiệm thu bổ sung, chưa dùng chỉnh prompt |
| `src/agents/routing.py` — mới | Quyết định routing chung có reason code |
| `src/agents/nodes/triage_node.py`, `safety_node.py`, `case_brief_node.py` | Phân loại, giữ routing, không để sinh văn bản hạ quyết định an toàn |
| `src/services/rag_service.py`, `src/agents/nodes/rag_node.py` | Truy xuất đã lọc model, kiểm tra nguồn và độ đủ của bằng chứng |
| `scripts/process_chunks.py`, `scripts/ingest_knowledge_base.py` | Chỉ sửa nếu audit chứng minh lỗi dữ liệu; tạo bản candidate độc lập |
| `src/services/agent_llm.py`, `src/services/llm.py`, `src/config.py`, `src/services/tracer.py` | Deadline, kết quả lỗi được phân loại, circuit breaker và số liệu |
| `src/agents/state.py`, `src/agents/graph.py` | Truyền ngân sách lượt và metadata đo lường |
| `prompts/triage.md`, `rag_qa.md`, `version_log.csv` | Chỉ thay sau khi có lỗi dev và bằng chứng tăng chất lượng |
| `tests/test_agents/test_quality_regressions.py`, `test_rag_quality.py`, `test_llm_budget.py` — mới | Regression và kiểm tra các hợp đồng mới |
| `tests/test_eval/test_evaluation_runner.py` | Denominator, mode, nhãn và tiêu chí tính điểm |

## 6. Review Focus

1. Yêu cầu có từ hỏi giá nhưng đồng thời có bộ phận hỏng: vẫn là ticket, không bỏ qua HITL — Task 2.
2. FAQ về an toàn khác sự cố đang diễn ra; thiếu bằng chứng thì từ chối/chuyển review, không sinh hướng dẫn mới — Task 2/3.
3. Chỉ biết dòng xe nhưng không biết phiên bản/năm: không lấy thông số từ biến thể khác — Task 3.
4. Provider bị quota giữa hai node hoặc nhiều phiên đồng thời: phản hồi vẫn trong ngân sách, không retry hàng loạt — Task 4.
5. Đổi nhãn hoặc chạy ít mẫu làm điểm tăng giả: giữ báo cáo v1, hash dữ liệu, mẫu số và coverage — Task 1/5.

## 7. Các task triển khai

### Task 1 — Chuẩn hóa phép đo và rà soát nhãn

**Files:** `scripts/run_agent_eval.py`, mới `scripts/audit_agent_eval.py`, `eval/datasets/agent_label_review_v2.jsonl`, `tests/test_eval/test_evaluation_runner.py`.

**Interfaces:**
- Giữ `compute_evaluation_metrics(results: list[dict]) -> dict` và bảy metric hiện có.
- Thêm `audit_results(results_path: Path, dataset_paths: list[Path]) -> list[dict]` trả `id`, lỗi intent/routing/review/grounding, căn cứ hiện có và nguyên nhân chưa xác nhận.
- Mở rộng runner nhận đường dẫn dataset; mỗi run ghi mode, dataset hash, prompt hash, model, embedding/KB version, sample counts, response type, cited source IDs, sanitized evidence và từng giai đoạn latency.

- [ ] Viết test RED: `test_label_versions_do_not_overwrite_v1`; `test_empty_denominator_is_na`; `test_unanswered_faq_is_not_grounded`; `test_online_fallback_coverage_is_explicit`. Tất cả mẫu cần nguồn được giữ trong mẫu số kể cả CLARIFICATION/NO_SOURCE.
- [ ] Chạy riêng test mới; xác nhận fail vì contract mới chưa có, không vì môi trường.
- [ ] Triển khai audit và metadata. Tách ba chế độ `offline`, `online`, `provider_failure`; không gọi một run trộn fallback là online thuần.
- [ ] Lập bảng review cho mọi case lệch: ưu tiên `TRIAGE-009/014/017/029/033/054`; không mặc định cho rằng nhãn cũ hoặc Agent đúng. Mỗi thay đổi ghi căn cứ ADR/source và người rà soát; bản chưa rà soát không dùng nghiệm thu.
- [ ] Giữ v1 để so sánh; thêm báo cáo chính sách độc lập đo bỏ sót HITL. Bộ 45 case đã được xem dùng làm regression chẩn đoán, không tiếp tục gọi là holdout chưa thấy.
- [ ] Chạy test evaluator: `python -m pytest tests/test_eval/test_evaluation_runner.py -q -p no:cacheprovider --basetemp=.test-runs/quality-task1`.

**Nghiệm thu:** Mọi lỗi baseline có ID và tầng nghi ngờ; số liệu v1 tái tính đúng; thay đổi nhãn hiển thị riêng, không che mức cải thiện bằng sửa mẫu số.

### Task 2 — Sửa triage, routing và giữ quyết định safety

**Files:** mới `src/agents/routing.py`, `tests/test_agents/test_quality_regressions.py`; sửa `triage_node.py`, `safety_node.py`, `case_brief_node.py`, `guardrails.py`, `state.py`, `prompts/triage.md`.

**Interfaces:**
- `classify_request_kind(text: str) -> Literal["faq", "incident", "complaint", "oos", "uncertain"]` trong `triage_node.py`.
- `RoutingDecision` gồm `target: str`, `reason_code: str`; `decide_routing(state: AgentState) -> RoutingDecision` trong `routing.py`.
- Hỗ trợ sáu đích: `emergency_rescue`, `mobile_service`, `service_center`, `charging_support`, `customer_relations`, `sales_support`.
- Node brief sử dụng routing đã được hàm chung kiểm tra, không ánh xạ lại chỉ bằng intent.

- [ ] Viết test RED với diễn đạt mới cùng nhóm lỗi: xe không lên nguồn → incident; pin chìa khóa → không nhầm traction battery; phụ tùng gãy dù hỏi giá → incident/HITL; app crash gây không mở khóa → yêu cầu hỗ trợ hoặc complaint theo taxonomy đã review.
- [ ] Viết test `test_policy_refusal_routing_survives_brief` và `test_mobile_service_routing_survives_brief`: `routing` trước/sau brief bằng nhau; refusal giữ HIGH và review=true.
- [ ] Viết test phân biệt câu hỏi thông tin về cứu hộ/app với sự cố thực: FAQ không bị đòi mã lỗi; hiện có khói/mất phanh vẫn phản hồi emergency, không gọi LLM.
- [ ] Chạy test xác nhận RED, sau đó triển khai nhận diện thực thể/trạng thái và routing với thứ tự: critical → policy refusal → cứu hộ theo nhu cầu → mobile service → service/charging/complaint/sales.
- [ ] Với xe hết pin trên cao tốc và yêu cầu kéo xe: kiểm tra routing cứu hộ; không tự đổi taxonomy safety nếu điều kiện critical chưa được thống nhất. Không cam kết đã điều xe đến.
- [ ] Rà soát nghĩa phủ định, thông tin quá khứ và trích dẫn tình huống trong câu hỏi an toàn; bổ sung test đối chứng. Trường hợp không rõ hiện tại phải hỏi ngắn hoặc dùng hướng dẫn bảo thủ.
- [ ] Chạy `python -m pytest tests/test_agents/test_quality_regressions.py tests/test_agents/test_boundary_regressions.py -q -p no:cacheprovider --basetemp=.test-runs/quality-task2`.

**Nghiệm thu:** Không còn routing bị brief ghi đè; các lỗi service/mobile đã xác nhận có regression đạt; không phát sinh bỏ sót HITL. Bảng taxonomy/routing chưa được review thì chưa đổi để chạy theo nhãn.

### Task 3 — Cải thiện RAG theo từng tầng lỗi

**Files:** `src/services/rag_service.py`, `src/agents/nodes/rag_node.py`, mới `tests/test_agents/test_rag_quality.py`; các script chunk/ingest và metadata nguồn chỉ khi có bằng chứng cần sửa.

**Interfaces:**
- Giữ `RAGService.retrieve(query: str, top_k: int = 3, vehicle_model: str | None = None) -> dict` tương thích caller.
- Thêm `retrieve_diagnostics(...) -> dict` nội bộ: candidate source/chunk IDs, distance, filter reason (`model_mismatch`, `registry_mismatch`, `distance`, `unsafe_content`), không lộ nội dung chưa sanitize.
- Thêm `select_supported_evidence(query: str, citations: list[dict]) -> list[dict]` để chọn đoạn đủ liên quan trước sinh câu trả lời.

- [ ] Viết test RED: khác model bị loại; sai phiên bản không được dùng cho thông số; URL chưa verify không thành citation; đoạn độc hại không được vào prompt; câu trả lời có link nhưng thiếu bằng chứng nội dung không được đánh dấu grounded.
- [ ] Chạy riêng tests xác nhận RED.
- [ ] Audit 8 case RAG chưa đạt: kiểm tra nguồn có nội dung kỳ vọng hay không, candidate có chứa đoạn đúng không, bị lọc ở đâu, snippet có bị cắt mất điều kiện/đơn vị không. Ghi từng kết luận kèm chunk ID.
- [ ] Chuẩn hóa truy vấn và metadata dòng xe; lọc model trước khi lấy ứng viên. Thử tối đa 20 ứng viên nội bộ, xếp hạng dựa trên liên quan của thuật ngữ và bằng chứng; chỉ trả tối đa ba chunk ra tool. Không ưu tiên theo ID của test.
- [ ] So sánh trên dev với retrieval hiện tại trước khi thay. Kiểm tra metric distance của collection; không quy đổi similarity bằng công thức tùy tiện, không nới 0,70 chỉ để đạt điểm.
- [ ] Nếu nội dung SRC-009 hoặc nguồn khác thiếu: cập nhật từ trang chính thức đã xác minh, giữ raw text/URL/ngày/phiên bản; xây Chroma candidate tại `.test-runs/kb-candidate`, không ghi đè collection đang chạy.
- [ ] Trích theo câu/đoạn giữ nguyên số, đơn vị, ngoại lệ; nếu không đủ bằng chứng cho câu hỏi, giữ NO_SOURCE/HITL. Đối chiếu lỗi số liệu với nguồn trước khi đổi keyword kỳ vọng.
- [ ] Chạy `python -m pytest tests/test_agents/test_rag_quality.py tests/test_agents/test_rag_node.py -q -p no:cacheprovider --basetemp=.test-runs/quality-task3`; đánh giá RAG dev độc lập.

**Nghiệm thu:** Có giải thích từng lỗi retrieval/generation; mục tiêu trích dẫn ≥85% trên tập đã review; không tăng điểm bằng chấp nhận sai model, gán citation giả hoặc đoán thông số.

### Task 4 — Giảm độ trễ và kiểm soát lỗi Gemini

**Files:** `agent_llm.py`, `llm.py`, `tracer.py`, `config.py`, `state.py`, `graph.py`, các node gọi model; mới `tests/test_agents/test_llm_budget.py`.

**Interfaces:**
- Giữ `structured_call(state: AgentState, prompt: str, schema: type[T]) -> T | None` để không làm vỡ caller.
- Ghi một event cho mọi attempt: `parsed`, `timeout`, `rate_limited`, `auth_error`, `provider_error`, `parse_error`, `circuit_open`, `budget_exhausted`; lỗi chỉ lưu loại và mã an toàn.
- State có ngân sách thời gian toàn lượt tính bằng đồng hồ monotonic, không đưa thời điểm monotonic vào dữ liệu persisted để tái sử dụng ở lượt sau.
- Cấu hình khởi điểm: deadline xử lý foreground 2,0 giây; LLM tối đa 1,2 giây mỗi lượt; tối đa một lời gọi foreground; không retry foreground. Đây là giá trị cần xác minh bằng profiling, không phải số đo hiện tại.
- Circuit breaker: mở 60 giây khi gặp 429; hết hạn cho một probe; không có thông tin quota thì không tự tạo hàng đợi dài. Việc cooldown nằm trong adapter, không ngủ trong request.

- [ ] Viết test RED bằng fake clock/provider: một call treo không quá budget; quota mở circuit, lượt kế tiếp không gọi provider; raw exception/key không vào trace; mọi attempt có reason; emergency không gọi model dù circuit đang đóng.
- [ ] Chạy test xác nhận RED.
- [ ] Triển khai deadline và timeout phía SDK, `max_retries=0`; phân loại lỗi và cancellation; cache client/Chroma khởi tạo an toàn để tránh tải lại mỗi lượt.
- [ ] Phân bổ model có chọn lọc: triage quy tắc đủ chắc thì không gọi LLM; brief dùng facts/template; ưu tiên RAG generation khi cần và còn budget. Không tạo summary LLM trên đường phản hồi khẩn cấp.
- [ ] Nếu provider không thể trả trong budget, dùng lời đáp extractive đã được kiểm chứng hoặc NO_SOURCE; không tăng deadline để che lỗi latency. Đo tỷ lệ parsed theo số attempt, tách attempt skipped và fallback.
- [ ] Chạy `python -m pytest tests/test_agents/test_llm_budget.py tests/test_agents/test_agent_llm.py -q -p no:cacheprovider --basetemp=.test-runs/quality-task4`; kiểm tra hai phiên đồng thời không tạo retry storm.

**Nghiệm thu:** Latency toàn lượt ≤2,5 giây trung bình trên workload thống nhất; đường dự phòng đạt KPI chất lượng. Báo cáo thêm p50/p95 và coverage Gemini. Nếu model gần như không trả thành công, chỉ xác nhận cấu hình hybrid đạt, không nhận là Gemini thuần đạt.

### Task 5 — Tập nghiệm thu độc lập và chốt kết quả

**Files:** mới `eval/datasets/agent_acceptance_v2.jsonl`, `eval/results/quality-v2/`; runner/evaluator, `prompts/version_log.csv`, hướng dẫn, báo cáo tiếng Việt.

**Interfaces:** Dataset giữ các trường label hiện có; thêm `kind`, `split`, `rationale`, `source_version`, và `expected_behavior` cho hội thoại nhiều lượt. Chỉ dataset đã được rà soát mới dùng làm cổng nghiệm thu.

- [ ] Viết test RED cho chuẩn hóa cách viết số/đơn vị tương đương: `160.000 km` và `160000 km` được so sánh đúng; số khác không được chấp nhận. Không bỏ kiểm tra nguồn khi thêm chuẩn hóa từ khóa.
- [ ] Bổ sung tối thiểu 60 tình huống triage và 30 RAG; trong đó ít nhất 10 critical, 20 RAG có nguồn, 10 RAG cần NO_SOURCE/từ chối. Tách tập dev với tập nghiệm thu chưa dùng chỉnh prompt; không đưa case test vào ví dụ prompt.
- [ ] Trong triage bổ sung, có ít nhất 10 hội thoại nhiều lượt qua bridge/API: sửa facts, đã hỏi hai lần, Guest hết lượt gặp emergency, staff đã In Progress, explicit case sai quyền và lỗi lưu DB. Báo cáo nhóm này riêng, không trộn câu-turn vào mẫu số single-turn mà không ghi rõ.
- [ ] Rà soát label và nội dung kỹ thuật bằng nguồn/ADR; đánh giá thủ công đúng ngữ nghĩa, điều kiện và citation cho các câu trả lời có nguồn. Model judge nếu dùng chỉ hỗ trợ, không tự quyết định acceptance.
- [ ] Chạy toàn bộ regression với thư mục temp mới: `python -m pytest tests/ -q -p no:cacheprovider --basetemp=.test-runs/quality-acceptance-01`; Ruff trên các file sửa; `git diff --check`. Không yêu cầu tổng số test giữ ở 82 vì sẽ có test mới.
- [ ] Chạy offline → provider_failure → online trên cùng tập, cùng KB; tạo output riêng, không ghi đè baseline. Warm-up được ghi rõ; latency request bao gồm chờ hàng đợi thực, không bao gồm thời gian nghỉ giữa các request do runner áp dụng quota.
- [ ] Chạy online với pacing lấy từ quota thực đã xác minh. Ghi timeout/rate-limit/parse rate và chi phí nếu có dữ liệu; chưa có thì N/A. Không thực hiện thêm nhiều run trả phí khi lần đầu còn lỗi cơ bản.
- [ ] Lập bảng PASS/FAIL cho từng KPI và từng mode, bảng case chuyển fail→pass và pass→fail, metric trước/sau thay nhãn. Online run không đủ coverage model vẫn báo fallback thật và trạng thái integration chưa đầy đủ.
- [ ] Cập nhật báo cáo tiếng Việt và version log theo số đo thật. Nếu sửa prompt tạo regression an toàn/quyền truy cập hoặc nguồn sai, rollback artifact/cấu hình liên quan và giữ báo cáo thất bại.

**Nghiệm thu cuối:** Bảy KPI đạt trên tập đã review ở chế độ sản phẩm chọn dùng; tất cả safety/HITL bắt buộc và regression quyền truy cập đều đạt; không có lỗi mới bị che bằng đổi nhãn. Nếu yêu cầu là Gemini thuần, phải có một run đủ phản hồi model và đạt KPI riêng trước khi tuyên bố hoàn thành.

## 8. Trình tự, trách nhiệm và phụ thuộc

| Chặng | Công việc | Người/vai trò thực hiện | Đầu ra cần có trước chặng sau |
|---|---|---|---|
| A | Task 1 | AI/Backend phối hợp người quản lý eval | Audit, schema đo lường, nhãn cần adjudication |
| B | Task 2 | AI/Backend, người quyết định chính sách | Triage/routing đúng, regression safety/HITL |
| C | Task 3 | Data/RAG phối hợp AI | Evidence đủ, candidate KB đã xác minh |
| D | Task 4 | AI/Backend, người quản lý quota | Deadline, circuit breaker, trace lỗi đầy đủ |
| E | Task 5 | Người quản lý eval/reviewer độc lập | Tập mới, báo cáo ba chế độ, quyết định acceptance |

Lập tập nghiệm thu và rà soát nguồn có thể chuẩn bị sớm; không dùng nội dung nghiệm thu để chỉnh logic. Thực thi từng task trong phiên hiện tại phù hợp vì chia sẻ state, evaluator và graph; chỉ cân nhắc giao việc độc lập khi đã chốt hợp đồng.

Chưa đưa ra lịch hoàn thành cố định: phụ thuộc thời gian rà soát nhãn, xác minh nội dung chính thức và quota online. Mỗi chặng kết thúc bằng sản phẩm đo được; quota bị giới hạn không chặn cải thiện offline hoặc kiểm thử provider_failure.

Các task có thể tạo commit riêng khi bước tích hợp được yêu cầu. Kế hoạch này không tự commit, merge, push hay triển khai API.

## 9. Các cổng dừng và quyết định còn cần chốt khi thực thi

- Nếu nhãn chưa thống nhất với ADR, vẫn sửa lỗi độc lập và báo cáo v1, nhưng không xác nhận KPI policy-sensitive trên bản nhãn chưa review.
- Nếu nguồn thiếu dữ kiện chính thức, giữ NO_SOURCE và ghi thiếu coverage; không thay expected answer bằng kiến thức chưa verify.
- Nếu candidate retrieval/embedding tốt hơn trên dev nhưng gây sai model hoặc sai nguồn, không đưa vào cấu hình sản phẩm.
- Nếu quota chưa cho phép online đủ coverage, nghiệm thu offline/provider_failure riêng và ghi online chưa đủ bằng chứng.
- Phạm vi hiện tại là chất lượng backend Agent/eval. Production auth, danh bạ điểm dịch vụ thật, Vision/OCR và triển khai hạ tầng là các hạng mục tích hợp riêng; không suy ra chúng đã đạt từ báo cáo này.

## 10. Checklist tự rà soát kế hoạch

- [x] Có task cho cả bảy KPI và giới hạn các bài kiểm thử hiện tại.
- [x] Tách bằng chứng đã xác nhận khỏi giả thuyết về dữ liệu/retrieval/provider.
- [x] Có file, interface, test RED/GREEN và điều kiện nghiệm thu cho từng task.
- [x] Giữ baseline, không dùng đổi nhãn hay giảm safety để tăng điểm.
- [x] Có coverage cho năm failure mode trong Review Focus.
- [x] Không coi quota/đổi model là lời giải cho toàn bộ lỗi chất lượng.
- [x] Không tự triển khai thay đổi mã sản phẩm trong bước lập kế hoạch.

**Tài liệu đối chiếu:** Báo cáo tiếng Việt `eval/results/bao-cao-danh-gia-agent-2026-10-03.md`; dữ liệu baseline `eval/results/agent/agent_results.json` và `eval/results/agent-online/agent_results.json`.
