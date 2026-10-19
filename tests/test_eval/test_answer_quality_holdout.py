from eval.answer_quality import grade_holdout_row


def test_holdout_requires_content_status_language_and_source():
    case = {'category': 'answerable', 'language': 'en', 'expected_status': 'answered',
        'expected_concepts': [['10 years', '10-year'], ['200,000 km', '200000 km']],
        'evidence': [{'source_id': 'SRC-002'}], 'forbidden_concepts': ['unlimited']}
    output = {'response': '10 years or 200,000 km', 'language': 'en',
        'answer_status': 'answered', 'sources': [{'source_id': 'SRC-002'}]}
    assert grade_holdout_row(case, output)['passed']
    for patch in [{'response': 'I cannot answer'}, {'answer_status': 'needs_data'},
                  {'language': 'vi'}, {'sources': []}, {'response': '10 years or 200,000 km unlimited'}]:
        assert not grade_holdout_row(case, {**output, **patch})['passed']


def test_boundary_abstention_does_not_pass_wrong_confirmation():
    case = {'category': 'boundary', 'language': 'vi', 'expected_status': 'external_action_required',
            'expected_concepts': [['chưa xác nhận', 'chưa đặt']], 'forbidden_concepts': ['đã đặt thành công']}
    assert not grade_holdout_row(case, {'response': 'đã đặt thành công', 'language': 'vi',
        'answer_status': 'external_action_required', 'sources': []})['passed']



def test_old_multitopic_labels_cover_every_authored_turn():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    scenarios = json.loads((root / 'eval/datasets/long_multitopic_memory_v1.json').read_text(encoding='utf-8'))
    labels = json.loads((root / 'eval/datasets/long_multitopic_quality_labels_v1.json').read_text(encoding='utf-8'))['cases']
    expected = {s['id'] + ':' + str(n): step for s in scenarios for n, step in enumerate(s['turns'], 1)}
    assert len(labels) == len(expected) == 90
    assert {r['id'] for r in labels} == set(expected)
    for row in labels:
        assert row['question'] == expected[row['id']]['message']
        assert row['goal'] == expected[row['id']]['goal']
        assert row['expected_answer_classes'] and row['evidence']['basis']
        assert {'model', 'variant', 'year', 'component'} <= row['scope'].keys()
