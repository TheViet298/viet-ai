def test_source_sections_preserve_instruction_and_qualifier():
    from scripts.refresh_agent_sources import source_sections

    text = "7. Cách đặt lịch dịch vụ\nThực hiện 5 bước:\nBước 1: Đặt dịch vụ\nBước 2: Chọn loại dịch vụ\nBước 3: Chọn địa điểm\nBước 4: Chọn thời gian\nBước 5: Xác nhận\n8. Chính sách khác\nĐiều kiện sử dụng tiêu chuẩn."
    chunks = source_sections(text)
    assert any('5 bước' in c and 'Bước 5' in c for c in chunks)
    assert all(not c.startswith('ước') for c in chunks)
