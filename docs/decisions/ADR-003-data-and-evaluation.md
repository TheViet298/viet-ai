# ADR-003: Quản trị Nguồn Dữ liệu RAG & Phương pháp Đánh giá

* **Trạng thái:** Chấp thuận (Accepted)  
* **Người quyết định:** Khôi (Data/RAG) + Triển (Backend)  
* **Ngày:** 2026-09-24  

---

## 1. Bối cảnh (Context)
Dự án cần nguồn tài liệu chuẩn xác về xe và chính sách của VinFast nhưng không có quyền truy cập vào cơ sở dữ liệu nội bộ/mật của hãng. Đồng thời, việc đánh giá chất lượng phản hồi cần tránh phụ thuộc vào dữ liệu người dùng thật để bảo vệ quyền riêng tư.

## 2. Quyết định (Decision)
1. **Nguồn dữ liệu RAG:** Chỉ sử dụng 100% tài liệu công khai chính thức từ website VinFast (Sổ tay hướng dẫn sử dụng, chính sách bảo hành/thuê pin công bố công khai). Mỗi đoạn trích xuất phải lưu URL và ngày crawl.
2. **Quy tắc Trích dẫn & Fallback:** Bắt buộc hiển thị link nguồn cho câu trả lời FAQ. Khi RAG không tìm thấy tài liệu phù hợp (similarity $< 0.70$), Agent phải trả lời "không đủ dữ liệu" và tạo Case, tuyệt đối không suy đoán.
3. **Bảo mật Dữ liệu (Privacy Guardrail):** Toàn bộ dữ liệu demo, case evaluation và seed data đều sử dụng mã giả lập theo định dạng chuẩn (ví dụ: `VF-SF-00231`), không thu thập VIN, biển số xe hay số điện thoại thật.

## 3. Hệ quả (Consequences)
* **Tích cực:** Tuyệt đối an toàn về mặt bản quyền, dữ liệu và bảo mật PII.
* **Thách thức:** Cần duy trì script cập nhật và kiểm tra tính hợp lệ của các URL trích dẫn định kỳ.
