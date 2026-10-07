from src.services.rag_service import RAGService, source_registry


def retrieve(text, query, source_id="SRC-002"):
    meta = {**source_registry()[source_id], "source_id": source_id, "applicable_models": "ALL"}
    rows = {"documents": [[text]], "metadatas": [[meta]], "distances": [[0.2]], "ids": [["evidence"]]}
    return RAGService().filter_results(rows, "VF8", query)


def test_general_warranty_rejects_perforation_and_paint():
    text = "Chính sách bảo hành\nÁp dụng cho VF8: bảo hành 10 năm với tấm kim loại bị xuyên thủng.\nSơn ngoại thất\nVF8: 10 năm không giới hạn km."
    assert retrieve(text, "VF8 được bảo hành bao lâu?")["status"] == "NO_SOURCE"


def test_warranty_conditions_cannot_be_answered_with_duration_only():
    text = "Thời hạn bảo hành Ô tô — điều kiện sử dụng tiêu chuẩn. VF8: 10 năm hoặc 200.000 km, tùy điều kiện nào đến trước."
    assert retrieve(text, "Điều kiện sử dụng tiêu chuẩn trong chính sách bảo hành VF8 là gì?")["status"] == "NO_SOURCE"


def test_whole_vehicle_conditions_reject_component_commercial_policy():
    text = "Chính sách bảo hành pin cho xe dịch vụ thương mại tiếp tục áp dụng sau chuyển nhượng.\nẮc-quy\nÔ tô điện: 1 năm."
    assert retrieve(text, "Điều kiện sử dụng tiêu chuẩn trong chính sách bảo hành VF8 là gì?")["status"] == "NO_SOURCE"


def test_appointment_description_is_not_a_procedure():
    text = "Hướng dẫn đặt lịch bảo dưỡng\nỨng dụng cho phép đặt lịch bảo dưỡng.\nKiểm tra cảnh báo lỗi\nBước 1: Truy cập mục cảnh báo lỗi."
    assert retrieve(text, "Hướng dẫn đặt lịch bảo dưỡng trên ứng dụng VinFast", "SRC-001")["status"] == "NO_SOURCE"


def test_incomplete_procedure_starting_at_step_two_is_rejected():
    text = "Đặt lịch bảo dưỡng\nBước 2: Chọn thời gian.\nBước 3: Xác nhận."
    assert retrieve(text, "Hướng dẫn đặt lịch bảo dưỡng", "SRC-001")["status"] == "NO_SOURCE"


def test_whole_vehicle_warranty_does_not_include_tire_section():
    text = "Thời hạn bảo hành Ô tô\nVF8: 10 năm hoặc 200.000 km tùy điều kiện nào đến trước.\nLốp theo xe\nÁp dụng chính sách riêng."
    result = retrieve(text, "VF8 được bảo hành bao lâu?")
    assert result["status"] == "SUCCESS"
    assert "200.000 km" in result["citations"][0]["relevant_snippet"]
    assert "Lốp" not in result["citations"][0]["relevant_snippet"]


def test_valid_appointment_retains_all_steps_without_unrelated_section():
    text = "Đặt lịch bảo dưỡng\nBước 1: Chọn dịch vụ.\nBước 2: Chọn xưởng.\nBước 3: Xác nhận.\n7.4. Kiểm tra cảnh báo lỗi\nBước 1: Mở cảnh báo lỗi."
    result = retrieve(text, "Hướng dẫn đặt lịch bảo dưỡng trên ứng dụng VinFast", "SRC-001")
    assert result["status"] == "SUCCESS"
    assert "Bước 3" in result["citations"][0]["relevant_snippet"]
    assert "cảnh báo lỗi" not in result["citations"][0]["relevant_snippet"]
