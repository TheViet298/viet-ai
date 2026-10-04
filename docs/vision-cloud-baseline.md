# Chạy baseline AI hình ảnh xe trên cloud

Nhánh: `feature/agent-long`. Hai notebook chỉ chạy phần AI; OCR và kết nối chatbot chưa nằm trong thay đổi này.

## File dùng ngay

- `notebooks/train_vehicles_baseline.ipynb`: YOLO11n Classification cho 14 nhãn thư mục VinFast, train 167 / validation 41 ảnh. Một ảnh Nerio Green để riêng.
- `notebooks/train_damage_baseline.ipynb`: YOLO11n Detection cho 6 nhãn CarDD, train 2.222 / validation 594 ảnh, tổng 6.211 bbox.
- `data/vision/cloud-baseline-v2.zip`: dữ liệu và code đã đóng gói, không chứa đường dẫn Windows trong manifest dùng trên cloud. Không upload tự động; giữ gói dữ liệu trong không gian riêng.
- `src/services/vision/contract.py`: schema và adapter kết quả. JSON Schema ở `docs/vision-evidence.schema.json`; `docs/vision-evidence.example.json` là ví dụ giả lập, không phải dự đoán đã chạy.

## Colab

1. Đặt `cloud-baseline-v2.zip` trong Google Drive của bạn; mở một notebook bằng Upload notebook.
2. Chọn GPU trong Runtime, sửa `ZIP_PATH` nếu ZIP không nằm ở MyDrive. Chạy lần lượt các cell.
3. Cell preflight kiểm tra split, label map và trùng byte trước train. Cell train tải pretrained checkpoint khi cần. Mặc định 40 epochs, batch 16, seed 142; giảm batch nếu thiếu VRAM.
4. Xem `evaluation.json`, confusion matrix/plots, ảnh dự đoán và JSON mẫu. Tải ZIP artifacts hoặc đặt `RUNS` trên Drive trước khi train để giữ checkpoint khi hết phiên.
5. Chạy notebook thứ hai với cùng gói dữ liệu. Nếu train lại cùng tác vụ, đổi `RUNS`; script giữ các kết quả cũ.

## Kaggle

Đưa ZIP vào private input của tài khoản của bạn, import notebook, sửa `ZIP_PATH` đến input thật, chọn GPU và bật Internet để cài dependencies/tải checkpoint. `WORK` mặc định tự chọn `/kaggle/working`. ZIP kết quả xuất hiện trong Output; cần lưu phiên/kết quả trước khi đóng.

## Kết quả và giới hạn

Hai notebook gọi chung `scripts/train_vision_baseline.py`, không chứa bản sao logic train. Môi trường khóa Ultralytics 8.3.235, dùng torch/torchvision GPU của notebook và ghi phiên bản thực tế. Chưa chạy GPU training trong tác vụ chuẩn bị này.

Mỗi run lưu `weights/best.pt`, `args.yaml`, `results.csv`, plots và `evaluation.json` có hash dữ liệu/checkpoint, nhãn, seed, package versions, GPU và metrics. Classifier thêm macro-F1, precision/recall từng lớp và confusion matrix; detector thêm AP50–95 từng lớp và metrics tổng của Ultralytics. Checkpoint chọn theo validation fitness mặc định, không chọn theo test hoặc macro-F1. Các transforms/crop mặc định của YOLO Classification có thể làm mất đặc điểm xe trong ảnh dài; phải kiểm tra preview và thử preprocessing phù hợp ở vòng sau.

Validation chỉ là split phát triển nội bộ, không có test ảnh chụp thật độc lập. Threshold classifier 0.7 và detector 0.25 chỉ là ngưỡng thử; chưa hiệu chỉnh unknown/hãng khác và xe nguyên vẹn. Nhãn xe vẫn là nhãn thư mục, chưa xác nhận taxonomy. CarDD mirror không phải benchmark đầy đủ; license gốc được giữ trong ZIP, quyền tác giả vẫn như báo cáo audit.

## Contract bàn giao agent

`VisionEvidence` có `schema_version`, `image_id`, `vehicle`, `damage` và `ocr=deferred_to_ocr`. Bbox dùng **xyxy chuẩn hóa theo ảnh**, không dùng pixel hoặc xywh.

- Vehicle: `candidate` là dòng xe đề xuất cần xác nhận; `unknown` khi dưới ngưỡng; `unavailable` khi không chạy được; `not_requested` khi không yêu cầu.
- Damage: `detected`, `not_detected`, `unavailable`, `not_requested`. `not_detected` không xác nhận xe nguyên vẹn. Lỗi model phải trả `unavailable` kèm reason, không chuyển thành kết quả rỗng.
- Hai tác vụ độc lập: xe unknown vẫn giữ kết quả damage. Không có severity, bộ phận xe hoặc chẩn đoán nguyên nhân vì dữ liệu chưa có nhãn này. Không tự ghi đè thông tin dòng xe đã được khách xác nhận.

Notebook minh họa chuyển output YOLO sang contract, lưu `prediction-example.json`. Adapter này chưa được gắn vào intake/Knowledge Agent; bước đó cần checkpoint đã train và đánh giá trước.

## Tái tạo gói

```powershell
python scripts/export_vision_cloud.py --output data/vision/cloud-baseline-v3.zip
python -m unittest discover -s tests -p 'test_vision*.py' -v
```

Exporter không ghi đè ZIP đã có, giữ nguyên split của baseline v1 và không sửa dữ liệu nguồn. Trên cloud có thể chạy preflight riêng mà không import framework:

```bash
python scripts/train_vision_baseline.py --task vehicles --data-root /content/vision-baseline --check-only
python scripts/train_vision_baseline.py --task damage --data-root /content/vision-baseline --check-only
```

Tham khảo API: [YOLO11](https://docs.ultralytics.com/models/yolo11/), [classification](https://docs.ultralytics.com/tasks/classify/), [detection](https://docs.ultralytics.com/tasks/detect/), [validation](https://docs.ultralytics.com/modes/val/). Dependencies train được tách khỏi requirements của backend.

Kiểm tra local ngày 2026-10-04: 15 vision unit tests đạt, Ruff đạt, code cells của cả hai notebook compile được; schema và JSON ví dụ khớp. ZIP cuối có 5.859 entries, CRC đạt và code đóng gói khớp code hiện tại. Preflight trên dữ liệu giải nén đạt cho cả hai tác vụ; orchestration train/eval được test bằng engine giả lập, chưa xác minh runtime train GPU thực tế. Dùng ZIP v2; ZIP v1 là bản trước sửa sai số làm tròn bbox.
