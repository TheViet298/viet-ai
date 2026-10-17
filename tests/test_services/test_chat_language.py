import pytest
from src.services import chat_language


@pytest.mark.parametrize('text,expected', [
    ('Does VinFast offer Mobile Service?', 'en'),
    ('Do you offer Mobile Service?', 'en'),
    ('Did VinFast receive my request?', 'en'),
    ('Do xe toi khong sac duoc', 'vi'),
])
def test_auxiliary_english_questions_select_english_without_breaking_vietnamese(text, expected):
    assert chat_language.detect_language(text) == expected


@pytest.mark.parametrize('query', ['Bạn có thể giúp gì cho tôi?', 'Phanh tái sinh hoạt động như thế nào?', 'Thời tiết ngày mai thế nào?'])
def test_vietnamese_accents_are_not_english_grammar(query):
    assert chat_language.detect_language(query, 'vi') == 'vi'


def test_requested_output_locale_does_not_change_input_understanding():
    assert chat_language.response_language('Xe VF8 có màu gì?', 'en', 'vi') == 'en'
    assert chat_language.response_language('Tell me about VF7', 'vi', 'en') == 'vi'
    assert chat_language.response_language('Please answer in English. VF8?', 'vi', 'vi') == 'en'


@pytest.mark.parametrize('text,previous,expected', [
    ('Tell me about VF7', 'vi', 'en'), ('tu van vf7', 'vi', 'vi'),
    ('Please answer in English. VF8 có màu gì?', 'vi', 'en'),
    ('Vui lòng trả lời bằng tiếng Việt. VF8?', 'en', 'vi'),
    ('Plus?', 'en', 'en'), ('Thank you, I understand now', 'vi', 'en'),
])
def test_language_is_explicit_or_inferred_without_treating_vietnamese_shorthand_as_english(text, previous, expected):
    function = getattr(chat_language, 'detect_language', None)
    assert function is not None
    assert function(text, previous) == expected


@pytest.mark.parametrize('text,expected', [
    ('Tell me about the VF7 Plus', 'tư vấn VF7 Plus'),
    ('What colors are available for the VF8 Plus?', 'VF8 Plus có những màu gì?'),
    ('I would like to book a test drive for the VF7', 'Tôi muốn đăng ký lái thử VF7'),
    ('Tomorrow morning in Hanoi. Has my booking been confirmed?', 'sáng ngày mai tại Hà Nội. Đã đặt lịch thành công chưa?'),
])
def test_english_intent_uses_same_canonical_query(text, expected):
    function = getattr(chat_language, 'canonical_query', None)
    assert function is not None
    assert function(text) == expected


def test_protected_translation_requires_exact_numbers_urls_and_case_ids():
    function = getattr(chat_language, 'protect_literals', None)
    assert function is not None
    source = 'VF8 Plus: 1.079.000.000 VNĐ, 475 km. https://vinfastauto.com/vn_vi CASE-abc123'
    masked, tokens = function(source)
    assert '1.079.000.000' not in masked and 'https://' not in masked
    assert chat_language.restore_literals(masked, tokens) == source
    with pytest.raises(ValueError):
        chat_language.restore_literals(masked.replace(next(iter(tokens)), 'invented'), tokens)

@pytest.mark.parametrize('query', [
    'What is the battery warranty of VF8 and is it transferable?',
    'Could you explain roadside coverage eligibility for my VF7?',
    'Can I transfer the battery warranty if I sell my VF8?',
])
def test_partial_canonical_mapping_still_requires_semantic_translation(query):
    mapped = chat_language.canonical_query(query)
    assert chat_language.needs_semantic_translation(mapped)


@pytest.mark.parametrize('query', [
    'Tell me about the VF7 Plus', 'What colors are available for the VF8 Plus?',
    'What is the on-road price of the VinFast VF8 Plus?',
])
def test_complete_canonical_mapping_does_not_require_semantic_translation(query):
    assert not chat_language.needs_semantic_translation(chat_language.canonical_query(query))

@pytest.mark.parametrize('extra', [' 999 km', ' https://evil.example', ' CASE-other', ' __LITERAL_999999__'])
def test_translation_cannot_append_new_unprotected_literals(extra):
    source = 'VF8 Plus: 475 km'
    masked, tokens = chat_language.protect_literals(source)
    with pytest.raises(ValueError):
        chat_language.restore_literals(masked + extra, tokens)


def test_translation_cannot_duplicate_or_reorder_protected_occurrences():
    masked, tokens = chat_language.protect_literals('VF8 Plus: 475 km')
    first, second = list(tokens)
    with pytest.raises(ValueError):
        chat_language.restore_literals(masked + first, tokens)
    with pytest.raises(ValueError):
        chat_language.restore_literals(second + first, tokens)


def test_regenerative_braking_canonical_phrase_does_not_need_a_second_translation():
    assert not chat_language.needs_semantic_translation(
        chat_language.canonical_query('How does regenerative braking work?'))


def test_safety_confirmation_is_not_retranslated_because_of_vietnamese_an():
    mapped = chat_language.canonical_query('I am in a safe place now')
    assert mapped == 'Tôi đã ở nơi an toàn'
    assert not chat_language.needs_semantic_translation(mapped)
    assert chat_language.needs_semantic_translation('I am in an unknown place')
