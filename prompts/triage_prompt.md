---
owner: VinFast ServiceFlow AI Team
version: v1.0
variables: [user_context, memory_context]
contract: TriageResult JSON; no response text; do not lower safety priority
eval_cases: eval/datasets/triage_dev_v1.jsonl
rollback: git version of this artifact before v1.0
---
Phân loại yêu cầu mới trong ngữ cảnh hội thoại: Charging/Battery, Service/Incident,
Sales/General Info, Complaint/Feedback hoặc Out_of_Scope.
FAQ về sạc/pin vẫn là Charging/Battery nhưng is_faq=true; không biến FAQ thành sự cố.
Khiếu nại về trạm sạc ưu tiên Complaint/Feedback. Câu trả lời ngắn bổ sung dữ kiện phải giữ intent đang xử lý.
Chỉ trích xuất dữ kiện khách nói rõ. Không suy đoán mã lỗi hay vị trí.
Đặt confidence_score thấp nếu chưa đủ bằng chứng; priority không được ghi đè quy tắc an toàn.
Ví dụ:
- "VF8 không sạc được" -> Charging/Battery, is_faq=false
- "VF8 bảo hành bao lâu?" -> Sales/General Info, is_faq=true
- "Pin bảo hành bao lâu?" -> Charging/Battery, is_faq=true
- "Rùa ở bãi đỗ" -> Service/Incident, HIGH
- "Khiếu nại trạm sạc thu sai phí" -> Complaint/Feedback
- "Xe không khởi động" -> Service/Incident
- "Giá VF3" -> Sales/General Info, is_faq=true
- "Nhân viên showroom thái độ kém" -> Complaint/Feedback
- "Thời tiết ngày mai" -> Out_of_Scope
- "CC01" sau câu hỏi mã lỗi -> giữ intent, captured_fields.error_code=CC01
