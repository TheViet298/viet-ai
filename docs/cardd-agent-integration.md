# CarDD → AI Agent → Case Brief

Inference chạy ngoài graph bằng `CarddDamageDetector`. Agent nhận JSON `VisionEvidence` đã tính sẵn, không load weights hoặc import Ultralytics trong lượt chat. Vehicles và OCR giữ nguyên.

## Bàn giao Python

```python
import asyncio
from src.services.vision.damage_detector import CarddDamageDetector
from src.agents.chatbot_agent import process_chat_message

# Reuse detector; bên tích hợp xác thực quyền sở hữu ảnh/session và chọn ảnh ngoại thất.
detector = CarddDamageDetector()
evidence = await asyncio.to_thread(detector.analyze, image_bytes, image_id="attachment-123")
result = await process_chat_message(
    "Xem ảnh ngoại thất giúp tôi",
    session_id=session_id,
    user_role="customer",
    owner=authenticated_owner,
    damage_evidence=evidence.model_dump(mode="json"),
)
```

`damage_evidence` là tham số nội bộ do tầng tích hợp truyền sau inference. Không lấy từ `client_context` hoặc JSON tùy ý do client tự khai báo.

## Thử từ UI

Trong chat, **Loại ảnh → Tự nhận diện loại ảnh** là mặc định. Server phân loại nội dung bằng Vision trước khi chọn công cụ:

- Táp-lô hoặc trụ sạc → luồng OCR hiện có.
- Ngoại thất xe → CarDD, không đọc biển báo trong nền thành cảnh báo táp-lô.
- Chưa chắc chắn hoặc Vision lỗi → yêu cầu chọn loại ảnh/chụp lại; không tự chạy OCR thay thế.

UI hiển thị loại ảnh nhận được. Có thể chọn thủ công **Táp-lô / trụ sạc** hoặc **Ngoại thất xe — kiểm tra hư hại** để phân tích lại ảnh đang chọn.
API upload nhận multipart `image_kind=auto|dashboard|exterior`. UI gửi `auto`; client cũ không gửi trường này vẫn giữ mặc định `dashboard` để tương thích.
Phân loại tự động sử dụng dịch vụ Vision bên ngoài; CarDD chạy cục bộ. Ngưỡng `IMAGE_ROUTING_MIN_CONFIDENCE=0.8` là cấu hình ban đầu, chưa được hiệu chỉnh trên tập kiểm định. `IMAGE_ROUTING_TIMEOUT_S=12` giới hạn thời gian chờ.
Ảnh ngoại thất chạy CLI CarDD trên CPU, lưu `CARDD/vision_evidence` cùng owner của attachment.
Chat chỉ đọc evidence do server lưu sau khi kiểm tra quyền sở hữu, xử lý an toàn trước,
rồi gọi Agent và lưu Case Brief vào database backend khi cần nhân viên tiếp nhận.
Các lượt xác nhận dùng session CarDD riêng theo owner; không lấy kết quả dự đoán từ client.

Runtime mặc định dùng `data/vision/runtime-env/Scripts/python.exe` trên Windows
(hoặc `bin/python` trên Linux), nếu không có thì dùng Python của backend.
Có thể đặt `CARDD_PYTHON_EXECUTABLE` trỏ đến môi trường đã cài requirements vision.
`CARDD_INFERENCE_TIMEOUT_S` mặc định 45 giây; timeout hoặc lỗi runtime trả `unavailable`,
không chuyển sang OCR và không khẳng định xe nguyên vẹn. Mỗi upload chạy một process CPU riêng.
Vehicles vẫn chưa chạy inference trên UI.

Đường đi: intake chuẩn hóa tín hiệu → safety → review ảnh mới → hỏi xác nhận/ảnh bổ sung → intake thông tin khách → Case Brief. Safety khẩn cấp và chặn hướng dẫn nguy hiểm luôn được xử lý trước; FAQ/complaint/ngoài phạm vi tiếp tục theo luồng văn bản.

## Xác nhận và bằng chứng

- `detected`: liệt kê dấu hiệu AI. Nếu mọi score dưới 0,5, nói rõ chưa chắc chắn; 0,5 chỉ là quy tắc diễn đạt thử nghiệm, không phải ngưỡng đã hiệu chỉnh hoặc bộ lọc bbox.
- `not_detected`: không xác nhận xe nguyên vẹn; hỏi mô tả/chụp cận cảnh.
- `unavailable`: chưa phân tích được ảnh; hỏi mô tả thủ công. Không chuyển lỗi thành không hư hại.
- `not_requested`: không tạo bằng chứng hư hại hoặc yêu cầu xác nhận.

Quick replies: **“Xác nhận hư hại trong ảnh”** và **“Không xác nhận kết quả ảnh”**. Chỉ hai câu trả lời rõ ràng này chuyển trạng thái xác nhận; một câu “oke” chung không xác nhận các nhãn AI. Xác nhận chỉ ghi nhận khách nói ảnh có hư hại, không chứng minh đúng từng label/bbox. Không thêm nhãn AI vào `captured_fields` hoặc thay dòng xe.

Khi khách xác nhận ảnh ngoại thất có hư hại, luồng hỏi dòng xe và xe còn di chuyển/khởi động được không; không bắt nhập đèn táp-lô để bù vào warning_symbol. Giữ giới hạn hai lượt làm rõ, quá giới hạn chuyển nhân viên với bằng chứng vẫn ghi trạng thái chưa xác nhận nếu cần.

Kết quả trả về có `visual_evidence`; Case Brief của Service/Incident có cùng trường và summary ghi nguồn AI/xác nhận khách. `confidence_score` của agent là độ chắc về định tuyến ý định, không thay cho confidence từng bbox.

Chỉ bằng chứng có xác nhận khách được thêm vào tool context cho Knowledge/RAG, kèm chú thích nhãn/bbox là giả thuyết. Nó không trở thành citation hoặc tài liệu sửa chữa. Query và fact người dùng không bị thay bằng tên nhãn AI; nguồn hướng dẫn vẫn phải qua kiểm tra tài liệu của RAG.

## Tránh kết quả cũ và dữ liệu thừa

Tín hiệu được gắn vào turn tiếp theo ở service entrypoint, tiêu thụ một lần ở intake và xóa `pending_cardd_signal`. Envelope khác lượt bị bỏ qua. Cùng ảnh/hash model/status/threshold/bbox không kích hoạt review lại hoặc đặt lại tuổi bằng chứng. Giữ tối đa ảnh gần nhất, tối đa 100 bbox; bằng chứng hết hiệu lực sau hai lượt tiếp theo, tránh gắn sang cuộc trao đổi mới.

Tầng tích hợp cần await inference và truyền kết quả cùng request hiện tại; nếu dùng job bất đồng bộ, phải đối chiếu attachment/session/turn trước khi gọi entrypoint. Agent không tự biết một kết quả mới chưa từng thấy thực ra thuộc job cũ. Bằng chứng malformed trở thành `unavailable/invalid_evidence`, không lưu raw payload. Metadata chỉ gồm ID ảnh, hash model, loại hư hại, tọa độ, score, turn và trạng thái xác nhận; không chứa bytes/base64/đường dẫn ảnh.

## Kiểm thử

`tests/test_agents/test_cardd_evidence.py` kiểm tra photo score thấp, safety, xác nhận/từ chối, persistence, stale/replay, payload sai, metadata không được giả xác nhận, FAQ và giới hạn làm rõ. Tests tắt live LLM, không chạy inference trong graph.

```powershell
python -m pytest tests/test_agents/test_cardd_evidence.py -q -p no:cacheprovider
```

Ảnh VinFast người dùng gửi được giữ làm ví dụ kiểm thử đường đi agent từ JSON đã có; chưa dùng để fine-tune và chưa có nhãn bbox ground truth để đo AP.

Đã kiểm tra: 199 tests đạt gồm toàn bộ agent và các test graph/API bridge, customer chat, dashboard chat; có 15 tests CarDD mới. Ruff và kiểm tra whitespace đạt. Hội thoại mô phỏng dùng kết quả ảnh VinFast được lưu ở `data/vision/predictions/cardd-agent-demo.json`; xác nhận trong file này là dữ liệu mô phỏng, không phải xác nhận thực của người dùng. Bản ảnh giữ nguyên hash ở `data/vision/vinfast-real-eval/unlabeled`, tách khỏi dữ liệu train.
