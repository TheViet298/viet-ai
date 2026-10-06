import pytest
from src.services.vehicle_context import resolve_vehicle_context

def test_correction_vf5_not_vf6():
    # Câu kiểm thử thực tế từ 01_sales_to_incident lượt 6
    text = "Xe đang gặp sự cố là VF5, không phải VF6."
    prev = {"incident_model": None, "is_incident": True, "models": ["VF6"]}
    ctx = resolve_vehicle_context(text, prev)
    assert ctx["incident_model"] == "VF5"
    assert "VF6" not in ctx.get("models", [])

def test_ownership_with_preference_term():
    # Câu kiểm thử từ 11_long_memory lượt 1: không được loại bỏ ownership chỉ vì có chữ "muốn" ở mệnh đề sau
    text = "Tôi đang đi xe VF5, pin còn 27%. Tôi muốn được liên hệ sau 17h."
    ctx = resolve_vehicle_context(text, {})
    assert ctx["owned_model"] == "VF5"

def test_correction_scope_switches_model():
    # Trường hợp 06_correction_scope lượt 2
    text = "Sự cố xảy ra trên xe VF5 tại trụ P02, không phải VF8 P01"
    prev = {"incident_model": "VF8", "is_incident": True, "models": ["VF8"]}
    ctx = resolve_vehicle_context(text, prev)
    assert ctx["incident_model"] == "VF5"
