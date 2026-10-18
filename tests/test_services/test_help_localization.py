import pytest

from src.models.schemas import ChatResponseData
from src.services.chat_language import canonical_query, needs_semantic_translation
from src.services.customer_localization import localize_response


@pytest.mark.parametrize('english, vietnamese', [
    ('Please explain public charging, charging fees and VinFast app features.',
     'Hướng dẫn cách sạc pin tại trạm sạc công cộng, biểu phí sạc và tính năng trên App VinFast.'),
    ('I would like to ask about battery warranty and scheduled maintenance.',
     'Tôi muốn hỏi chính sách bảo hành pin và lịch bảo dưỡng định kỳ.'),
])
def test_english_quick_reply_has_complete_canonical_input(english, vietnamese):
    assert canonical_query(english) == vietnamese
    assert not needs_semantic_translation(canonical_query(english))


@pytest.mark.asyncio
async def test_english_help_keeps_tariff_amounts_and_conditions_without_model(monkeypatch):
    from src.services import customer_localization as module
    async def no_translation(*args, **kwargs):
        pytest.fail('Reviewed quick replies must not require an LLM translation')
    monkeypatch.setattr(module, 'translate', no_translation)
    data = ChatResponseData(response_type='FAQ_ANSWER', message=(
        'Theo tài liệu VinFast:\n\n### Biểu phí sạc\n\n'
        '- Đơn giá sạc: 3.858 VNĐ/kWh (áp dụng từ ngày 19/03/2024).\n\n'
        '- Phí sử dụng dịch vụ trạm sạc bổ sung sau khi hoàn thành phiên sạc:\n\n'
        '- Miễn phí từ phút thứ 1 đến phút thứ 10\n\n'
        '- 1.000 đồng/phút từ phút thứ 11 đến phút thứ 60\n\n'
        '- 4.000 đồng/phút từ phút thứ 121 trở đi\n\n'
        'Đây là mức phí trong tài liệu đã xác minh ngày 2026-09-30. Cần kiểm tra biểu phí và ưu đãi áp dụng cho xe trên ứng dụng trước khi sạc.'))
    await localize_response(data, 'en', {})
    assert 'Charging fees' in data.message
    assert '3,858 VND/kWh' in data.message
    assert '1,000 VND/minute' in data.message and '4,000 VND/minute' in data.message
    assert '19/03/2024' in data.message and '2026-09-30' in data.message
    assert '11 to 60' in data.message and '121 onward' in data.message
    assert 'after the charging session has ended' in data.message


def test_unknown_or_unverified_text_is_not_given_a_canned_translation():
    from src.services.help_localization import english_help_answer
    assert english_help_answer('Theo tài liệu VinFast:\n\nPin được bảo hành trọn đời.') is None
    assert english_help_answer('Theo tài liệu VinFast:\n\nPin bao hanh tron doi.') is None
    assert english_help_answer('Theo tài liệu VinFast:\n\n__HELP_0__') is None


def test_reviewed_english_snippets_preserve_every_number():
    import json
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / 'fixtures/knowledge'
    for name in ('charging_guides.json', 'warranty_maintenance.json'):
        for record in json.loads((root / name).read_text(encoding='utf-8')):
            assert re.findall(r'\d+', record['relevant_snippet']) == re.findall(r'\d+', record['relevant_snippet_en'])
