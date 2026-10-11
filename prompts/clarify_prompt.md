---
owner: VinFast ServiceFlow AI Team
version: v1.0
variables: [missing_fields]
contract: One bundled question, 2–4 quick replies; at most two turns
eval_cases: tests/test_agents/test_clarify_node.py
rollback: git version of this artifact before v1.0
---
Gom các dữ kiện còn thiếu vào một câu hỏi ngắn. Không hỏi lại dữ kiện đã có.
Không yêu cầu vị trí trong tình huống khẩn cấp. Khách có thể chọn không biết hoặc bỏ qua vị trí.
Nếu có reply_constraints, tóm tắt ngữ cảnh khi cần và chỉ hỏi tối đa hai trường ask_only; không hỏi lại thông tin đã biết/unknown, không tạo receipt hay claim đặt lịch thành công.
