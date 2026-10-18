# ServiceFlow — web demo độc lập

Giao diện chat tiếng Việt và bàn kỹ thuật, phục vụ trình diễn quy trình tư vấn/CSKH và tiếp nhận sự cố. Toàn bộ ứng dụng, cấu hình, dữ liệu mẫu và test nằm trong `demo/`.

## Chạy tại máy của bạn

Từ thư mục gốc repo:

```bash
bash demo/setup.sh
bash demo/run.sh
```

Mở **http://127.0.0.1:8765**. Dừng bằng `Ctrl+C`.

Script ưu tiên Python 3.11 nếu có; nếu không dùng `python3` đã cài. Cần Python từ 3.11. Không có dependency bên thứ ba, không cần npm, API key, Google API, ChromaDB hoặc dịch vụ cloud. Giao diện dùng HTML/CSS/JavaScript; server và SQLite dùng thư viện chuẩn Python. Font có fallback khi không có Internet.

`setup.sh` tạo `demo/.venv` và sao chép `.env.example` sang `.env` khi chưa có. Không ghi đè env có sẵn. Dữ liệu được lưu tại `demo/data/demo.db`, tự khởi tạo khi chạy. `.env`, virtual environment và database bị Git ignore. Thay cổng bằng `DEMO_PORT` trong `demo/.env`; đường dẫn SQLite tương đối được tính từ thư mục `demo/`.

## Luồng trình diễn

1. **Tư vấn:** gửi “Tôi cần tư vấn xe cho gia đình”. Trợ lý hỏi nhu cầu/số chỗ khi thiếu ngữ cảnh. Trả lời “Gia đình, 5 chỗ” để tra cứu, xếp hạng các bản ghi sản phẩm trong SQLite và hiển thị nguồn. UI hiển thị thông báo chờ trong lúc xử lý.
2. **CSKH:** gửi “Làm thế nào đặt lịch bảo dưỡng?”. Trợ lý tra cứu database và trả lời trích xuất kèm liên kết nguồn.
3. **Sự cố:** gửi “Xe không nhận sạc”. Trợ lý phân loại HIGH, hỏi dòng xe/trạng thái xe. Trả lời “VF8 đã dừng an toàn” để tạo hồ sơ. Có tối đa hai lượt hỏi bổ sung; thông tin còn thiếu được chuyển cùng hồ sơ.
4. **Khẩn cấp:** gửi “Xe đang bốc khói” hoặc “VF9 báo rùa vàng trên cao tốc”. Trợ lý gắn URGENT và tạo hồ sơ ngay, không đợi bổ sung ngữ cảnh.
5. **Con người xử lý:** mở “Bàn kỹ thuật”, chọn “Nhân viên tiếp nhận” rồi “Đánh dấu hoàn tất”. Trạng thái thay đổi trong SQLite và có audit. URGENT được đưa lên đầu hàng đợi. Đây là thao tác mô phỏng trong máy demo, chưa điều phối tới nhân viên VinFast thật.

## Dữ liệu và luật

- `datasets/rules.json`: từ khóa URGENT, quy tắc rùa vàng + ngữ cảnh nguy hiểm, các mức LOW/MEDIUM/HIGH, nhóm tư vấn/CSKH và giới hạn lượt hỏi. Các phủ định gần từ khóa như “không có khói” được xét trước khi kết luận URGENT.
- `datasets/knowledge.json`: 14 bản ghi demo (6 sản phẩm và 8 CSKH) lấy từ dữ liệu đã có trong repo. Dữ liệu và nguồn chưa được kiểm chứng lại trong task này; không đưa giá bán hoặc cam kết dịch vụ hiện hành vào câu trả lời.
- `store.py`: khởi tạo SQLite, lưu session/hội thoại/hồ sơ/audit và xếp hạng trích xuất theo từ khóa, dòng xe và số chỗ.
- `engine.py`: phân loại, giữ ngữ cảnh qua nhiều lượt, hỏi bổ sung, trả lời có nguồn hoặc tạo hồ sơ kỹ thuật.
- `app.py`: phục vụ web và API nội bộ của demo.
- `static/`: giao diện responsive, trạng thái chờ/lỗi, quick replies, nguồn tham khảo, ngữ cảnh và bàn kỹ thuật.

Tra cứu hiện là retrieval bằng từ khóa trong SQLite, chưa dùng vector embedding hoặc LLM. Khi không có bản ghi phù hợp, UI báo thiếu nguồn thay vì tự tạo câu trả lời. Không dùng demo làm báo cáo chất lượng benchmark; một số dữ liệu tham chiếu được lấy từ tập QA của repo.

## API để nối với hệ thống chính sau này

- `POST /api/chat`: `{ "message": "...", "session_id": null }`; trả `session_id`, `intent`, `priority`, `status`, `message`, `citations`, `context`, `trace`, `case_id`.
- `GET /api/cases`: hàng đợi demo.
- `POST /api/cases/action`: `{ "case_id": "DEMO-...", "action": "ACCEPT" }` hoặc `RESOLVE`.
- `GET /api/health`: trạng thái server.

Các request frontend tập trung trong hàm `request()` của `static/app.js`. Sau này có thể thay adapter này bằng API FastAPI của dự án, bổ sung login/RBAC và mapping schema. Demo hiện chỉ phục vụ máy cục bộ; bàn kỹ thuật chưa có authentication và không nên public trực tiếp. Khóa API LLM chỉ cần khi nhóm quyết định bổ sung câu trả lời sinh bởi mô hình; không đưa khóa vào JavaScript phía trình duyệt.

## Kiểm tra

```bash
demo/.venv/bin/python -m unittest discover -s demo/tests -v
node --check demo/static/app.js
```

Test dùng database tạm, kiểm tra ngữ cảnh, phân loại/mức độ, phủ định từ khóa khẩn cấp, bounded clarification, citations, session isolation, persistence, thứ tự hàng đợi và chuyển trạng thái.

Kết quả kiểm tra ngày 30/09/2026: 15 unit test đạt; cú pháp JavaScript và shell đạt. Kiểm tra HTTP thực tế và trình duyệt đạt cho tư vấn có nguồn, hỏi bổ sung, tạo hồ sơ HIGH/URGENT và nhân viên tiếp nhận/hoàn tất. Giao diện được kiểm tra ở desktop 1440px và mobile 390px, không tràn ngang hoặc có exception JavaScript chưa xử lý. Máy hiện dùng Python 3.14 vì chưa cài Python 3.11.
