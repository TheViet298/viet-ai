"""Policy rows retain their own component and usage condition, never a neighbour's."""
import pytest

from src.services.answer_evidence import AnswerClaim, validate_answer_claims


# SRC-002 captured policy, Pin cao áp / Ắc-quy. Kept verbatim for the contract.
POLICY = '''Pin cao áp
Pin cao áp mua theo xe mới, sử dụng tiêu chuẩn:
VF 8, VF 9, Lạc Hồng 900 LX: 10 năm hoặc 200.000 km tùy theo điều kiện nào đến trước.
VF 3, VF 5, VF 6, VF 7: 8 năm hoặc 160.000 km tùy điều kiện nào đến trước.

Pin cao áp mua theo xe mới, xe đang hoặc đã từng sử dụng cho mục đích dịch vụ thương mại:
VF 3, VF 7, VF 8, VF 9: 3 năm hoặc 100.000 km tùy điều kiện nào đến trước.

Ắc - quy
Ắc quy 12V trên ô tô điện: 1 năm (không giới hạn quãng đường sử dụng).'''
CITATION = {'source_id': 'SRC-002', 'source_type': 'official_policy',
            'title': 'Chính sách bảo hành', 'relevant_snippet': POLICY}


def claim(value='10', unit='năm', subject='VF8 pin cao áp', conditions=None):
    return AnswerClaim(claim_key='warranty', value=value, unit=unit, subject=subject,
                       conditions=conditions or ['mua theo xe mới', 'sử dụng tiêu chuẩn'], source_ids=['SRC-002'])


def test_policy_header_and_condition_stay_with_numeric_row():
    assert validate_answer_claims([claim()], [CITATION], [])['supported']
    assert validate_answer_claims([claim('200.000', 'km')], [CITATION], [])['supported']


@pytest.mark.parametrize('bad', [
    claim('1'), claim('3'), claim(subject='VF5 pin cao áp'),
    claim(subject='VF8 2024 pin cao áp', conditions=['mua theo xe mới', '2024']),
    claim(conditions=['pin mua thay thế']),
    claim(conditions=['dịch vụ thương mại']),
    claim(subject='VF8 ắc quy'),
])
def test_policy_cannot_borrow_another_row_or_header(bad):
    assert not validate_answer_claims([bad], [CITATION], [])['supported']


def test_negative_textual_policy_does_not_become_affirmative():
    citation = {**CITATION, 'relevant_snippet': 'VF8 pin cao áp không được bảo hành khi can thiệp trái phép.'}
    statement = claim(value='được bảo hành khi can thiệp trái phép', unit='', conditions=['can thiệp trái phép'])
    assert not validate_answer_claims([statement], [citation], [])['supported']


def test_component_heading_with_colon_clears_previous_component():
    citation = {**CITATION, 'relevant_snippet': 'Pin cao áp\nVF8: 10 năm.\nẮc quy:\nVF8: 1 năm.'}
    bad = claim('1', conditions=['VF8'])
    assert not validate_answer_claims([bad], [citation], [])['supported']


@pytest.mark.parametrize('key,value,unit,condition,source', [
    ('charging_time', '30', 'phút', '10–70%', 'VF8 sạc DC 150 kW từ 10–70% trong 30 phút.'),
    ('range', '471', 'km', 'WLTP', 'VF8 Plus quãng đường 471 km theo chuẩn WLTP.'),
])
def test_scoped_charging_and_range_keep_measurement_condition(key, value, unit, condition, source):
    citation = {**CITATION, 'relevant_snippet': source}
    item = AnswerClaim(claim_key=key, value=value, unit=unit, subject='VF8',
                       conditions=[condition], source_ids=['SRC-002'])
    assert validate_answer_claims([item], [citation], [])['supported']
    wrong = item.model_copy(update={'conditions': ['NEDC' if key == 'range' else '20–80%']})
    assert not validate_answer_claims([wrong], [citation], [])['supported']
