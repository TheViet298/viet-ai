# ADR-002: Cơ chế Triage bằng Quy tắc Cứng và Human-in-the-Loop (HITL)

* **Trạng thái:** Chấp thuận (Accepted)  
* **Người quyết định:** Long (AI) + Khôi (RAG/Data)  
* **Ngày:** 2026-09-24  

---

## 1. Bối cảnh (Context)
Nếu để LLM tự do quyết định trong các tình huống khẩn cấp (cháy nổ, mất phanh, rùa vàng trên cao tốc) hoặc các tranh chấp khiếu nại tài chính, hệ thống có nguy cơ phản hồi chậm hoặc ảo giác (hallucinate), dẫn đến hậu quả nghiêm trọng về an toàn và pháp lý.

## 2. Quyết định (Decision)
1. **Hard Safety Rules:** Tách riêng một lớp lọc từ khóa nguy hiểm bằng code/regex trước khi gửi request tới LLM. Nếu phát hiện rủi ro, kích hoạt ngay cảnh báo an toàn và đẩy priority lên `CRITICAL`.
2. **Bắt buộc Human Review (HITL):** 100% ticket sự cố kỹ thuật, khiếu nại và trường hợp có điểm tin cậy thấp ($< 0.60$) đều bắt buộc phải qua Service Agent Console để nhân viên phê duyệt hoặc chỉnh sửa trước khi tiến hành xử lý.
3. **Audit Log & AI Feedback:** Lưu vết toàn bộ thay đổi của Staff khi chỉnh sửa Case Brief để làm tập dữ liệu đánh giá (evaluation) và tinh chỉnh prompt/fine-tuning sau này.

## 3. Hệ quả (Consequences)
* **Tích cực:** Đảm bảo 100% tính an toàn và trách nhiệm giải trình.
* **Thách thức:** Cần xây dựng luồng trạng thái đồng bộ (`Staff Reviewing` $\rightarrow$ `In Progress`) mượt mà giữa Customer và Staff Console.
