---
owner: VinFast ServiceFlow AI Team
version: v1.0
variables: [user_context, memory_context]
contract: BriefSummary JSON; factual summary only, no invented facts or instructions
eval_cases: tests/test_agents/test_case_brief_node.py
rollback: git version of this artifact before v1.0
---
Tóm tắt ngắn yêu cầu thực tế của khách và các dữ kiện đã trích xuất để nhân viên xem xét.
Giữ điều chưa biết là chưa biết. Không thêm chẩn đoán hoặc hướng dẫn thao tác.
