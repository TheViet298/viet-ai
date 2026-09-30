# Báo cáo chỉnh sửa metadata RAG, liên kết đánh giá và tiến độ WORKLOG

**Ngày:** 2026-09-27

**Phạm vi:** Tài liệu nguồn RAG, ví dụ API/demo, báo cáo đánh giá và đối chiếu tiến độ trước 26/09/2026. Không thay đổi mã nguồn ứng dụng.

## Đã chỉnh sửa

| File | Nội dung |
| --- | --- |
| [Đặc tả nguồn RAG](architecture/rag-and-data-sources.md) | Đồng bộ tên tài liệu `SRC-APP-001` với tiêu đề trên trang VinFast; thay lỗi `2020 OK (200)` bằng trạng thái HTTP chưa xác nhận (`null`); bỏ danh sách model chưa được trang nguồn xác nhận; cập nhật ngày kiểm tra nội dung và ghi rõ giới hạn kiểm tra. Bổ sung thứ tự triển khai: Flow 1 trước, FAQ/RAG hoàn chỉnh sau. |
| [API contract](architecture/api-contract.md) | Đồng bộ ví dụ citation với metadata nguồn mới. |
| [Kịch bản demo](product/demo-scenarios.md) | Đồng bộ tên nguồn và ngày kiểm tra nội dung trong Flow 3. |
| [Báo cáo đánh giá](../eval/results/report.md) | Sửa link dataset từ đường dẫn `file:///` trên máy cá nhân thành đường dẫn tương đối trong repo. Ghi đúng trạng thái chưa chạy baseline và đặt đánh giá FAQ/RAG sau Flow 1. |
| [WORKLOG](../WORKLOG.md) | Đối chiếu đủ 16 đầu việc ngày 20, 23, 24/09 với bằng chứng, giới hạn xác minh và trạng thái đề xuất; điều chỉnh các nhãn `Done` quá rộng, đặc biệt Mentor Duty và form khảo sát. |
| [JOURNAL](../JOURNAL.md) | Đồng bộ các checklist và nhận định tuần với kết quả kiểm tra: đầu ra tài liệu khác tính năng triển khai, các việc ngoài repo chưa được xác minh, các mục còn mở được giữ ở trạng thái chưa xong. |

## Đã tạo mới

- File báo cáo này: `docs/change-report-2026-09-27-rag-metadata.md`.

## Căn cứ và giới hạn

- [Trang hướng dẫn ứng dụng VinFast cho ô tô điện (Phần 2)](https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast) đọc được qua trình duyệt và có các mục về trạng thái sạc, đặt lịch dịch vụ và theo dõi sửa chữa. Trang chưa xác nhận rõ phạm vi cho từng model trong danh sách cũ.
- Lệnh kiểm tra HTTP trực tiếp từ môi trường phát triển trả `403`; vì thế không khẳng định mã HTTP hiện tại là `200`. Trường `status_code` được để `null` cho đến khi pipeline nạp nguồn kiểm tra được mã HTTP trong chính môi trường chạy của nó.
- Metadata nguồn đã được chuẩn bị; ứng dụng chưa có pipeline FAQ/RAG hoàn chỉnh. Flow 1 (`Charging/Battery` từ tiếp nhận đến Staff Review và cập nhật trạng thái) vẫn là ưu tiên triển khai trước.

## Kết quả kiểm tra

- Đường dẫn tương đối từ `eval/results/report.md` đến `eval/datasets/triage_cases_v1.jsonl` tồn tại.
- Các ví dụ `SRC-APP-001` được chỉnh sửa thống nhất tiêu đề, ngày kiểm tra, `status_code` và `applicable_models`.
- Hai ví dụ JSON trong đặc tả nguồn và ví dụ citation trong API contract parse được; `git diff --check` không phát hiện lỗi khoảng trắng.

## Bổ sung Task 1: đối chiếu tiến độ và bằng chứng

Bảng trong [WORKLOG](../WORKLOG.md) có một dòng cho mỗi đầu việc trước 26/09/2026: **16 mục**, gồm 7 mục có bản thảo/tài liệu/quyết định kiểm tra được, 4 mục chỉ hoàn thành một phần hoặc cần đồng bộ, 3 mục WIP và 2 mục chưa thể xác minh bằng repo. Những nhãn này phản ánh đầu ra trong repo, không xác nhận khảo sát gốc, thời gian làm việc hoặc việc nộp bài trên hệ thống khác.

Hai mục chưa xác minh là bản form khảo sát và Mentor Duty. Không thêm bản khảo sát, dữ liệu người tham gia hoặc biên nhận nộp bài vào repo. Nếu nhóm muốn lưu các tài liệu đó, cần xin phép trước và kiểm tra, loại bỏ dữ liệu cá nhân phù hợp.

Các phần chất lượng còn mở: README chính vẫn là template, chưa thấy backlog/checklist Gate G1 riêng; screen spec còn `name`/`phone` trái với quy tắc không PII thật; dataset mới có 12/40 ca mục tiêu; agent guardrails và Case lifecycle API chưa triển khai. Việc viết scope, rule matrix và API contract được ghi nhận là hoàn thành bản thảo, không phải Flow 1 E2E đã chạy.

## T1 — Kiểm tra hoàn tất đối chiếu WORKLOG (2026-09-28)

- **Mục tiêu:** Xác nhận 16 đầu việc trước 26/09 có trạng thái và bằng chứng phù hợp; phân biệt đầu ra trong repo, bản thảo và sự kiện cần xác nhận ngoài repo.
- **File đã chỉnh sửa:** `WORKLOG.md`, `JOURNAL.md` và báo cáo này trong commit `bd68284`; lần kiểm tra này chỉ bổ sung mục T1 vào báo cáo.
- **Thay đổi chính:** Bảng đối chiếu trong WORKLOG liên kết đầu ra cho các mục có tài liệu, giữ các mục thiếu đầu ra ở trạng thái một phần/WIP/chưa xác minh. JOURNAL ghi rõ giới hạn của khảo sát và việc nộp Mentor Duty. Không tự xác nhận sự kiện ngoài repo.
- **Lệnh kiểm tra và kết quả:** `git show a90ed60:WORKLOG.md` cho thấy 16 dòng gốc, trong đó 13 dòng ghi `Done` và 3 dòng ghi `WIP`; `rg -n '^(\| (0[1-9]|1[0-6]) \|)' WORKLOG.md` tìm đủ 16 dòng đối chiếu; `git show --check --oneline bd68284` và `git diff --check` đều không báo lỗi khoảng trắng; `git ls-files` và tìm kiếm nội dung repo xác nhận có các tài liệu được liên kết, nhưng không thấy form khảo sát, biên nhận Mentor Duty hay backlog/checklist Gate G1 riêng. Không chạy test ứng dụng vì T1 chỉ rà tài liệu.
- **Giới hạn còn lại:** Nghiên cứu đối chiếu VinFast, dữ liệu khảo sát gốc n=4, thời điểm kiểm tra URL ngày 24/09 và việc nộp Mentor Duty không thể kiểm chứng bằng repo. README/backlog/checklist Gate G1 chưa đủ đầu ra; các bản thảo chưa chứng minh tính năng chạy. Trạng thái này không kết luận công việc ngoài repo chưa diễn ra.
- **Cần nhóm xác nhận/cung cấp:** (1) nội dung Mentor Duty log và biên nhận hoặc đường dẫn submission kèm thời điểm nộp; (2) bản câu hỏi hoặc đường dẫn form khảo sát; (3) số liệu khảo sát n=4 đã ẩn danh cùng phương pháp thu thập/tổng hợp để đối chiếu các khẳng định trong scope; (4) backlog/WBS và checklist Gate G1 đã dùng, nếu được lưu ngoài repo; (5) nguồn/ghi chú đối chiếu tính năng VinFast và bằng chứng kiểm tra URL ngày 24/09, nếu muốn giữ các khẳng định đó là đã xác thực; (6) xác nhận của người phụ trách về việc chốt scope Gate G1. Chỉ cập nhật trạng thái tương ứng sau khi nhóm kiểm tra các bằng chứng này; không đưa dữ liệu cá nhân lên repo.

> một số mô tả về role trên repo chung chưa update, nhưng không quá quan trọng, hãy bắt đầu làm các task khác.

## T3 — Case lifecycle API and audit (2026-09-29)

- **Objective:** Implement the customer chat/status/actions and staff queue/detail/actions flow under the T2 proposal confirmed in chat, with session, message, case, brief, and audit storage; enforce status transitions and keep internal brief fields out of customer responses.
- **Modified files:** `src/api/routes.py`, `src/models/schemas.py`, `src/main.py`, `src/config.py`, `tests/test_api/test_routes.py`, this report, and the explicitly authorized new module `src/services/case_store.py`. No `data/app.db` was created.
- **Key changes:** Added an in-memory SQLite case store with session, case, message, case brief, and audit tables. Added bounded clarification, case creation, customer status/actions, staff queue/detail/actions, session ownership checks, staff bearer-token checks, action validation, explicit transition rules, and consistent API error envelopes. Staff identity comes from server configuration rather than request bodies. Customer responses omit brief/confidence/internal analysis. Staff rerouting persists the selected team. Read and state-changing operations are recorded in audit for an existing case.
- **Test commands and results:** `PYTHONDONTWRITEBYTECODE=1 /tmp/p142-test-YfxrIF/venv/bin/pytest -p no:cacheprovider tests/test_api/test_routes.py -q` passed **8 tests**. Tests use a separate in-memory SQLite store and mock staff token. `git diff --check` found no whitespace errors. The first test attempt could not start because Python dependencies were absent; minimal test dependencies were installed into a temporary `/tmp` virtual environment without changing repository files.
- **Remaining limitations:** The default database is in memory, so data is lost on process restart; file-backed SQLite is opened only if a database file already exists. This work does not create `data/app.db`. The rule-based demo triage is not an evaluated AI classifier; FAQ/RAG is not implemented. The T2 proposal file still says “not approved” because updating that document is outside this task's allowed files, although the user confirmed it in chat. Free-text PII screening catches common email/phone patterns but cannot guarantee removal of every personal detail.
- **Human review or decision:** Configure a strong `STAFF_API_TOKEN` outside the repository and verify unauthenticated/wrong-token staff requests are denied. Confirm whether a shared demo token and configured `STAFF_ID` are acceptable; real staff audit attribution requires individual authentication and role checks. Verify that customer session IDs cannot be guessed or reused across users in the deployed client, and manually test cross-session case access. Decide whether to authorize creation of `data/app.db` for persistent trials and update the T2 contract documents when document edits are permitted. Review the demo triage wording and routing before use with real customers.

## T4 — Local Codex prompt and reply logging (2026-09-29)

- **Objective:** Capture each Codex prompt and available final reply in a local ignored log, and exercise a small Python file while checking the logging setup.
- **Modified files:** `.codex/hooks.json`, `scripts/log_hook.py`, `hello-world.py`, and this report. Log output target: `.ai-log/session.jsonl`, ignored by Git and not staged.
- **Key changes:** Hook commands resolve scripts and the log directory from the Git root. The Codex logger stores the full prompt on `UserPromptSubmit` and the full available `last_assistant_message` on `Stop`, returns valid empty JSON to Codex, and creates the log with mode `0600`. Added a minimal `hello-world.py` that prints `Hello, world!`.
- **Test commands and results:** `PYTHONDONTWRITEBYTECODE=1 python3 hello-world.py` printed `Hello, world!`. A synthetic hook integration test from a repository subdirectory wrote prompt and reply events to `/tmp`, preserved a 1,201-character prompt and Unicode reply, and verified the log file mode was `0600`. `python3 -c 'import json; from pathlib import Path; json.loads(Path(".codex/hooks.json").read_text())'` and `git diff --check` passed. The real `.ai-log/session.jsonl` is not present because the changed project hooks have not yet been trusted in Codex; automatic capture is therefore still awaiting activation.
- **Remaining limitations:** Hook execution is conditional on project trust. Stop events contain the latest assistant message only when Codex provides it. `.ai-log/*.jsonl` remains ignored, so the prompt and reply contents are local and are not included in GitHub commits.
- **Human review or decision:** Review and trust the project hooks in Codex `/hooks`, then start a new session and verify one prompt and its final reply appear in `.ai-log/session.jsonl`. Confirm the test script should remain in the repository after the smoke test.

## ai-log
summarise what have you done  

The previous task was missing because Codex capture had missed its prompts. The pre-push hook only recovered Antigravity logs, so it reported “No logs to submit.”

I have:

- Recovered **1,011 missing activity records** from four repository sessions.
- Added Codex recovery, broader hooks, and a watcher that captures every 3 seconds and uploads approximately every 15 seconds.
- Fixed upload batching, retry handling, and tool payload compatibility.
- Passed **12 regression tests**.
- Verified server acknowledgment for **44 records**, with zero repository mismatches.

The remaining backlog is being retried. I haven’t verified that all records appear on Phoenix, or confirmed the final push completed—the last command was interrupted.

## T5 — Khôi phục và sửa luồng AI logging (2026-09-30)

### Nguyên nhân và phạm vi

Kiểm tra `.ai-log/archive/2026-09-30.jsonl` cho thấy archive ban đầu chỉ có **6 bản ghi**, không chứa các prompt của task tách dataset. Khi push task đó, không có log đang chờ nên hook báo `No logs to submit`. Pre-push lúc ấy chỉ quét lại transcript Antigravity, chưa có bước khôi phục transcript Codex. Bản sửa trước đó mới xử lý việc gửi log có sẵn và đọc cấu hình `.env`; chưa giải quyết việc Codex bỏ sót capture.

Các prompt bị thiếu vẫn tồn tại trong transcript Codex cục bộ. Chưa xác định chắc chắn vì sao native hook không chạy cho những lượt đó; không kết luận project chưa trust hoặc hooks bị tắt chỉ từ việc thiếu log. Bản sửa bổ sung đường khôi phục độc lập với native hook, thay vì chỉ dựa vào lúc push.

### File đã chỉnh sửa trong task logging

| File có sẵn | Chi tiết thay đổi |
| --- | --- |
| `.codex/hooks.json` | Giữ hook prompt/Stop và bổ sung `PostToolUse`, `SessionStart`, `SessionEnd`, `Interrupt`, `PreCompact`, `PostCompact`; điều chỉnh timeout theo sự kiện. |
| `scripts/log_hook.py` | Ghi đầy đủ prompt và phản hồi Codex khi payload cung cấp; ghi hoạt động công cụ và vòng đời session; bổ sung ID chống trùng, khôi phục từ transcript được cung cấp, gửi log tại Stop và trả JSON hợp lệ cho Codex. Xử lý trường hợp không tìm được Git root. |
| `scripts/submit_log.py` | Đọc cấu hình bằng thư viện chuẩn; tách khóa capture/submission; chia batch tối đa 500 bản ghi với ngưỡng kích thước 256 KiB (một bản ghi lớn được giữ nguyên); timeout gửi 30 giây. Chỉ archive phần server xác nhận, giữ phần chưa gửi và khôi phục batch khi lỗi hoặc tiến trình bị ngắt. Lưu receipt; chuyển `tool_input`/`tool_response` có cấu trúc thành chuỗi JSON khi gửi để phù hợp schema ingestion. |
| `scripts/setup_hooks.sh` | Cài pre-push theo đường dẫn Git của repository/worktree; chạy Codex recovery, Antigravity recovery rồi gửi toàn bộ batch. Thêm tùy chọn `--watch` để khởi động capture và submission liên tục. Hook vẫn không chặn push khi gửi log thất bại. |
| `scripts/setup_hooks.ps1` | Bổ sung cùng luồng khôi phục/gửi log trên Windows và tùy chọn `-Watch`. Chưa chạy kiểm thử thực tế trên Windows. |
| `.gitignore` | Bỏ qua toàn bộ nội dung `.ai-log/`, ngoại trừ `.gitkeep`, bao gồm transcript đã capture, archive, receipt, khóa và thông tin watcher. |
| `README.md` | Mô tả native hook, recovery và watcher; hướng dẫn chạy lại sau khi khởi động máy, lệnh khôi phục/gửi thủ công, phạm vi dữ liệu được ghi và giới hạn của xác nhận HTTP 202. |

### File mới đã tạo trong task logging trước đó

Danh sách sau ghi nhận các file đã được tạo trong task sửa logging; lần cập nhật báo cáo này không tạo thêm file.

| File mới | Vai trò |
| --- | --- |
| `.codex/config.toml` | Bật feature hooks trong cấu hình Codex của project. Không tự thay đổi danh sách hash hook đã được người dùng trust. |
| `scripts/ai_log_store.py` | Các hàm dùng chung để tìm Git root, đọc `.env`, xác định thư mục log, khóa ghi, tạo ID ổn định, chống ghi trùng và che giá trị bí mật nhận diện được. |
| `scripts/log_codex.py` | Quét session/transcript thuộc repository này, khôi phục prompt, câu trả lời công khai, hoạt động công cụ và lượt bị ngắt; hỗ trợ `--auto`, `--dry-run`, `--transcript`, `--watch`, `--submit`. Watcher quét khoảng mỗi 3 giây và thử gửi khoảng mỗi 15 giây. Bỏ qua reasoning và chỉ dẫn system/developer. |
| `tests/test_ai_logging.py` | 12 kiểm thử hồi quy cho capture, Unicode/prompt dài, phạm vi repository, chống trùng, che bí mật, ghi đồng thời, batch/retry, khôi phục upload bị ngắt và chuyển payload công cụ sang schema server. |

Ngoài mã nguồn, quá trình chạy có sinh dữ liệu riêng trong `.ai-log/`: log chờ gửi, archive được bổ sung, receipt và file vận hành watcher. Các dữ liệu này bị Git ignore và không nằm trong commit. Không xóa file mã nguồn trong hai commit sửa logging.

### Kiểm tra và kết quả đã xác nhận

- `python3 -m unittest discover -s tests -p test_ai_logging.py -q`: **12 tests passed**. Các request trong test được mock; kết quả test không được tính là upload thật.
- Kiểm tra cú pháp Python, `bash -n scripts/setup_hooks.sh` và `git diff --check` đã chạy thành công trong quá trình sửa.
- Lần recovery đầu ghi thêm **1.011 bản ghi hoạt động** từ **4 session thuộc repository**, gồm prompt và hoạt động công khai; đây không phải 1.011 prompt.
- Server từng trả HTTP 422 vì `tool_response` có dạng cấu trúc, trong khi API yêu cầu chuỗi. Đã sửa phần chuyển đổi payload khi gửi và bổ sung kiểm thử giữ nguyên nội dung sau chuyển đổi.
- Tại mốc xác nhận trong phần tổng kết trước, receipt ghi **44 bản ghi đã gửi**, HTTP **202**: server báo **42 accepted**, **2 duplicates**, **0 mismatched_repos**. Bản ghi chưa gửi thành công được giữ để retry; chưa xác nhận toàn bộ backlog đã gửi hết.
- Đã cài lại Git pre-push và khởi động/restart watcher. Watcher cần được chạy lại sau khi khởi động máy; chưa cài dịch vụ tự khởi động cùng hệ điều hành.
- Hai commit trên `feature/ai-khoi`: `06c9d08` — khôi phục Codex và gửi log liên tục; `b023c90` — tương thích payload ingestion. Khi bắt đầu cập nhật báo cáo này, Git hiển thị branch đồng bộ với `origin/feature/ai-khoi`, nên bước push trước đó đã hoàn thành dù lượt trả lời bị ngắt.

### Giới hạn và trạng thái báo cáo

HTTP 202 xác nhận server đã tiếp nhận batch, không chứng minh mọi hoạt động đã xuất hiện trên [Phoenix AI logs, cohort-4](https://phoenix.note.transformerlabs.ai/ai-logs?cohort=cohort-4). Chưa xác minh đầy đủ dashboard bằng session đăng nhập. Native hook vẫn cần được Codex tải và duyệt cấu hình khi có thay đổi; recovery/watcher bổ sung khả năng ghi lại những sự kiện native hook bỏ sót. Định dạng transcript là nội bộ và có thể thay đổi; việc che bí mật dựa trên giá trị/pattern nhận diện được, không phải bảo đảm loại bỏ mọi dữ liệu nhạy cảm.

Lần cập nhật này chỉ bổ sung mục T5 vào `docs/change-report-2026-09-27-rag-metadata.md`, giữ nguyên nội dung có sẵn, không tạo hoặc xóa file và không commit/push báo cáo.
