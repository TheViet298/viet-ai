# Vận hành bản cải thiện chất lượng Agent

Triển khai local ngày 2026-10-03–04 trên branch `feature/agent-long`. Không commit, push hay triển khai hạ tầng. `.env` local dùng `CHROMA_PERSIST_DIR=./data/chroma-quality-v4`; kho `data/chroma` gốc được giữ để rollback. Không đưa API key vào tài liệu hoặc Git.

Backend giữ routing dùng chung cho triage/brief, yêu cầu chuyên viên cho sự cố và giao dịch cá nhân. Gemini gọi có chọn lọc, tối đa một attempt/lượt; không retry foreground. Deadline asyncio 1,2 giây cho model, budget từ intake 2 giây; SQLite và tầng HTTP chưa có cam kết thời gian toàn request trong mọi tình huống quá tải. SDK transport dùng tối thiểu 10 giây vì Gemini từ chối deadline ngắn; cancellation không kéo dài thời gian chờ foreground.

Kho candidate dùng `Xenova/multilingual-e5-small`, revision `761b726`, file `onnx/model_quantized.onnx` và `tokenizer.json` dưới `data/models/multilingual-e5-small`. Hash artifact thực trong `eval/results/quality-v2/kb-fingerprint.json`. Model khoảng 118 MB; thư mục `data/` không nằm trong Git. Dùng `huggingface_hub.snapshot_download` với repo/revision và `allow_patterns` hai file trên để tái tạo model. Cài dependencies từ `requirements.txt` trước khi build.

Tái tạo candidate riêng từ các snapshots hiện hữu, không ghi đè kho gốc:

```powershell
.\.venv\Scripts\python.exe scripts/refresh_agent_sources.py --multilingual data/chroma-quality-rebuild-base
.\.venv\Scripts\python.exe scripts/refresh_agent_sources.py --rewrite-source-sections data/chroma-quality-rebuild --from-candidate data/chroma-quality-rebuild-base
```

Build cần `data/processed/chunks.jsonl`, `data/raw/SRC-*.txt` và supplement tracked. Chỉ thay `CHROMA_PERSIST_DIR` sau khi so sánh regression, model/variant/year và nguồn. Để rollback local đặt lại `CHROMA_PERSIST_DIR=./data/chroma` rồi khởi động lại backend.

Refresh nguồn chính thức dùng:

```powershell
.\.venv\Scripts\python.exe scripts/refresh_agent_sources.py --verified-at 2026-10-04
```

Trình refresh ghi HTTP status thực và giữ bảng/heading. Lần này HTTP trực tiếp nhận 403; không phê duyệt catalog mới. Source URL khác registry chỉ được dùng nếu có bản xác minh exact URL/status/date hợp lệ. Kho candidate đang dùng snapshots cũ, không tuyên bố nội dung mọi nguồn đã cập nhật ngày 04/10.

Chạy eval dưới đây với `DATABASE_URL` riêng cho từng run và tắt cloud tracing. Các mode dùng cùng dataset/KB; mode online có thể fallback. Chế độ provider_failure mở circuit có chủ đích, không gọi API thật.

```powershell
.\.venv\Scripts\python.exe scripts/run_agent_eval.py --mode offline --dataset eval/datasets/agent_acceptance_v2.jsonl --output-dir eval/results/quality-v2/new-offline
.\.venv\Scripts\python.exe scripts/run_agent_eval.py --mode provider_failure --dataset eval/datasets/agent_acceptance_v2.jsonl --output-dir eval/results/quality-v2/new-provider-failure
.\.venv\Scripts\python.exe scripts/run_agent_eval.py --mode online --dataset eval/datasets/agent_acceptance_v2.jsonl --output-dir eval/results/quality-v2/new-online
.\.venv\Scripts\python.exe scripts/run_agent_multiturn_eval.py --output-dir eval/results/quality-v2/new-multiturn
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider --basetemp=.test-runs/new-verification
```

Bộ 90 ca có nhãn draft và đã được dùng chẩn đoán. `acceptance_approved=false` là chủ đích; cần tập độc lập được review và đủ model coverage trước nghiệm thu. RAG v1 còn thấp; danh bạ điểm dịch vụ, auth production, Vision/OCR và hạ tầng nằm ngoài phạm vi cải thiện này.

## Nâng cấp nền tảng RAG ngày 04/10/2026

Context budget dùng **byte UTF-8**, không phải token Gemini: `RAG_CONTEXT_MAX_BYTES=6000`, `AGENT_CONTEXT_MAX_BYTES=8000`. Các parent/mục được chọn nguyên văn. Quá budget có category `context_budget_exceeded`; prompt giữ system/policy/câu hỏi. `token_count` và tham số `max_tokens` chỉ là alias legacy đơn vị byte. Retrieval phân biệt `NO_SOURCE`, `UNAVAILABLE`, `ERROR`, `TIMEOUT`; failure chuyển chuyên viên, không tự dùng web hoặc thêm attempt LLM.

Candidate mới `data/chroma-rag-foundations-candidate` giữ 2.163 parent, index 2.168 child. Audit dùng E5 tokenizer thật: max 256 token tính cả `passage: ` và special tokens, 0 child quá giới hạn. Bốn parent quá dài được chia; parent nguyên văn lưu trong `parent-map.json`. Citation giữ `chunk_id` child và `parent_chunk_id`; registry/model/variant/distance/an toàn/budget kiểm tra trên bằng chứng parent.

Build và audit từ kho cũ đã có, không tải hoặc phê duyệt nguồn mới:

```powershell
.\.venv\Scripts\python.exe scripts/build_rag_candidate.py --source data/chroma-quality-v4 --output data/chroma-rag-foundations-rebuild --audit-only
.\.venv\Scripts\python.exe scripts/build_rag_candidate.py --source data/chroma-quality-v4 --output data/chroma-rag-foundations-rebuild
```

Builder từ chối output trùng/lồng source hoặc output đã có dữ liệu. Nếu build bị ngắt, chọn output mới để thử lại; không dùng index chưa có manifest/mapping hoàn chỉnh. Manifest ghi source content, model, tokenizer, child records và parent map hashes, dimension/metric/chunking version. Encoder strict từ chối passage quá 256; encoding legacy còn truncation tương thích, audit riêng chỉ ra các parent quá dài.

Chạy eval với database riêng cho từng run:

```powershell
$env:DATABASE_URL='sqlite:///./.test-runs/rag-foundations-eval.db'
$env:CHROMA_PERSIST_DIR='./data/chroma-rag-foundations-candidate'
.\.venv\Scripts\python.exe scripts/run_agent_eval.py --offline --dataset eval/datasets/agent_acceptance_v2.jsonl --output-dir eval/results/rag-foundations/offline
.\.venv\Scripts\python.exe scripts/check_rag_quality.py --engineering --output eval/results/rag-foundations/engineering.json
.\.venv\Scripts\python.exe scripts/check_rag_quality.py --report eval/results/rag-foundations/offline/agent_results.json --output eval/results/rag-foundations/acceptance-gate.json
```

Engineering gate là fixture tổng hợp public, không cần KB/model local/API thật; CI upload report kể cả khi thất bại. Acceptance CLI exit 0 khi report đủ điều kiện, 1 khi chất lượng/nhãn/provenance/coverage thiếu, 2 khi input malformed. `eval/rag_gate_config.json` là ngưỡng dự án, không phải chuẩn RAGAS. Report draft hiện tại **phải fail acceptance** vì nhãn chưa approved và thiếu expected evidence IDs; Recall/Precision còn `null/unavailable`, không tạo số giả.

`label-review.json` liệt kê nhãn evidence/facts cần kiểm tra. `dataset-split.json` chia ID ổn định development/holdout; bộ 90 ca đã dùng chẩn đoán nên partition này chưa thành holdout nghiệm thu độc lập. Cần bổ sung/review tập mới và đóng băng holdout trước điều chỉnh ngưỡng. Raw IDs trước/sau budget trong report hỗ trợ adapter RAGAS/judge về sau; fact/source matching deterministic không chứng minh Faithfulness ngữ nghĩa.

Eval hỗ trợ `--partition development` và `--partition holdout` để chỉ chạy/aggregate nhóm được chọn; mặc định `all` giữ khả năng so sánh diagnostic hiện hữu. Report ghi partition và giới hạn độc lập. Không dùng metric nhóm holdout để chỉnh ngưỡng; tập đã xem trước cần thay bằng tập mới trước nghiệm thu.

So sánh offline cùng 90 ca draft: baseline trước thay đổi grounded citation 85%; code mới + kho cũ 90%; code mới + candidate 90%. Safety recall/no-source compliance đều 100%, không ca nào đổi safety/routing/review/grounded khi chuyển kho cũ sang candidate. Candidate mean 53ms, p95 68ms (warm local offline); đây không phải benchmark tải hay SLA production.

Sau khi chọn local, đặt `.env` `CHROMA_PERSIST_DIR=./data/chroma-rag-foundations-candidate` và khởi động lại backend để settings/cache dùng đường dẫn mới. Rollback đợt này về `./data/chroma-quality-v4`, khởi động lại; cả hai kho được giữ nguyên. Đây là chuyển cấu hình local, chưa có atomic alias/blue-green hoặc deployment production.

Backlog: source lifecycle/freshness và thu hồi, auth/ownership/rate limiting thực, BM25/RRF/reranker benchmark, load/cost/async telemetry, cache có invalidation và rollout atomic. Chỉ thêm kỹ thuật nâng cao theo nhóm lỗi đo được.
