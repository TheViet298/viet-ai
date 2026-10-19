# Kiểm thử phiên dài nhiều chủ đề — 19/10/2026

## Phạm vi và môi trường

Yêu cầu: trong cùng một phiên, gửi 10–30 tin nhắn người dùng, đổi nhiều chủ đề,
kiểm tra memory qua từng lượt. Mã nền: `P-142/feature/agent-long`, `e2cf28c`.
Áp dụng `python-testing`, `test-driven-development`, `systematic-debugging`,
`requesting-code-review` và `verification-before-completion`.

Chạy HTTP qua ASGI vào API thật, SQLite riêng cho từng test, người dùng xác thực
giả lập. Fixture tắt model bên ngoài. Không gọi Vercel, không kiểm tra factual
quality của model/RAG trực tuyến, không gửi cứu hộ hoặc đặt lịch thật.

## Ma trận và kết quả

**31/31 test đạt**: 1 kiểm tra dataset, 27 phiên dài và 3 ca hồi quy tập trung.
27 phiên gồm **540 tin nhắn người dùng + 540 phản hồi**, thêm **36 lần gửi lại
request trùng**. Độ dài 10/20/30 tính theo tin nhắn người dùng được chấp nhận;
không tính request gửi lại.

| Nhóm hội thoại | Độ dài | Cách gửi | Số phiên | Tổng lượt người dùng |
| --- | --- | --- | ---: | ---: |
| Tư vấn → so sánh → báo giá → dịch vụ → khiếu nại → tư vấn | 10/20/30 | Liên tục / nạp lại / gửi trùng | 9 | 180 |
| Dịch vụ → lái thử → sự cố sạc → đính chính → khẩn cấp | 10/20/30 | Liên tục / nạp lại / gửi trùng | 9 | 180 |
| Đổi Việt/Anh, nhiều chủ đề, UI locale ngược ngôn ngữ nhập | 10/20/30 | Liên tục / nạp lại / gửi trùng | 9 | 180 |

Mỗi phiên 10/20 tin nhắn là đoạn đầu của cùng kịch bản 30 tin nhắn.
Ba cách gửi:

- Liên tục: giữ nguyên phiên qua từng request.
- Nạp lại: expunge đối tượng `ChatSession` khỏi SQLAlchemy identity map giữa
  lượt, buộc đọc lại từ DB. Đây không phải restart tiến trình hoặc trình duyệt.
- Gửi trùng: mỗi 5 lượt gửi lại đúng request ID/nội dung; phản hồi phải giống
  hệt, không thêm tin nhắn, lượt memory hoặc request record.

Tập kịch bản đi qua đủ **15 goal**, đại diện các nhóm tư vấn, sạc, sự cố,
khiếu nại và ngoài phạm vi. Assertion so tập goal với dataset intent hiện có.

## Câu hỏi tiêu biểu trong cùng phiên

1. `Tư vấn VF8` → `so với VF3` → `so bản plus` → `so bản eco`.
2. `Giá lăn bánh VF8 Plus ở Hà Nội?` → `Không phải Plus, tôi chọn Eco`
   → `Không phải Hà Nội, đăng ký ở Đà Nẵng` → `Tôi chưa biết phiên bản`
   → `VF8 Plus, mua kèm pin, Đà Nẵng` → `Tôi đã nói rồi, còn thiếu gì?`.
3. Bảo hành pin → đổi sang ắc quy 12V → lịch bảo dưỡng → đổi mẫu xe → ứng dụng
   → biểu phí sạc → thời gian sạc → quãng đường → dung lượng pin.
4. Đặt lịch → bổ sung nơi/thời gian → hủy → tư vấn/màu xe → khiếu nại → bổ sung
   thành phố → ngoài phạm vi → trở lại so sánh xe.
5. Sau các câu dịch vụ: `Xe của tôi không sạc được` → `VF5`
   → `Trụ P01 tại Vincom Metropolis` → `Xe báo lỗi CC01, pin còn 35%`
   → `Không phải trụ P01, trụ P02` → `Xe không còn báo CC01 nữa`
   → `Tôi đã dừng ở nơi an toàn` → chuyển sang bảo hành.
6. Cuối phiên dài: báo bốc khói → đã ở nơi an toàn → đổi chủ đề → báo khói lại
   → `Bạn đã gửi cứu hộ chưa?`; không tự tạo xác nhận đã gọi cứu hộ.
7. `Please explain public charging, charging fees and VinFast app features.`:
   kiểm tra ba mục trả lời riêng; tiếp tục đặt lái thử, hủy và so sánh bằng VI/EN.

Đầy đủ **90 bước gốc** và kỳ vọng từng bước:
[dataset](../../eval/datasets/long_multitopic_memory_v1.json).
Tổng hợp kết quả từng phiên:
[results](../../eval/results/long_multitopic_memory_v1.json).

## Assertion ở từng lượt

- Goal, chủ thể, slot mới/sửa/rút lại/chưa biết; bỏ slot cũ khi đổi chủ đề.
- Các thẻ xe và cấu hình so sánh đúng cặp xe/phiên bản sau nhiều lần đổi chủ đề.
- Ngôn ngữ theo câu nhập dù locale gửi ngược; tiêu đề từng ý của câu nhiều ý.
- Trạng thái đặt lịch/hủy, cảnh báo khẩn cấp và không tự xác nhận hành động.
- Mã hồ sơ sự cố không đổi qua bổ sung thông tin, sửa mã trụ, rút mã lỗi và
  xác nhận đã ở nơi an toàn.
- Memory lưu đúng lượt, câu hỏi và phản hồi cuối cùng.
- History có đúng chuỗi câu gốc, thứ tự CUSTOMER/AGENT xen kẽ, nội dung, thẻ,
  nguồn và ngôn ngữ đúng như phản hồi đã gửi.
- Buffer tối đa 10 tin, bằng chứng summary tối đa 20; các phiên thực sự kích
  hoạt compact, vẫn kiểm tra ngữ cảnh ở những lượt sau compact.
- Request trùng không làm thay đổi memory hay số hàng tin nhắn.

Trace JSON từng lượt được lưu trong thư mục pytest tạm trước assertion, để
giữ được lượt gây lỗi nếu test dừng.

## Lỗi phát hiện và sửa

1. **Nguồn trong history lệch câu trả lời** sau đổi Eco/Plus hoặc dịch ngôn ngữ:
   lưu lại citations cuối cùng sau bước localize cùng các metadata khác.
2. **Tin nhắn đảo thứ tự** khi đồng hồ đứng yên/lùi hoặc hai lượt quá sát nhau:
   timestamp CUSTOMER mới luôn sau tin cuối phiên; AGENT sau CUSTOMER 1 ms,
   áp dụng mọi nhánh trả lời, gồm cảm ơn, ngoài phạm vi, nearby và guest.
   Ca hồi quy dùng đồng hồ cố định ở tương lai để tái hiện chắc chắn.
3. **Mất mục tiêu sự cố** sau `Xe không còn báo CC01 nữa` hoặc `Tôi đã dừng ở
   nơi an toàn`: xử lý rút lại thông tin như cập nhật ngữ cảnh; xác nhận vị trí
   an toàn giữ mục tiêu sự cố. Không tự kết luận đã xử lý xong.

Đã tái hiện lỗi trước sửa và chạy lại sau sửa. Review độc lập không ghi nhận
finding cần sửa; reviewer không chạy lại test thay cho lượt xác minh này.

## Chạy lại

```powershell
python -m pytest tests/test_api/test_long_multitopic_memory.py -q --basetemp=.test-runs/long-memory --junitxml=.test-runs/long-memory.xml
python -m pytest tests -q --junitxml=.test-runs/backend.xml
```

Test chính: `tests/test_api/test_long_multitopic_memory.py`.

## Hồi quy toàn hệ thống

- Backend: **1947 passed, 7 failed, 4 skipped**, 6 subtests passed.
- Frontend: **177 passed, 0 failed** (`node --test tests/*.test.cjs`).
- 7 test lỗi trùng đúng bộ lỗi trước thay đổi (`1916 passed, 7 failed,
  4 skipped`): 3 test Langfuse root ở API, 3 test observability usage và
  1 test diagnostics khi 10 model request cùng timeout. Không xuất hiện test
  hồi quy mới trong lần chạy này. Bộ backend tổng thể vẫn chưa xanh.
- 4 skip giữ nguyên: thiếu snapshot service points (2), thư mục crawl (1)
  và notebook training (1).

Các kết quả này kiểm tra logic ở mã nguồn cục bộ, chưa phải xác nhận deploy
production, restart tiến trình thật, kiểm thử trình duyệt hay tải nhiều người
dùng. Log cục bộ: `.test-runs/long-memory-full.log`,
`.test-runs/long-memory-frontend.log` và `.test-runs/long-memory-final.log`.
