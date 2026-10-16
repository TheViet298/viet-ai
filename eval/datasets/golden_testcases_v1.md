# Golden testcase v1 — Agent dịch vụ VinFast

Ngày tạo: 2026-10-14. Dữ liệu: `golden_testcases_v1.jsonl` (JSONL UTF-8, 60 case).

| Nhóm | Số case | Phạm vi |
| --- | ---: | --- |
| safety | 15 | 10 nguy hiểm hiện tại; rùa vàng thông thường; phủ định, giả định và quá khứ |
| triage | 20 | Charging, Service, Complaint; priority; routing; Staff Review; từ chối can thiệp cao áp |
| rag | 15 | 5 trả lời theo nguồn giả lập; 8 fallback/nguồn không hợp lệ; 2 ngoài phạm vi |
| multiturn | 10 | 4 sửa dòng xe; giới hạn hỏi; 3 nâng CRITICAL; PII; không bịa mã lỗi |

## Nhãn và phạm vi

Nhãn dựa trên `docs/architecture/triage-and-hitl-rules.md`, đặc biệt bảng hard rules, hai lượt clarification và bắt buộc HITL. Quy tắc phân biệt phủ định/giả định/quá khứ và kiểm định citation tham chiếu thêm các regression hiện có trong `tests/test_agents/` và registry `docs/data-sources.md`. `rationale` ghi lý do của từng ca.

Tất cả nhãn mang `draft_policy_review`: đây là bộ tham chiếu đề xuất cần người phụ trách duyệt độc lập, chưa phải bộ nghiệm thu đã phê duyệt. Những câu hội thoại tương tự regression đã có không tạo ra holdout độc lập. Không nạp đáp án hoặc snippet của bộ này vào KB, train hay fine-tune.

## Schema

- `id`: ID ổn định `GOLD-<CATEGORY>-NNN`.
- `category`, `label_status`, `policy_ref`, `rationale`: nhóm, trạng thái duyệt và căn cứ.
- `retrieval`: kết quả công cụ tra cứu giả lập cho ca đó; mỗi lần đọc dùng bản sao riêng.
- `turns`: danh sách tuần tự các object gồm `input` và `expected`.
- `expected`: so sánh chính xác các trường đầu ra; đường dẫn dùng dấu chấm, ví dụ `case_brief.vehicle_model` hoặc `citations.0.source_id`.
- `nonempty`: các trường phải có giá trị, ví dụ hồ sơ, case ID hoặc quick replies.
- `contains`: các đoạn bắt buộc theo từng trường, không phân biệt hoa thường.
- `forbidden`: các chuỗi không được xuất hiện trong toàn bộ đầu ra, dùng cho PII và cam kết sai.

## Chạy

Từ thư mục gốc trên PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_eval/test_golden_cases.py -q --tb=short --basetemp=.test-runs/golden-local -p no:cacheprovider --junitxml=eval/results/golden-v1/offline-baseline.xml
```

Chỉ kiểm tra dữ liệu và bộ so sánh:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_eval/test_golden_cases.py -k "dataset_contract or contract_detects" -q --basetemp=.test-runs/golden-contract -p no:cacheprovider
```

Chỉ chạy một nhóm: thêm `-k GOLD-SAFETY`, `-k GOLD-TRIAGE`, `-k GOLD-RAG` hoặc `-k GOLD-MULTITURN` vào lệnh chạy. Có 60 test tình huống và 2 test kiểm tra bộ dữ liệu/bộ so sánh. Lệnh trả exit code khác 0 nếu có ca FAIL; không dùng xfail để che lệch nhãn.

Harness gọi `process_chat_message` thật, chạy graph thật và lưu từng lượt vào SQLite riêng của pytest. Fixture dự án tắt LLM và Langfuse, đồng thời chuyển database/Chroma sang thư mục tạm. Harness chỉ thay kết quả `rag_service.retrieve`, không thay output graph hay logic phân loại. Không sử dụng database khách hàng.

Metadata HTTP 200, ngày xác minh và URL trong `retrieval.citations` là giá trị mô phỏng khớp registry phiên bản tại thời điểm tạo để kiểm tra validation; không phải kết quả HTTP mới. Snippet là nội dung giả lập, không phải trích dẫn chính sách mới được xác minh. Ca thành công kiểm tra đủ dữ kiện/điều kiện trong câu trả lời; ca thất bại kiểm tra fallback, Staff Review và loại citation. ERROR/TIMEOUT được mô phỏng bằng trạng thái trả về, không đo độ trễ hoặc tạo lỗi mạng thực.

Runner `scripts/run_agent_eval.py` dùng schema single-turn khác và không đọc trực tiếp bộ này. Chạy bộ golden bằng pytest như trên. Chưa đánh giá HTTP/UI, guest quota, ảnh/Vision, LLM online, chất lượng vector retrieval hoặc chính sách thương mại hiện hành.

## Đọc baseline

`eval/results/golden-v1/report.md` và XML ghi kết quả chạy thực. Nếu implementation khác chính sách, giữ nhãn kỳ vọng và điều tra implementation/chính sách; không đổi nhãn chỉ để đạt PASS. Kết quả offline contract không đại diện cho độ chính xác toàn bộ hệ thống hoặc chất lượng KB production.

## Đánh giá trên Langfuse Cloud

Runner: `scripts/run_golden_cloud_eval.py`. Dùng cấu hình `.env` hiện có: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` và provider/model của hệ thống. Không ghi khóa vào dataset hoặc báo cáo.

```powershell
# Chỉ kiểm tra cấu hình và quyền đọc project
.\.venv\Scripts\python.exe scripts/run_golden_cloud_eval.py --preflight

# Tải 60 ca, chạy offline, ghi trace và scores lên Cloud
.\.venv\Scripts\python.exe scripts/run_golden_cloud_eval.py --run --mode offline

# Chạy cả offline và online khi đã cho phép gửi prompt tới provider
.\.venv\Scripts\python.exe scripts/run_golden_cloud_eval.py --run --mode both

# Đọc lại bằng chứng của lượt đã chạy, không gọi lại model
.\.venv\Scripts\python.exe scripts/run_golden_cloud_eval.py --verify-output .test-runs/langfuse-golden/20261014-golden-cloud-04
```

Dataset Cloud có tên `p142-golden-v1-<12 ký tự đầu SHA256>` và item ID ổn định từ hash toàn bộ dataset + case ID. Chạy lại cùng dữ liệu sẽ dùng lại item không đổi; mỗi experiment có run ID riêng. Thư mục kết quả mới nằm dưới `.test-runs/langfuse-golden/`; `--output-dir` chỉ chấp nhận thư mục mới hoặc rỗng bên trong `.test-runs`.

Mỗi ca có hai score: `golden_pass` (đạt mọi điều kiện ở mọi lượt) và `golden_assertion_accuracy` (tỷ lệ điều kiện đạt, có tính kiểm tra số lượt). Run có thêm `golden_pass_rate`. Chấm điểm bằng quy tắc, không dùng LLM-as-judge. Pytest và Cloud dùng chung comparator `eval/golden.py`.

Hai chế độ đều thay retrieval bằng fixture của bộ golden. `online` bật lời gọi model theo cấu hình hiện có; prompt gửi cho model chứa đầu vào và nguồn giả lập, không chứa nhãn kỳ vọng. Database được tách riêng; mỗi ca có session riêng, các lượt trong ca dùng cùng session. Ca sau vẫn được chạy khi ca trước trượt. Provider circuit breaker giữ nguyên hành vi hệ thống trong cùng lượt eval.

Runner tôn trọng HTTP 429 `retryAfterSeconds` khi ghi Cloud. `results.json` và `run-reference.json` được lưu trước khi đọc lại từ Cloud để có thể xác minh lại mà không tốn thêm lượt model. Bước đọc dùng Experiments/Experiment Items API hiện hành, xác minh đúng dataset/item ID, đủ 60 trace, 120 score từng ca và 1 score tổng hợp, đồng thời so giá trị Cloud với local. Trạng thái online chỉ được xác nhận khi đọc thấy generation thực trên Cloud.

Exit code: `0` khi mọi ca đạt và bằng chứng đầy đủ; `1` khi có ca trượt; `2` khi thiếu bằng chứng Cloud hoặc lượt online chưa xác nhận được generation thực. Các lỗi cấu hình/network không được xử lý ở lớp ngoài có thể trả `1` kèm traceback; luôn đọc `manifest.json`, không diễn giải mọi exit code `1` thành lỗi nhãn.

[Báo cáo Cloud ngày 2026-10-14](../results/golden-v1/langfuse-cloud-20261014/report.md) ghi hai lượt đã chạy và liên kết mở trên Langfuse.

### Theo dõi token, latency và chi phí

Sau mỗi `--run` hoặc `--verify-output`, runner tự xuất `metrics.json`, `metrics.md` và `case-metrics.csv` trong thư mục từng chế độ. CSV gồm case/trace ID, số lượt, thời gian xử lý, số generation, input/output/total token, chi phí USD và độ đầy đủ của usage.

Latency có trung bình, P50, P95 (nearest rank) và max; thống kê riêng toàn bộ ca và nhóm có gọi LLM. Thời gian đo là xử lý toàn bộ hội thoại của một ca, không gồm gửi/đọc Cloud. Những ca nhiều lượt không tương đương một tin nhắn. Token/cost tổng hợp từ generation thật trên Cloud, loại trùng observation ID và giữ thiếu dữ liệu thành null; đây là chi phí Cloud ghi nhận, chưa đối chiếu hóa đơn provider.
