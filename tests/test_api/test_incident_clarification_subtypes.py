import pytest
from src.api.customer import determine_incident_clarification_prompt

def test_turtle_clarification_asks_operational_status_not_charger():
    # Trường hợp 03_concepts lượt 7-8 và 01_sales_to_incident lượt 5
    text = "Xe tôi đang hiện rùa vàng và chạy yếu."
    msg, suggested = determine_incident_clarification_prompt(text, car_label="VF6", error_code=None, charger_id=None, station_name=None)
    assert "trạm sạc" not in msg.lower()
    assert "trụ" not in msg.lower()
    assert "an toàn" in msg.lower() or "vận hành" in msg.lower() or "di chuyển" in msg.lower()

def test_door_jam_clarification_asks_door_and_safety_not_charger():
    # Trường hợp 06_correction_scope lượt 4
    text = "Xe VF6 khác bị kẹt cửa bên lái không mở được"
    msg, suggested = determine_incident_clarification_prompt(text, car_label="VF6", error_code=None, charger_id=None, station_name=None)
    assert "trạm sạc" not in msg.lower()
    assert "trụ" not in msg.lower()
    assert "cửa" in msg.lower()

def test_charging_failure_asks_charger_info_when_charging_indicated():
    text = "Xe tôi cắm sạc nhưng không vào điện, trụ nháy đỏ"
    msg, suggested = determine_incident_clarification_prompt(text, car_label="VF5", error_code=None, charger_id=None, station_name=None)
    assert "trạm" in msg.lower() or "trụ" in msg.lower() or "mã lỗi" in msg.lower()
