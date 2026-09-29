# ADR-001: Phạm vi MVP & Định vị Hệ thống AI Agent

* **Trạng thái:** Chấp thuận (Accepted)  
* **Người quyết định:** Toàn đội dự án (Việt, Long, Triển, Khôi)  
* **Ngày:** 2026-09-24  

---

## 1. Bối cảnh (Context)
Trong các buổi làm việc ban đầu, đã có sự không đồng nhất về kỳ vọng đối với AI Agent: một số ý kiến muốn AI tự động chẩn đoán lỗi chuyên sâu và tự ra lệnh sửa chữa/cứu hộ cho xe. Tuy nhiên, việc tự động hóa hoàn toàn chẩn đoán kỹ thuật ô tô điện là bất khả thi trong phạm vi MVP và tiềm ẩn rủi ro an toàn nghiêm trọng.

## 2. Quyết định (Decision)
1. **Định vị chính xác:** Hệ thống là **AI Agent Tiếp nhận, Triage, Chuẩn hóa Case Brief và Hỗ trợ Bàn giao**, KHÔNG phải "AI sửa xe".
2. **Trọng tâm 4 Intent:**
   * Làm sâu 2 nhóm: `Charging/Battery` và `Service/Incident`.
   * Làm tinh gọn 2 nhóm: `Sales/General Info` (RAG FAQ) và `Complaint/Feedback` (Thu thập tối thiểu và chuyển người).
3. **Mốc triển khai:** Ưu tiên một Vertical Slice chạy E2E thông suốt trước ngày **29/09/2026** (Luồng: Không sạc được $\rightarrow$ Clarify $\rightarrow$ Case Brief $\rightarrow$ Staff Console $\rightarrow$ Cập nhật tiến độ).

## 3. Hệ quả (Consequences)
* **Tích cực:** Giữ đúng scope khả thi, tránh bị mentor/giám khảo chất vấn về tính an toàn và thẩm quyền xử lý lỗi cơ khí.
* **Thách thức:** Cần thiết kế giao diện Staff Console đủ tốt để chứng minh giá trị của Case Brief đối với nhân viên dịch vụ.
