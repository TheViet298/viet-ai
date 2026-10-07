import pytest
from src.agents.nodes.triage_node import classify_request_kind

def test_unknown_error_code_and_shaking_steering_wheel():
    # Câu kiểm thử thực tế từ 04_unknown_incident lượt 1
    text = "Xe VF6 của tôi báo mã ZQX987, vô lăng rung khi chạy chậm."
    assert classify_request_kind(text) == "incident"

def test_unaccented_charging_failure():
    # Câu kiểm thử thực tế từ 13_spelling lượt 2
    text = "xe vf 5 cua toi khong sac duoc"
    assert classify_request_kind(text) == "incident"

def test_unaccented_operation_failure():
    assert classify_request_kind("xe vf8 cua toi dang bao ma loi la") == "incident"
    assert classify_request_kind("xe toi khong khoi dong duoc") == "incident"
    assert classify_request_kind("xe vf5 dang bao rua vang va chay yeu") == "incident"

def test_door_jam_is_incident():
    text = "Xe tôi bị kẹt cửa bên lái không mở được"
    assert classify_request_kind(text) == "incident"
