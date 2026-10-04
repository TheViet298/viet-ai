# Dataset cảnh báo táp-lô trong chatbot

API `/api/v1/customer/chat` tra `dataset/img_warning_taplo/dashboard_warnings_full.json`
theo mô tả cảnh báo và mẫu xe do khách hàng cung cấp trong tin nhắn hoặc `client_context.vehicle_model`.
Không dùng mẫu xe VF8 mặc định làm căn cứ nếu khách hàng chưa cung cấp mẫu xe.

Ví dụ: `VF e34 báo áp suất lốp thấp` trả hướng dẫn kèm nguồn tham chiếu;
`VF e34 đèn phanh đỏ` tạo hồ sơ CRITICAL để nhân viên xem xét.
Nguồn trong dataset chưa được kiểm chứng trực tiếp khi trả lời, nên citation có
`source_type=DATASET_REFERENCE`, `verified_at=null`, `status_code=null`.

Upload nhận JPEG/PNG/WebP thật, tối đa 5 MB; giải mã và tạo lại ảnh để bỏ metadata.
Ảnh được gửi tới Gemini theo `GOOGLE_API_KEY` và `DASHBOARD_VISION_MODEL`
(mặc định `gemini-3.5-flash`, độc lập model chatbot); trả OCR, triệu chứng
được nhận diện, vị trí bánh và ước lượng độ rõ. Không suy đoán mẫu xe từ ảnh.
Tên file không được dùng làm bằng chứng. Kết quả có cấu trúc được kiểm tra trước
khi đối chiếu dataset. OCR nguyên văn chỉ hiển thị như dữ liệu, không được chạy
hoặc dùng làm chỉ dẫn cho chatbot. Đây là căn cứ sơ bộ, chưa phải chẩn đoán.
Ngưỡng 0.8 hiện là tạm thời, chưa được hiệu chỉnh từ tập ảnh đủ lớn.
Triệu chứng từ Vision phải có chữ cảnh báo tương ứng trong OCR; các biểu tượng
READY/dây an toàn không có chữ cảnh báo không tự trở thành triệu chứng chính.
Thiếu khóa, lỗi xác thực, timeout hoặc ảnh không rõ dẫn đến hỏi lại/chuyển nhân viên.
Không có kết quả OCR giả khi nhà cung cấp lỗi.
Lỗi HTTP 503 được thử lại tối đa một lần; timeout hoặc các lỗi khác trả trạng thái
FAILED để chatbot yêu cầu thông tin thay thế.
Mô tả thiếu, nhiều cảnh báo hoặc nhiều mẫu xe không rõ được hỏi lại tối đa hai lượt,
sau đó chuyển nhân viên với risk UNKNOWN; dấu hiệu HIGH/CRITICAL được chuyển ngay.
Câu trả lời làm rõ được nối với mô tả trước trong cùng phiên của cùng khách hàng.
Ảnh upload có chủ sở hữu; ảnh cũ đã gắn hồ sơ chỉ được dùng bởi chủ hồ sơ,
ảnh cũ chưa có thông tin sở hữu cần tải lại. Bỏ metadata không che VIN/biển số
hoặc khuôn mặt trong các pixel; khách hàng cần tránh gửi ảnh chứa dữ liệu cá nhân.

Ba URL hiện là ảnh tham chiếu, không phải tập train: ảnh cụm đồng hồ chỉ cho biết
kiểm tra lốp sau bên phải, mẫu xe chưa xác minh; hai hình minh họa có chữ
`Tire pressure low` và `Tire pressure sensor fault`. Catalog đã sửa theo nội dung này.

Kiểm tra:

```powershell
.\.venv\Scripts\python.exe dataset/img_warning_taplo/verify_dataset.py
.\.venv\Scripts\python.exe -m pytest tests/test_api/test_dashboard_chat.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_api/test_dashboard_vision.py -q
.\.venv\Scripts\python.exe -X utf8 -m scripts.smoke_dashboard_vision
```

Smoke test dùng DB tạm, chạy cả upload và chat với ba ảnh công khai, kiểm tra OCR,
triệu chứng, vị trí bánh và loại phản hồi. Ảnh tải xuống chỉ lưu tạm trong quá trình
test; báo cáo nằm ở `.test-runs/dashboard-vision-live.json`. Cần khóa Gemini hợp lệ.
