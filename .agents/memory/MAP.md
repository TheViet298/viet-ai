# P-142 — Structural Memory

> Bản đồ này chỉ giúp tìm đúng nguồn; không chứng minh module đang hoạt động. Xác nhận đường dẫn trong checkout nếu thư mục thay đổi.

## Chọn nguồn theo loại task

| Task | Bắt đầu ở | Nguồn chuẩn kế tiếp |
|---|---|---|
| Product/scope/user journey | `docs/product/` | `problem-and-mvp-scope.md`, `user-flows.md`, ADR phù hợp |
| Kiến trúc/luồng agent | `src/agents/`, `src/services/` | `docs/architecture/agent-workflow.md`, `langgraph-state-and-guardrails.md`, `system-overview.md`; xác nhận code/test |
| API/backend/data/auth | `src/api/`, `src/models/`, `src/services/`, `src/db.py` | `docs/architecture/api-contract.md`, `data-model.md`, `auth-and-rbac.md`; xác nhận schema/route/test |
| Web UI/customer/staff | `frontend/src/` | `docs/product/user-flows.md`, `docs/design/screen-spec.md`, `docs/design/ui-flow.md`; xem component/page thực tế |
| Prompt/triage/RAG | `prompts/`, `src/agents/`, `src/services/` | Prompt tương ứng, `docs/architecture/triage-and-hitl-rules.md`, `rag-and-data-sources.md`; so với test |
| Ảnh taplo/ngoại thất | `src/services/dashboard_vision_service.py`, `dashboard_warning_service.py`, `vehicle_vision_service.py`, `vision/`, `image_routing.py` | ADR-004, `docs/data-sources.md`, tài liệu vision liên quan; kiểm tra model/context/authorization trong code và test |
| Đánh giá/chất lượng | `eval/`, `tests/` | `eval/datasets/README.md`, `docs/eval_evidences.md`, đúng report trong `eval/results/`; phân biệt benchmark, target và kết quả |
| Cài đặt/chạy | `README.md`, `docs/setup-guide-linux-windows.md`, `docs/guide/` | Chỉ đọc bước liên quan môi trường/task |
| AI logging/hooks | `.agents/rules/`, `.agents/workflows/`, `scripts/` | Rule/workflow cụ thể; `.agents/**` có giới hạn branch ở `../rules/git-branch-restriction.md` |

## Bản đồ nhanh

- `src/`: FastAPI, agent, services và model dữ liệu.
- `frontend/`: Next.js; `frontend/src/features/chat` là customer chat, `features/console` là staff console, `features/landing` là landing.
- `docs/`: product, design, decisions, architecture, guides và evidence.
- `prompts/`: prompt theo tác vụ agent; prompt là đầu vào cấu hình, không phải bằng chứng về runtime.
- `eval/`: datasets, kết quả và báo cáo đánh giá; kết quả cũ không khẳng định trạng thái code hiện tại.
- `dataset/`: dữ liệu dự án; kiểm tra README/giấy phép/nguồn trước khi tái sử dụng ảnh hoặc nhãn.
- `tests/`: bằng chứng kiểm thử; chạy test liên quan khi được yêu cầu hoặc cần xác minh thay đổi.
- `.agents/`: rules, skills, workflows và memory dành cho agent. Tuân thủ giới hạn branch trong rule trước khi stage/commit/push.

## Bằng chứng trạng thái có sẵn

`docs/eval_evidences.md` ghi nhận Gate 2 là kiểm tra API backend local, chưa bao gồm UI. Snapshot đó có TC01–TC03 còn lỗi, TC04 đạt trong phạm vi tiếp nhận, TC05 đạt sau khi gửi lại. Đây là lịch sử tại đợt kiểm thử, không phải kết quả hiện tại; đọc report gốc khi cần trích dẫn.
