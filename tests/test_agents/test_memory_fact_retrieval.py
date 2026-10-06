import pytest
from src.services.vehicle_context import resolve_vehicle_context, detect_memory_recall_query

def test_extract_soc_and_safety_status():
    # Câu kiểm thử thực tế từ 01_sales_to_incident lượt 7
    text = "Tôi đã dừng ở chỗ an toàn, pin còn 18%, không có đèn đỏ."
    prev = {"incident_model": "VF5", "is_incident": True}
    ctx = resolve_vehicle_context(text, prev)
    assert ctx.get("incident_fields", {}).get("soc") == "18%"

def test_extract_contact_preference():
    text = "Tôi đang đi xe VF5, pin còn 27%. Tôi muốn được liên hệ sau 17h."
    ctx = resolve_vehicle_context(text, {})
    assert ctx.get("incident_fields", {}).get("soc") == "27%"
    assert "17h" in str(ctx.get("incident_fields", {}).get("contact_preference"))

def test_detect_memory_recall_query():
    # Câu kiểm thử thực tế từ 01_sales_to_incident lượt 9
    text = "Quay lại sự cố vừa rồi, xe tôi là dòng nào và pin còn bao nhiêu?"
    ctx = {
        "incident_model": "VF5",
        "incident_fields": {"soc": "18%"},
        "is_incident": True,
    }
    is_recall, answer = detect_memory_recall_query(text, ctx)
    assert is_recall is True
    assert "VF5" in answer
    assert "18%" in answer
