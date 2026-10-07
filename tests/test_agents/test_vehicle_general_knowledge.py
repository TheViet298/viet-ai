import pytest

from src.agents.nodes.general_node import general_node
from src.agents.nodes.triage_node import triage_node


@pytest.mark.asyncio
@pytest.mark.parametrize("question,expected", [
    ("Biểu tượng con rùa vàng là gì?", "giới hạn công suất"),
    ("ABS trên xe là gì?", "bó cứng"),
    ("TPMS là gì trên xe?", "áp suất lốp"),
    ("Giải thích ABS trên xe", "bó cứng"),
    ("Khi nào xe tự giới hạn công suất?", "giới hạn công suất"),
    ("SOC là gì?", "mức pin"),
    ("SOH là gì?", "sức khỏe"),
    ("Sạc AC và DC khác nhau như thế nào?", "xoay chiều"),
    ("Dung lượng pin là gì?", "năng lượng"),
    ("kWh trên pin xe nghĩa là gì?", "năng lượng"),
    ("Mô-men xoắn của xe là gì?", "lực quay"),
])
async def test_common_car_explanations_work_without_provider_or_sources(question, expected):
    triage = await triage_node({"latest_user_message": question, "user_role": "customer"})
    assert triage["is_general_query"]
    result = await general_node({"latest_user_message": question})
    assert expected in result["response"].casefold()
    assert "kiến thức chung" in result["response"].casefold()
    assert not result["rag_citations"]
    assert not result["needs_staff_review"]


@pytest.mark.asyncio
@pytest.mark.parametrize("question", [
    "Dung lượng pin VF8 bao nhiêu kWh?", "VF8 được bảo hành bao lâu?",
    "Giá lăn bánh VF8 bao nhiêu?", "Xe tôi đang hiện rùa vàng và không đi được",
    "Tháo pin cao áp trên xe như thế nào?", "Thời tiết hôm nay là gì?",
])
async def test_specific_claims_incidents_and_foreign_topics_never_use_common_knowledge(question):
    result = await triage_node({"latest_user_message": question, "user_role": "customer"})
    assert not result["is_general_query"]
