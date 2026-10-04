# Inference CarDD trong nhánh AI

`CarddDamageDetector` chạy checkpoint CarDD baseline cục bộ, mặc định CPU và confidence 0,25. Model chỉ được load khi có ảnh hợp lệ và được giữ lại để dùng cho các lần gọi sau. Load/predict dùng lock trong mỗi instance; tầng backend gọi ngoài budget hội thoại của agent.

Weights mặc định: `data/vision/trained/cardd-damage-baseline-v1/weights/best.pt`. SHA256 được kiểm tra theo checkpoint đã nhận; file thiếu/sai hash không được tải thay thế tự động. Names phải khớp 6 lớp nguồn theo đúng ID.

## Dùng trong Python

```python
from src.services.vision.damage_detector import CarddDamageDetector

detector = CarddDamageDetector()  # khởi tạo một lần cho mỗi worker
evidence = detector.analyze(image_bytes, image_id="attachment-123")
result = evidence.model_dump()
```

Ảnh bytes tối đa 5 MiB, tối đa 20 megapixel, ảnh tĩnh; decode, xoay EXIF, chuyển RGB trước inference. Bbox `xyxy_normalized` tương ứng **ảnh đã xoay EXIF**, tầng hiển thị cần cùng orientation. Không lưu bytes/base64 vào result.

Vehicle giữ `not_requested`, OCR giữ `deferred_to_ocr`. Damage trả `detected` hoặc `not_detected` khi inference thành công. Lỗi có `unavailable` và reason: `weights_missing`, `checkpoint_hash_mismatch`, `runtime_dependency_missing`, `model_load_failed`, `model_incompatible`, `invalid_image`, `image_too_large`, `animated_image_unsupported`, `inference_failed`, `invalid_model_output`. Lỗi không được chuyển thành không hư hại.

Confidence là score của detector, chưa hiệu chỉnh; không kết luận xe nguyên vẹn, mức độ hư hại, chi phí sửa hoặc nguyên nhân sự cố. Không có router ảnh táp-lô/other; bên gọi phải chọn tác vụ damage cho ảnh ngoại thất. Checkpoint này chưa được nghiệm thu trên ảnh VinFast thật.

## Môi trường và CLI

Môi trường inference tách khỏi backend. Ví dụ Windows CPU:

```powershell
python -m venv data/vision/runtime-env
data/vision/runtime-env/Scripts/python.exe -m pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cpu
data/vision/runtime-env/Scripts/python.exe -m pip install -r requirements-vision-runtime.txt
data/vision/runtime-env/Scripts/python.exe scripts/predict_cardd.py --image path/to/exterior.jpg --output data/vision/predictions/result.json
```

CLI xuất JSON `VisionEvidence`, exit 0 khi inference thành công, exit 2 khi result unavailable; thời gian của lần gọi đầu ghi stderr, gồm load model. File ảnh không tồn tại vẫn là lỗi đầu vào CLI. Không tạo API upload, database/job hay thay đổi OCR/vehicles trong tác vụ này.

Nếu thay checkpoint, truyền `--weights` và `--expected-sha256` đúng phiên bản đã kiểm tra. Library không import torch/Ultralytics ngay khi import module; backend không cài inference dependencies vẫn nhận reason rõ ràng khi gọi.

Unit tests dùng injected engine để kiểm tra lỗi, mapping và contract; smoke test dùng weights thật trên ảnh validation chỉ xác minh đường đi inference, không phải benchmark chất lượng thực tế.

Kiểm tra đã thực hiện: 9 test inference và 15 test chuẩn bị/cloud/schema đạt; lint đạt. Checkpoint thật chạy CPU trên ảnh validation 000014, trả scratch ~0,903, dent ~0,659, tire flat ~0,626, schema hợp lệ. CLI lần chạy đầu gồm import/setup mất ~13,25 giây; thử trong process đã import dependencies, lần load/predict đầu ~1,18 giây và hai lần dùng lại model ~0,061 giây/ảnh. Đây là smoke timing của một ảnh trên máy hiện tại, không phải P95/SLA. JSON ở `data/vision/predictions/cardd-000014.json`, timing ở `cardd-cpu-smoke.json`.
