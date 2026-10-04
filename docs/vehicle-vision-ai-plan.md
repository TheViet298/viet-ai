# Kế hoạch AI: nhận dạng dòng xe VinFast và hư hại ngoại thất

Ngày: 2026-10-04. Nhánh: `feature/agent-long`.

Trạng thái: bản đề xuất thiết kế và kế hoạch để review; chưa viết code, nhận dataset, huấn luyện hoặc đo KPI. Bản này thay thế phạm vi OCR/Vision của kế hoạch trước đối với phần việc của Long; không thay đổi phần việc thành viên khác.

## 1. Phạm vi đã chốt và trách nhiệm

Người dùng cung cấp bộ ảnh các mẫu xe VinFast. Nhánh này chỉ làm AI: nhận dạng dòng xe và phát hiện hư hại ngoại thất nhìn thấy trên ảnh. OCR táp-lô đã có thành viên khác phụ trách. Huấn luyện trước mắt trên môi trường cloud/notebook; chưa có GPU cá nhân.

| Người phụ trách | Công việc |
|---|---|
| Nhánh AI Long | Chuẩn hóa dataset, model dòng xe, model hư hại, inference module, schema kết quả, benchmark và tích hợp bằng chứng vào Agent |
| Thành viên OCR | OCR táp-lô, mức pin, mã lỗi và biểu tượng; cung cấp module/kết quả theo contract phối hợp |
| Backend | Xác thực, quyền sở hữu ảnh/session, upload, storage, jobs/timeouts, gọi AI và lưu kết quả |
| Frontend | Chọn/chụp ảnh, preview, hiển thị kết quả/khung hư hại, xác nhận dòng xe và nhập tay |

Không thực hiện trong nhánh: giao diện, upload routes, database attachment, queue worker, OCR, nhận dạng biển số/VIN, giám định bảo hiểm, ước tính giá sửa chữa, xác định nguyên nhân hoặc mức an toàn của xe từ ảnh. Chỉ thêm contract AI và logic dùng kết quả trong Agent.

Hiện `src/agents/state.py` có `attachment_signals`; `src/agents/context_manager.py` quản lý fact history; `case_brief_node.py` sinh Brief. Agent có budget 2 giây theo `src/config.py`: inference ảnh phải được tầng tích hợp gọi riêng; Agent chỉ tiêu thụ kết quả có sẵn.

## 2. Thiết kế đề xuất

### Hai nhiệm vụ trên cùng một ảnh

“Ảnh xe” và “ảnh ngoại thất” không phải hai lớp loại trừ nhau. Một ảnh toàn xe có thể phục vụ cả nhận dạng dòng xe và tìm hư hại. Một ảnh cận vết xước có thể đủ cho detector nhưng không đủ để xác định dòng xe.

Luồng:

```text
Ảnh đã được backend kiểm tra
  → decode/xoay ảnh/kiểm tra chất lượng
  → xác định loại ảnh: exterior / dashboard / other / uncertain
      dashboard → trả deferred_to_ocr, tầng tích hợp gọi module thành viên OCR
      other/uncertain → yêu cầu ảnh phù hợp; không ép đoán
      exterior → hai đầu ra độc lập:
          1. vehicle model: ứng viên dòng xe hoặc unknown
          2. damage: vùng/loại hư hại nghi ngờ hoặc not_detected/insufficient_view
  → kết quả có cấu trúc, model version và nguồn ảnh
  → khách/nhân viên xác nhận → Agent → RAG/Case Brief
```

Chọn loại ảnh trên UI là một gợi ý, không phải bằng chứng chắc chắn. Bản đầu ưu tiên pipeline ngoại thất với request task rõ ràng và bộ kiểm tra loại ảnh; chỉ huấn luyện router ảnh khi có đủ ảnh dashboard/other do đội phối hợp cung cấp. Nếu chưa có router được đánh giá, ghi `image_type=uncertain`, có thể yêu cầu xác nhận/chọn lại loại ảnh; không tuyên bố tự phân loại dashboard chính xác.

### Phương án model

1. **Khuyến nghị: classifier pretrained riêng + detector riêng.** Fine-tune YOLO classification (`-cls`) hoặc classifier gọn trong PyTorch/torchvision (ứng viên MobileNetV3/ResNet18); fine-tune YOLO detector trên CarDD sau kiểm tra dependency/checkpoint/license. Dòng xe và hư hại có lifecycle, dữ liệu, metrics và feature flags riêng.
2. **VLM API làm baseline so sánh hoặc fallback có kiểm soát.** Hữu ích trước khi có weights và dữ liệu đủ; không dùng mô tả model làm ground truth. VLM API không yêu cầu GPU cá nhân; VLM open-weight chạy local có yêu cầu bộ nhớ/phần cứng riêng, không mặc định phù hợp CPU.
3. **Model nhiều nhiệm vụ hoặc segmentation ngay từ đầu.** Chỉ cân nhắc sau MVP: khó gán nhãn và debug; chưa cần khi đầu ra MVP chỉ là bbox.

Không khóa model đời mới nhất trước benchmark. Khóa architecture, checkpoint, package versions, preprocessing, label map và thresholds trong manifest sau chạy thử. Notebook dùng GPU để train; runtime CPU được đo độc lập. ONNX chỉ bổ sung khi đo cho thấy cần và parity với PyTorch đạt.

### YOLO hay VLM?

| Mục tiêu | YOLO | VLM |
|---|---|---|
| Phân loại exterior/dashboard/other | Model classification với nhãn loại ảnh; cần dữ liệu/unknown tests | Có thể prompt phân loại từ đầu; vẫn cần test giao nhầm và unknown |
| Nhận dạng VF3/VF5/... | Fine-tune model classification bằng ảnh gắn nhãn dòng xe | Prompt danh sách dòng xe + unknown; thử trên tập độc lập, có thể nhầm dòng gần giống |
| Tìm vùng hư hại | Model detection bbox; segmentation nếu cần mask và có nhãn | Có thể mô tả/đề xuất vùng tùy model; tọa độ phải đánh giá riêng, không xem như detector đã kiểm chứng |
| Dữ liệu trước chạy | Nhãn dòng xe cho classification; bbox/mask cho damage | Không cần train để thử baseline; vẫn cần ground truth để đo chất lượng |
| Vận hành | Cloud GPU để fine-tune, model nhỏ có thể benchmark CPU/offline | API phụ thuộc mạng/chi phí; self-host cần đánh giá tài nguyên |

YOLO detection pretrained thông thường nhận lớp `car` không đồng nghĩa biết VF5/VF8 hay có lớp vết xước. Cần checkpoint đúng tác vụ và fine-tune label map. Với nhiều xe, detector tìm từng xe rồi classifier nhận từng crop; MVP có thể yêu cầu ảnh một xe thay vì thêm pipeline nhiều xe ngay.

Đề xuất thực hiện: benchmark VLM trên tập development/validation trước để có mốc so sánh; khi nhận dataset, train YOLO-cls cho dòng xe và YOLO-detect cho hư hại. Nếu ưu tiên demo nhanh, VLM có thể cung cấp kết quả đề xuất trong khi chờ train, nhưng không thay detector bbox hoặc tuyên bố accuracy chưa đo. Chỉ gọi VLM fallback khi kết quả unknown/ảnh khó và tính lợi ích trên validation; không gọi cả hai model trên mọi ảnh mặc định. VLM không được tự ghi đè nhãn đã xác nhận hoặc confidence của detector.

## 3. Cần dữ liệu gì ngoài ảnh các mẫu xe?

### A. Bộ nhận dạng dòng xe do người dùng cung cấp

- Danh sách dòng xe thực sự cần hỗ trợ: đề xuất VF3/VF5/VF6/VF7/VF8/VF9/e34, chỉ bật các lớp có dữ liệu được xác nhận.
- Ảnh kèm nhãn đúng: `vehicle_model`, `vehicle_group_id` hoặc `capture_group_id`, nguồn/quyền sử dụng, góc chụp và đời xe nếu biết. Không tự đoán năm/phiên bản nếu không có nhãn.
- Mốc thu thập khởi đầu đề xuất: 100–200 ảnh gốc mỗi dòng, đến từ khoảng 10–20 chiếc xe/nguồn độc lập nếu có thể. Đây là mục tiêu chuẩn bị, không bảo đảm đủ để đạt KPI; nhận ít hơn vẫn audit được nhưng giảm số dòng hỗ trợ.
- Các góc trước, sau, trái, phải, góc chéo; nhiều màu, nền, ánh sáng, khoảng cách; có ảnh không thấy logo. Không chỉ ảnh quảng cáo hoặc nhiều crop của cùng một xe.
- Ảnh âm: xe hãng khác, mẫu VinFast chưa hỗ trợ, nội thất/táp-lô, ảnh không phải xe, crop quá sát, nhiều xe. Có thể dùng nhãn `unknown` làm dữ liệu kiểm tra/huấn luyện hỗ trợ rejection; softmax classifier vẫn cần hiệu chuẩn và kiểm thử ngoài phân bố.
- Tập test ảnh thật của xe/phiên chụp chưa xuất hiện trong train. Tối thiểu đề xuất 20–30 ảnh gốc độc lập mỗi lớp cho báo cáo ban đầu; công bố số xe/phiên và độ bất định, không xem nhiều ảnh cùng một xe là nhiều mẫu độc lập.

Nếu chỉ có một chiếc/màu/nền cho mỗi dòng, model có thể học nền hoặc màu thay vì hình dáng. Nếu không biết group ID, cần suy ra nhóm nguồn và khử gần trùng trước split; ghi rõ hạn chế.

### B. Bộ hư hại ngoại thất

- CarDD làm dữ liệu nền: 4.000 ảnh, hơn 9.000 instance thuộc 6 nhóm theo bài báo: `dent`, `scratch`, `crack`, `glass shatter`, `tire flat`, `lamp broken`.
- Bảo toàn ID/name mapping gốc; nhãn nội bộ dùng `dent`, `scratch`, `crack`, `glass_shatter`, `tire_flat`, `lamp_broken` sau bước chuyển đổi đã kiểm tra. Giữ split gốc khi so sánh với benchmark CarDD; kiểm tra rò rỉ vào test VinFast bổ sung.
- CarDD cần được tác giả cho phép sử dụng theo license; thương mại cần được cho phép riêng. Chưa tải và không gửi email xin quyền trong tác vụ lập kế hoạch này.
- Cần bổ sung ảnh VinFast hư hại thực tế có bbox và nhãn từng vùng để kiểm thử khả năng áp dụng. Ảnh sạch các mẫu xe không cung cấp nhãn vết xước/móp.
- Cần ảnh VinFast nguyên vẹn và hard negatives: bóng đổ, phản sáng, bụi/bùn, đường ráp thân xe, decal. Mục đích đo false positive thay vì suy ra xe hư từ bất kỳ đường tối nào.
- Mốc khởi đầu đề xuất: 100–200 ảnh hư hại VinFast và 100–200 ảnh nguyên vẹn, cân đối các lớp có thể thu thập. Lớp không đủ ảnh test phải ghi chưa xác minh; không cam kết nhận diện cả 6 lớp trên VinFast khi chưa có mẫu.
- Bbox nhiều instance/ảnh là yêu cầu MVP; segmentation mask là tùy chọn giai đoạn sau. Tên bộ phận (cửa/cản/đèn) là nhiệm vụ nhãn riêng, không suy ra CarDD cung cấp đầy đủ part annotations.

Không có vùng hư hại được phát hiện chỉ có nghĩa “chưa phát hiện trong phần nhìn thấy”, không đồng nghĩa cả xe nguyên vẹn. Ảnh mờ/che/cận cảnh không đủ → `insufficient_view`.

### C. Dữ liệu phối hợp và metadata

- Một bộ mẫu dashboard/other có quyền dùng và nhãn loại ảnh từ thành viên OCR để kiểm thử giao nhầm; chưa cần lấy lại dataset OCR để huấn luyện chữ.
- Thống nhất thư mục hoặc manifest, đường dẫn ảnh và ID ảnh. Không cần cung cấp VIN, biển số, danh tính chủ xe.
- Bbox dùng tọa độ tương ứng ảnh đã xoay EXIF đúng hướng; training augmentation sau split, ảnh sinh/ảnh augment không đưa vào test thật.
- Chỉ dùng nguồn được phép; lưu provenance/license/consent trong manifest. File ảnh và weights dưới `data/`, không đưa vào Git.

Ví dụ bố trí dữ liệu (chỉ là hướng dẫn, chưa tạo dataset):

```text
data/vision/vehicles/VF3/*.jpg
data/vision/vehicles/VF5/*.jpg
data/vision/vehicles/unknown/*.jpg
data/vision/damage/images/*.jpg
data/vision/damage/annotations.json
data/vision/manifests/vehicles.jsonl
data/vision/manifests/damage.jsonl
```

## 4. Contract AI bàn giao

Module nhận bytes ảnh đã kiểm tra từ backend, ID nguồn và danh sách tác vụ. Không nhận URL client tùy ý, không tự tải ảnh từ mạng, không tự truy cập session/storage/auth. Metadata bối cảnh dòng xe dùng sau dự đoán để kiểm tra xung đột; không dùng làm nhãn đáp án cho classifier.

Interfaces đề xuất:

```python
analyze_vehicle_image(image_bytes: bytes, attachment_id: str, tasks: tuple[str, ...]) -> VisualAnalysis
predict_vehicle_model(image: Image.Image) -> VehiclePrediction
detect_exterior_damage(image: Image.Image) -> DamagePrediction
merge_visual_evidence(state: AgentState, results: list[VisualAnalysis]) -> dict
```

`VisualAnalysis`: `schema_version`, `attachment_id`, `status`, `image_type`, `oriented_width`, `oriented_height`, `quality_issues`, `vehicle`, `damage`, `requires_confirmation`, `model_versions`, `latency_ms`.

- `status`: `ready/deferred_to_ocr/needs_retake/unavailable`; các nhánh có `not_requested` để phân biệt chưa chạy và chạy không tìm thấy.
- `VehiclePrediction`: `status=predicted/unknown/not_requested/unavailable`, `top_candidates` có `model/score`, `selected_model` nullable; score không tự coi là xác suất đúng.
- `DamagePrediction`: `status=detected/not_detected/insufficient_view/not_requested/unavailable`, list `detections` chứa `class_name/score/bbox_xyxy`.
- Bbox `[x1,y1,x2,y2]` chuẩn hóa 0–1 theo kích thước ảnh đã xoay; frontend dùng cùng ảnh xoay để overlay. Validation kiểm tra range, thứ tự tọa độ, nhãn whitelist, finite score.
- `requires_confirmation=true` khi có dòng xe ứng viên; Agent không tự ghi đè dòng xe khách xác nhận. Chưa hỗ trợ mức nặng/nhẹ, bộ phận hư hoặc báo giá.
- Model hư hại bị tắt/chưa có weights trả `unavailable`; không trả danh sách rỗng giả như model đã kết luận không có hư hại.

Thành viên OCR trả kết quả riêng với ID ảnh và phiên bản schema tương thích; người điều phối ở backend gọi đúng module. Kết quả ảnh không tự tạo lượt chat; backend gắn kết quả vào lượt hợp lệ sau kiểm tra session/owner.

## 5. Kế hoạch triển khai theo gói

Mỗi gói có thể review riêng. Xây nhận dạng dòng xe trước; detection hư hại có feature flag độc lập và chỉ bật sau có dữ liệu/quyền/đánh giá.

### Gói 1 — Contract và audit dataset

Files dự kiến: `src/models/vision.py`, `scripts/audit_vision_dataset.py`, `tests/test_vision/test_schemas.py`, `tests/test_vision/test_dataset_audit.py`, tài liệu `docs/vision-ai-contract.md`.

- [ ] Định nghĩa các result types và chữ ký module tại mục 4; thử fixtures chuẩn/sai, bbox ngược, score NaN, unknown và OCR deferred.
- [ ] Viết audit function `audit_dataset(manifest_path: Path) -> dict`: decode được, nhãn trong whitelist, thống kê lớp/góc/group, SHA256 và nhóm gần trùng, nguồn/quyền còn thiếu.
- [ ] Kiểm thử ảnh giả/corrupt, nhãn lệch tên, group bị chia qua nhiều split; audit phải báo lỗi trước train.
- [ ] Chốt danh sách lớp đủ dữ liệu và split theo group 70/15/15; nếu ít group, đề xuất thu thêm hoặc giới hạn scope thay vì tách cùng xe qua test.
- [ ] Bàn giao dataset report và contract cho backend/OCR; chốt image orientation và `not_requested/unavailable` semantics.

### Gói 2 — Nhận dạng dòng xe

Files dự kiến: `src/services/vision/preprocess.py`, `src/services/vision/vehicle_classifier.py`, `scripts/train_vehicle_classifier.py`, `scripts/eval_vehicle_classifier.py`, `notebooks/train_vehicle_classifier.ipynb`, `requirements-vision-train.txt`, `requirements-vision-runtime.txt`, `tests/test_vision/test_vehicle_classifier.py`.

- [ ] Preprocessing thống nhất train/inference; thử EXIF rotation, grayscale, corrupt image và ảnh quá lớn. Giới hạn đề xuất nội bộ: 5 MiB bytes, 20 megapixel decoded, image tĩnh.
- [ ] Huấn luyện classifier pretrained trên cloud bằng entrypoint script có seed/config; notebook gọi cùng script, không chứa logic thứ hai.
- [ ] Chọn checkpoint bằng validation macro-F1; giữ test không dùng lựa model/threshold.
- [ ] Chọn rejection threshold trên validation, đo unknown/hãng khác/crop sát; không chỉ dựa score tối đa để công bố open-set robust.
- [ ] Implement `predict_vehicle_model` với injected predictor cho unit test; map đúng class index, thiếu weights trả unavailable, ảnh nhiều xe không chọn bừa.
- [ ] Chạy test với weights thật; báo confusion matrix, per-model recall/precision, coverage, unknown false acceptance và latency CPU.

### Gói 3 — Phát hiện hư hại ngoại thất

Files dự kiến: `scripts/prepare_cardd.py`, `scripts/train_damage_detector.py`, `scripts/eval_damage_detector.py`, `src/services/vision/damage_detector.py`, `tests/test_vision/test_damage_detector.py`; reuse dependency files gói 2.

- [ ] Kiểm tra quyền CarDD và artifact thật; chuyển COCO bbox sang detector format, có unit test tọa độ và category map; không đổi tên nhãn theo cảm tính.
- [ ] Train detector pretrained trên cloud; giữ split CarDD gốc và test VinFast riêng. Training env/checkpoint/license được ghi rõ trong manifest.
- [ ] Kiểm thử nhiều vùng hư hại, bbox ngoài ảnh, empty output, engine lỗi, feature flag tắt và ảnh không đủ view; lỗi không bị chuyển thành not_detected.
- [ ] Chọn thresholds trên validation, kiểm thử false positives trên xe nguyên vẹn/phản sáng; audit thủ công các lỗi xước–móp.
- [ ] Bàn giao detector bbox và báo cáo per-class AP/precision/recall, không thêm severity/part inference khi không có nhãn.

### Gói 4 — Điều phối AI và bằng chứng Agent

Files dự kiến: `src/services/vision/analyzer.py`, `src/agents/visual_evidence.py`, `src/agents/state.py`, `src/agents/nodes/intake_node.py`, `src/agents/nodes/case_brief_node.py`, `src/agents/context_manager.py`, `src/agents/chatbot_agent.py`, `src/config.py`, `tests/test_vision/test_analyzer.py`, `tests/test_agents/test_visual_evidence.py`.

- [ ] Analyzer thực hiện các tác vụ độc lập: dòng xe unknown vẫn cho phép detector chạy; detector unavailable không làm mất vehicle result; dashboard trả deferred_to_ocr.
- [ ] `merge_visual_evidence` chỉ nhận schema đã validate; lưu ID/phiên bản/tóm tắt, không lưu bytes ảnh hoặc base64 vào Agent/tracer.
- [ ] Kết quả dòng xe là đề xuất. Người dùng xác nhận mới cập nhật `captured_fields.vehicle_model`/fact history; mâu thuẫn giữ cả nguồn để làm rõ.
- [ ] Brief ghi vùng/loại hư hại nghi ngờ và ID ảnh; không điều phối cứu hộ hoặc chẩn đoán nguyên nhân chỉ bằng detector score.
- [ ] Kết quả cũ/đã tiêu thụ/khác lượt không ghi đè dữ kiện mới; thêm test conflict, xác nhận sửa và module bị tắt.
- [ ] Giữ safety văn bản chạy trước, không thêm inference model vào budget 2 giây; kiểm tra regression Agent và bàn giao adapter call cho backend.

### Gói 5 — Đánh giá và bàn giao

Files dự kiến: `scripts/run_vision_eval.py`, `docs/vision-ai-model-card.md`, `eval/results/vehicle-vision/` (report/version metadata; ảnh thật/weights ở data).

- [ ] Chạy held-out vehicle/damage/router riêng, không gộp thành một accuracy.
- [ ] Ghi dataset hash/group splits, model/checkpoint hash, label map, preprocessing, seed, package versions, threshold, hardware, batch=1 và latency cold/warm/P95.
- [ ] Unit test dùng stub; test chất lượng dùng weights và ảnh thật. Chạy `pytest tests/test_vision tests/test_agents -q` sau triển khai, không ghi “đạt” trước khi chạy.
- [ ] Bàn giao module + weights manifest + dependency runtime + sample JSON + hướng dẫn notebook/train/eval/CPU inference; backend/frontend/OCR tích hợp theo contract.

## 6. Tiêu chí đánh giá đề xuất

| Hạng mục | Tiêu chí |
|---|---|
| Dòng xe | Mục tiêu precision ≥90% trong dự đoán chấp nhận, coverage ≥70% trên ảnh đủ view; macro-F1, per-class metrics và số group phải công bố |
| Unknown | Mục tiêu false acceptance ≤10% trên tập âm; báo riêng hãng khác, mẫu chưa hỗ trợ, crop sát/nhiều xe; không bảo đảm chỉ nhờ threshold |
| Hư hại | Báo mAP50-95, AP từng lớp, recall và false positive/image trên ảnh nguyên vẹn; ngưỡng nghiệm thu chốt sau baseline validation, trước test |
| Giao nhầm OCR | Nếu router chưa được đánh giá, ghi uncertain/defer; nếu có router, báo confusion matrix và dashboard false-route rate trên ảnh OCR thành viên cung cấp |
| CPU inference | Đo P50/P95 batch=1; mục tiêu ban đầu ≤5 giây/ảnh trên CPU được chỉ định, không phải SLA chat; runtime target cần benchmark thật |
| Tích hợp | Schema valid, không tự đổi dòng xe confirmed, không giả not_detected khi lỗi, không chặn emergency văn bản; regression phải pass |

Không đạt dòng xe/lớp hư hại nào thì giữ unknown/unavailable hoặc giảm coverage hỗ trợ. Không bù bằng nhãn khách xác nhận để nâng điểm AI. Test ít mẫu hoặc nhiều ảnh cùng một xe phải được ghi là đánh giá ban đầu.

## 7. Lộ trình và những thông tin còn cần

Ước lượng có điều kiện cho một người AI: audit/contract 1–2 ngày; classifier 2–3 ngày; detector 3–5 ngày; tích hợp/eval/bàn giao 2–3 ngày. Khoảng 8–13 ngày làm việc khi dữ liệu đã có nhãn và cloud GPU truy cập được; không bao gồm thời gian xin quyền CarDD, chờ quota, gán nhãn hoặc thu thêm ảnh. Module dòng xe có thể bàn giao trước trong khoảng 3–5 ngày theo cùng điều kiện.

Người dùng cần cung cấp: danh sách dòng xe, số ảnh từng dòng, nhãn tên dòng, nguồn/quyền dùng, group xe/phiên chụp nếu biết. Đội cần thêm: CarDD được phép dùng + ảnh VinFast hư hại/xe sạch có nhãn; ảnh âm; bộ test độc lập; runtime CPU mục tiêu; contract/ảnh mẫu để bàn giao module OCR.

Cloud notebook và tài khoản/quota dùng để train do người dùng chọn. Kế hoạch không tạo tài khoản, mua GPU, upload dữ liệu hoặc tải model trong tác vụ này. Khi có dữ liệu, bước đầu là audit để quyết định đủ train lớp nào; chưa cần train tất cả dòng hoặc segmentation ngay.

## 8. Nguồn kỹ thuật

- [PyTorch transfer learning tutorial](https://docs.pytorch.org/tutorials/beginner/transfer_learning_tutorial.html): cơ sở fine-tune classifier pretrained.
- [Ultralytics object detection](https://docs.ultralytics.com/tasks/detect/): tham khảo detector bbox; xác minh license/checkpoint khi chốt lựa chọn.
- [YOLO classification](https://docs.ultralytics.com/tasks/classify/), [YOLO segmentation](https://docs.ultralytics.com/tasks/segment/): tác vụ phân loại và mask là các checkpoint/task riêng.
- [Gemini image understanding](https://ai.google.dev/gemini-api/docs/image-understanding): ví dụ VLM API cho baseline hiểu ảnh; chưa chứng minh chất lượng trên VinFast.
- [CarDD project](https://cardd-ustc.github.io/), [bài báo](https://arxiv.org/html/2211.00945v2), [license](https://cardd-ustc.github.io/docs/CarDD_license.pdf): số ảnh, loại nhãn và điều kiện truy cập.

Đọc nguồn ngày 2026-10-04. Các model, KPI và số ảnh bổ sung trong bản này là đề xuất lập kế hoạch; chưa phải chất lượng đã được đo hoặc thiết kế được người dùng duyệt.
