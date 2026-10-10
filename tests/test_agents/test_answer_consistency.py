from src.services.answer_evidence import AnswerClaim, validate_answer_claims


def test_history_pin_cannot_support_range_number():
    claim = AnswerClaim(claim_key='range', value='500', unit='km', subject='VF8', source_ids=['s'])
    result = validate_answer_claims([claim], [{'source_id': 's', 'relevant_snippet': 'VF8: lịch sử dùng pin, đã chạy 500 km.'}], [])
    assert not result['supported']


def test_exclusions_cannot_support_warranty_duration():
    claim = AnswerClaim(claim_key='warranty', value='10', unit='năm', subject='pin cao áp VF8', source_ids=['s'])
    assert not validate_answer_claims([claim], [{'source_id': 's', 'relevant_snippet': 'Pin không bảo hành nếu dùng sai. Xe có tuổi thọ 10 năm.'}], [])['supported']


def test_conditions_and_prior_value_conflict_are_explicit():
    old = AnswerClaim(claim_key='range', value='500', unit='km', subject='VF8', conditions=['WLTP'], source_ids=['s'])
    new = AnswerClaim(claim_key='range', value='450', unit='km', subject='VF8', conditions=['WLTP'], source_ids=['s'])
    result = validate_answer_claims([new], [{'source_id': 's', 'relevant_snippet': 'VF8 quãng đường một lần sạc 450 km WLTP.'}], [old])
    assert result['supported']
    assert result['conflicts']


def test_price_version_and_from_qualifier_are_required():
    claim = AnswerClaim(claim_key='price', value='1.079.000.000', unit='VNĐ', subject='VF8 Plus', source_ids=['s'])
    snippet = {'source_id': 's', 'relevant_snippet': 'VF8 Plus giá bán từ 1.079.000.000 VNĐ.'}
    assert not validate_answer_claims([claim], [snippet], [])['supported']
    claim.conditions = ['từ']
    assert validate_answer_claims([claim], [snippet], [])['supported']
    snippet['relevant_snippet'] = 'VF8 Eco giá bán từ 1.079.000.000 VNĐ.'
    assert not validate_answer_claims([claim], [snippet], [])['supported']


def test_numeric_boundary_does_not_accept_50_inside_450():
    claim = AnswerClaim(claim_key='range', value='50', unit='km', subject='VF8', conditions=['WLTP'], source_ids=['s'])
    assert not validate_answer_claims([claim], [{'source_id': 's', 'relevant_snippet': 'VF8 quãng đường một lần sạc 450 km WLTP.'}], [])['supported']


def test_currency_multipliers_are_extracted_and_validated():
    from src.services.answer_evidence import extract_numeric_claims
    citation = {'source_id': 's', 'relevant_snippet': 'VF8 Plus giá bán từ 1,2 tỷ đồng.'}
    claims = extract_numeric_claims(citation['relevant_snippet'], [citation], 'VF8 Plus')
    assert len(claims) == 1
    assert claims[0].unit == 'tỷ đồng'
    assert validate_answer_claims(claims, [citation], [])['supported']


def test_decimal_value_is_not_collapsed_into_integer():
    claim = AnswerClaim(claim_key='capacity', value='49.5', unit='kWh', subject='VF8', source_ids=['s'])
    assert not validate_answer_claims([claim], [{'source_id': 's', 'relevant_snippet': 'VF8 dung lượng pin 495 kWh.'}], [])['supported']


def test_old_price_article_does_not_supply_current_price():
    claim = AnswerClaim(claim_key='price', value='1.492.000.000', unit='VNĐ', subject='VF8 Plus', source_ids=['s'])
    assert not validate_answer_claims([claim], [{'source_id': 's', 'relevant_snippet': 'Năm 2022 VF8 Plus giá bán 1.492.000.000 VNĐ.'}], [])['supported']


def test_price_including_battery_cannot_use_excluding_battery_evidence():
    from src.services.answer_evidence import extract_numeric_claims
    citation = {'source_id': 's', 'relevant_snippet': 'VF8 Plus giá bán không bao gồm pin là 1.200.000.000 VNĐ.'}
    claims = extract_numeric_claims('VF8 Plus giá mua kèm pin là 1.200.000.000 VNĐ.', [citation], 'VF8 Plus')
    assert not validate_answer_claims(claims, [citation], [])['supported']


def test_interval_requires_both_endpoints_in_evidence():
    from src.services.answer_evidence import extract_numeric_claims
    citation = {'source_id': 's', 'relevant_snippet': 'VF8 quãng đường một lần sạc 450 km WLTP.'}
    claims = extract_numeric_claims('VF8 quãng đường một lần sạc 400-450 km WLTP.', [citation], 'VF8')
    assert not validate_answer_claims(claims, [citation], [])['supported']


def test_pin_duration_cannot_use_whole_vehicle_duration():
    claim = AnswerClaim(claim_key='warranty', value='10', unit='năm', subject='VF8 pin cao áp', source_ids=['s'])
    citation = {'source_id': 's', 'title': 'Chính sách bảo hành', 'relevant_snippet': 'Xe VF8 bảo hành 10 năm.'}
    assert not validate_answer_claims([claim], [citation], [])['supported']
    citation['relevant_snippet'] = 'Pin cao áp VF8 bảo hành 10 năm.'
    assert validate_answer_claims([claim], [citation], [])['supported']
