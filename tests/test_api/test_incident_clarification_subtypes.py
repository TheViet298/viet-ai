import pytest
from src.api.customer import determine_incident_clarification_prompt

pytest_plugins = ["tests.test_api.test_chat_remediation"]

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


def test_vibrating_wheel_and_unknown_code_asks_operation_not_door():
    # Trường hợp "VF6 của tôi báo mã ZQX987, vô lăng rung" không được nhầm thành lỗi cửa/khóa
    text = "VF6 của tôi báo mã ZQX987, vô lăng rung"
    msg, suggested = determine_incident_clarification_prompt(text, car_label="VF6", error_code="ZQX987", charger_id=None, station_name=None)
    assert "cửa" not in msg.lower()
    assert "khóa" not in msg.lower()
    assert "trạm" not in msg.lower()
    assert "trụ" not in msg.lower()
    assert "vận hành" in msg.lower() or "rung" in msg.lower() or "an toàn" in msg.lower()


@pytest.mark.asyncio
async def test_turtle_flow_does_not_convert_to_charging_incident(client, chat_db):
    # Luồng rùa vàng khi báo dừng an toàn & SOC không được chuyển nhầm sang sự cố sạc
    c = client
    await c.post('/api/v1/customer/chat', json={'session_id': 'turtle-test', 'message': 'Xe tôi đang hiện rùa vàng và chạy yếu.'})
    await c.post('/api/v1/customer/chat', json={'session_id': 'turtle-test', 'message': 'Xe đang gặp sự cố là VF5, không phải VF6.'})
    r = await c.post('/api/v1/customer/chat', json={'session_id': 'turtle-test', 'message': 'Tôi đã dừng ở chỗ an toàn, pin còn 18%, không có đèn đỏ.'})
    data = r.json()['data']
    assert "sự cố sạc" not in data['message'].lower()
    assert "trụ sạc" not in data['message'].lower()
    assert "trạm sạc" not in data['message'].lower()
    assert "vận hành" in data['message'].lower() or "rùa vàng" in data['message'].lower()


@pytest.mark.asyncio
async def test_denied_cc01_clears_error_code_and_acknowledges_in_reply(client, chat_db):
    # Khách báo xe không còn báo CC01 nữa thì error_code phải được xóa bỏ khỏi hồ sơ
    from src.models.db_models import CaseBrief, Case
    db, _, _ = chat_db
    c = client
    await c.post('/api/v1/customer/chat', json={'session_id': 'cc01-test', 'message': 'Xe VF8 của tôi không sạc được ở trụ P01, lỗi CC01.'})
    await c.post('/api/v1/customer/chat', json={'session_id': 'cc01-test', 'message': 'Tôi nói nhầm, xe là VF5 và trụ P02, không phải P01.'})
    r = await c.post('/api/v1/customer/chat', json={'session_id': 'cc01-test', 'message': 'Xe không còn báo CC01 nữa nhưng vẫn không vào điện.'})
    data = r.json()['data']
    assert "mã lỗi: cc01" not in data['message'].lower()
    case = db.query(Case).filter_by(session_id='cc01-test').first()
    assert case is not None
    brief = db.query(CaseBrief).filter_by(case_id=case.id).first()
    assert brief is not None
    assert brief.captured_fields.get('error_code') is None
    assert brief.captured_fields.get('charger_id') == 'P02'
    assert brief.captured_fields.get('vehicle_model') == 'VF5'
