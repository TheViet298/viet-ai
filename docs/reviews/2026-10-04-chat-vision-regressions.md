# Kiểm tra trả lời và định tuyến ảnh — 04/10/2026

## Hành vi đã kiểm tra

| Nhóm | Ví dụ / kết quả mong đợi |
|---|---|
| Kiến thức chung | Rùa vàng, ABS/ESC, TPMS, BMS, ADAS, phanh tái sinh; giải thích và ghi rõ chưa đối chiếu mẫu/đời xe |
| Khái niệm bổ sung | SOC/SOH, sạc AC/DC, dung lượng pin, kWh, mô-men xoắn; không bị chặn chỉ vì chứa “dung lượng” |
| So sánh / hỏi tiếp | “Phân biệt SOC và SOH”, sau SOH hỏi “Nó khác SOC thế nào?”, “Phân biệt ABS và ESC”, “ADAS?” |
| Nhiều yêu cầu | Tổng quan VF3–VF9 + giá lăn bánh + lái thử; mỗi phần được xử lý riêng |
| Thông tin riêng mẫu xe | Giá/thông số/chính sách vẫn cần nguồn; không lấy số liệu từ kiến thức chung |
| Sự cố thật | “Xe tôi bị mất phanh” vẫn qua an toàn khẩn cấp, không thành câu hỏi khái niệm |
| Upload auto | Dashboard/charger chỉ dùng OCR; exterior chỉ dùng CarDD; unknown yêu cầu làm rõ và không tạo hồ sơ |
| Vision lỗi / ít chắc chắn | JSON sai, timeout/lỗi HTTP, kết quả bị cắt, confidence thấp: không đoán loại ảnh |
| API chat lỗi | Không tạo tư vấn mẫu, citation, case ID hoặc khẳng định đã báo cứu hộ; giữ banner khẩn cấp cục bộ |

## Kết quả tự động

- `tests/test_agents` + `tests/test_api`: **287 passed** (22,45 giây).
- `tests/test_eval` + bốn file kiểm thử vision/CarDD: **47 passed, 6 subtests passed** (2,63 giây).
- `node --test frontend/tests/useChat-errors.test.cjs`: **7 passed**. Trước sửa, bốn tình huống lỗi và hai tình huống ảnh thất bại; sau sửa đạt.
- TypeScript `tsc --noEmit`: đạt.
- Ruff cho các module/test mới: đạt. API có lỗi E402 từ HEAD do helper nằm trước imports; chỉ sắp xếp import liên quan, không coi lint toàn file là đạt.
- `git diff --check`: kiểm tra lại trước bàn giao.

## Thử thật và UI

Vision thật nhận đúng hai ảnh táp-lô công khai và một ảnh ngoại thất công khai.
Ảnh trắng trả unknown; trong lượt cuối nguyên nhân là dịch vụ không sẵn sàng,
không dùng kết quả đó để đo khả năng nhận biết ảnh ngoài phạm vi.
Kết quả lưu `.test-runs/image-routing-live.json`.

UI trả đủ SOC/SOH, ghi chú kiến thức chung, không tạo hồ sơ.
Upload ảnh công khai `vehicle-oto.png` từ VinFast hiển thị
“Đã tự nhận diện: Ngoại thất xe — CarDD”; gửi ảnh trả lời chưa phát hiện
vùng hư hại đạt ngưỡng, không khẳng định xe nguyên vẹn. Bằng chứng:
`.test-runs/ui-auto-routing.png` và `.test-runs/ui-cardd-reply.png`.

## Giới hạn

Các test tự động phần lớn dùng mock cho dịch vụ bên ngoài; không chứng minh
mọi câu hỏi đều đúng. Mẫu ảnh thật còn nhỏ; ngưỡng định tuyến 0,8 chưa hiệu chỉnh.
Provider sinh văn bản vẫn có thể lỗi 503; khái niệm phổ biến có lời giải thích
cục bộ, câu khác có thể báo chưa hoàn thành thay vì tạo câu trả lời giả.
Ảnh riêng người dùng chưa được gửi sang Vision trong phép thử này vì kiểm tra
phê duyệt tự động từ chối truyền ảnh cụ thể đó tới dịch vụ bên ngoài.

Chưa triển khai nhận dạng dòng xe Vehicles; định tuyến ngoại thất chỉ chọn CarDD.

## Hiển thị tin nhắn ảnh

Ảnh gửi thành công được giữ trong tin nhắn khách bằng preview riêng của lượt gửi.
Lượt chỉ gửi ảnh không hiển thị câu mô tả tự động; nếu khách viết nội dung, hiển thị
ảnh kèm nội dung đó. Backend vẫn nhận attachment ID và câu yêu cầu phân tích,
preview không truyền thêm vào payload chat. Dữ liệu hiển thị hiện thuộc phiên UI;
chưa bổ sung tải lại lịch sử ảnh sau refresh.
