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
