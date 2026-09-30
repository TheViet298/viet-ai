# RAG & Data Sources Specification

> **Người phụ trách chính:** Khôi (Data/RAG Engineer)  
> **Cập nhật lần cuối:** 2026-09-24  
> **Trạng thái:** In Review (Đã chuẩn hóa Source Metadata Schema & Verified Sources)

---

## 1. Nguyên tắc Quản trị Dữ liệu & Bản quyền (Data Governance)

> [!IMPORTANT]
> **Quy định Nghiêm ngặt về Nguồn Dữ liệu:**
> * **KHÔNG sử dụng** bất kỳ tài liệu nội bộ, mật hoặc chưa được công bố chính thức của VinFast nếu không có thẩm quyền.
> * **CHỈ sử dụng** các tài liệu công khai trên cổng thông tin chính thức của VinFast đã được nhóm mở, đọc và kiểm chứng thực tế.
> * **Không đưa các thông số chưa có nguồn xác thực vào demo/eval** (ví dụ: các ngưỡng phần trăm pin chưa có tài liệu đối chiếu).
> * Mọi đoạn trích dữ liệu (chunks) phải lưu trữ kèm metadata đầy đủ: **`source_id`**, **`title`**, **`url`**, **`verified_at`**, **`status_code`**, **`applicable_models`**, **`source_type`**.

---

## 2. Schema Metadata Chuẩn cho Nguồn Dữ liệu (Source Metadata Schema)

```json
{
  "source_id": "SRC-APP-001",
  "title": "Hướng dẫn sử dụng Ứng dụng VinFast",
  "url": "https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast",
  "verified_at": "2026-09-24",
  "status_code": 200,
  "applicable_models": ["VF3", "VF5", "VF6", "VF7", "VF8", "VF9", "e34"],
  "source_type": "OFFICIAL_APP_GUIDE",
  "summary": "Tài liệu mô tả các tính năng chính trên app: theo dõi tình trạng xe, quản lý pin/sạc, tiếp nhận cảnh báo, đặt lịch dịch vụ bảo dưỡng và theo dõi tiến độ dịch vụ trực tuyến."
}
```

---

## 3. Danh mục Nguồn Dữ liệu Công khai Đã Kiểm chứng (Verified Public Sources)

| ID Nguồn | Tên Tài liệu / Chủ đề | URL Nguồn Công khai | Ngày Kiểm chứng (`verified_at`) | HTTP Status | Dòng xe Áp dụng (`applicable_models`) | Loại Nguồn (`source_type`) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| `SRC-APP-001` | Hướng dẫn sử dụng Ứng dụng VinFast (Trạng thái xe, Pin/Sạc, Cảnh báo, Đặt lịch & Theo dõi dịch vụ) | [vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast](https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast) | 2026-09-24 | `2020` OK (200) | Tất cả các dòng xe điện VinFast | `OFFICIAL_APP_GUIDE` |

---

## 4. Cơ chế Trích dẫn (Citation) & Fallback khi Không có Nguồn

### 4.1. Quy tắc Trích dẫn Nguồn bắt buộc:
* Khi Agent trả lời câu hỏi dạng FAQ, câu trả lời phải kèm theo thẻ trích dẫn (citations) có cấu trúc:
```json
{
  "citations": [
    {
      "source_id": "SRC-APP-001",
      "title": "Hướng dẫn sử dụng Ứng dụng VinFast",
      "url": "https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast",
      "verified_at": "2026-09-24",
      "status_code": 200,
      "applicable_models": ["VF3", "VF5", "VF6", "VF7", "VF8", "VF9", "e34"],
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

## 5. Knowledge Hub Public

* Landing/FAQ/Policy chỉ hiển thị nội dung hoặc link từ nguồn VinFast đã kiểm chứng.
* Knowledge Hub không phải CMS và không tự crawl/cập nhật trong MVP.
* Nội dung public không mặc định được đưa hết vào Vector DB; chỉ index nguồn đã được Data/RAG kiểm duyệt.
