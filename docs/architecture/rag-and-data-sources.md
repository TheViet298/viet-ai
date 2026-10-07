# RAG & Data Sources Specification

> **Người phụ trách chính:** Khôi (Data/RAG Engineer)  
> **Cập nhật lần cuối:** 2026-09-27
>
> **Trạng thái:** In Review (Đã kiểm tra lại metadata nguồn; FAQ/RAG chưa triển khai)

---

## 1. Nguyên tắc Quản trị Dữ liệu & Bản quyền (Data Governance)

> [!IMPORTANT]
> **Quy định Nghiêm ngặt về Nguồn Dữ liệu:**
> * **KHÔNG sử dụng** bất kỳ tài liệu nội bộ, mật hoặc chưa được công bố chính thức của VinFast nếu không có thẩm quyền.
> * **CHỈ sử dụng** các tài liệu công khai trên cổng thông tin chính thức của VinFast đã được nhóm mở, đọc và kiểm chứng thực tế.
> * **Không đưa các thông số chưa có nguồn xác thực vào demo/eval** (ví dụ: các ngưỡng phần trăm pin chưa có tài liệu đối chiếu).
> * Mọi đoạn trích dữ liệu (chunks) phải lưu trữ kèm metadata đầy đủ: **`source_id`**, **`title`**, **`url`**, **`verified_at`**, **`status_code`**, **`applicable_models`**, **`source_type`**.
> * `verified_at` là ngày kiểm tra nội dung trang, không mặc nhiên chứng minh HTTP 200. `status_code` có thể là `null` khi không xác nhận được mã HTTP đáng tin cậy. `applicable_models: []` nghĩa là chưa xác minh phạm vi theo từng dòng xe; không suy diễn là áp dụng cho mọi model.

---

## 2. Schema Metadata Chuẩn cho Nguồn Dữ liệu (Source Metadata Schema)

```json
{
  "source_id": "SRC-APP-001",
  "title": "Hướng dẫn sử dụng Ứng dụng VinFast cho ô tô điện (Phần 2)",
  "url": "https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast",
  "verified_at": "2026-09-27",
  "status_code": null,
  "applicable_models": [],
  "source_type": "OFFICIAL_APP_GUIDE",
  "summary": "Trang chính thức mô tả việc theo dõi trạng thái xe và sạc, cảnh báo, đặt lịch dịch vụ và theo dõi quá trình sửa chữa trên ứng dụng VinFast. Chưa xác minh khả năng áp dụng cho từng model."
}
```

---

## 3. Danh mục Nguồn Dữ liệu Công khai Đã Kiểm chứng (Verified Public Sources)

| ID Nguồn | Tên Tài liệu / Chủ đề | URL Nguồn Công khai | Ngày kiểm tra nội dung (`verified_at`) | HTTP Status | Dòng xe Áp dụng (`applicable_models`) | Loại Nguồn (`source_type`) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| `SRC-APP-001` | Hướng dẫn sử dụng Ứng dụng VinFast cho ô tô điện (Phần 2) | [vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast](https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast) | 2026-09-27 | Chưa xác nhận (`null`) | Chưa xác minh theo từng model (`[]`) | `OFFICIAL_APP_GUIDE` |

Nội dung trang đọc được qua trình duyệt ngày 2026-09-27. Lệnh kiểm tra HTTP trực tiếp từ môi trường phát triển nhận `403`, nên không dùng kết quả đó để khẳng định trang trả `200` cho mọi phương thức truy cập. Trước khi chạy pipeline nạp tài liệu tự động, cần kiểm tra lại quyền truy cập và lưu mã HTTP của chính lần nạp đó.

---

## 4. Cơ chế Trích dẫn (Citation) & Fallback khi Không có Nguồn

### 4.1. Quy tắc Trích dẫn Nguồn bắt buộc:
* Khi Agent trả lời câu hỏi dạng FAQ, câu trả lời phải kèm theo thẻ trích dẫn (citations) có cấu trúc:
```json
{
  "citations": [
    {
      "source_id": "SRC-APP-001",
      "title": "Hướng dẫn sử dụng Ứng dụng VinFast cho ô tô điện (Phần 2)",
      "url": "https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast",
      "verified_at": "2026-09-27",
      "status_code": null,
      "applicable_models": [],
      "source_type": "OFFICIAL_APP_GUIDE",
      "relevant_snippet": "Khách hàng có thể theo dõi trạng thái xe, kiểm tra dung lượng pin, đặt lịch dịch vụ và theo dõi tiến độ sửa chữa trực tiếp trên ứng dụng VinFast."
    }
  ]
}
```

### 4.2. Cơ chế Fallback (Khi RAG Score < Ngưỡng an toàn 0.70 hoặc chưa có nguồn xác thực):
> [!WARNING]
> **Tuyệt đối KHÔNG hallucinate (bịa đặt thông tin hoặc con số chính sách chưa xác thực).**
> 
> * **Hành vi bắt buộc:** Phản hồi khách hàng: *"Hiện tại hệ thống chưa có dữ liệu chính thức đã kiểm chứng về vấn đề này. Em đã ghi nhận và tạo hồ sơ để chuyên viên VinFast kiểm tra trực tiếp cho anh/chị."*
> * Chuyển đổi yêu cầu thành Ticket và đẩy vào Staff Queue (`Staff Reviewing`).

---

<!-- update info from feature/ai-long branch: merge giữ nguyên cả hai phiên bản để nhóm review sau. -->
<!-- Hai phần bên dưới có thể khác nhau về trạng thái, phạm vi hoặc số liệu; chưa chọn một phiên bản thay cho phiên bản còn lại. -->

<!-- Phiên bản feature/ai-khoi -->
## 5. Thứ tự triển khai

Flow 1 (`Charging/Battery`: tiếp nhận, làm rõ, tạo Case Brief, Staff Review, khách xem trạng thái) là ưu tiên trước. Metadata nguồn ở tài liệu này là phần chuẩn bị; FAQ/RAG hoàn chỉnh thuộc giai đoạn sau khi Flow 1 chạy xuyên suốt. Chỉ bật câu trả lời FAQ tự động khi đã có nguồn được nạp, kiểm tra trích dẫn và kiểm thử fallback khi không có nguồn.

<!-- Phiên bản feature/ai-long -->
## 5. Knowledge Hub Public

* Landing/FAQ/Policy chỉ hiển thị nội dung hoặc link từ nguồn VinFast đã kiểm chứng.
* Knowledge Hub không phải CMS và không tự crawl/cập nhật trong MVP.
* Nội dung public không mặc định được đưa hết vào Vector DB; chỉ index nguồn đã được Data/RAG kiểm duyệt.
* Không index raw ticket, chat history, ảnh hoặc location của Customer vào Knowledge Hub/RAG public. Nếu dùng insight từ case demo, phải biên soạn lại thành bài viết ẩn danh và được Staff duyệt.
