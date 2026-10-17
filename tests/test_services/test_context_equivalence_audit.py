from scripts.audit_context_equivalence import build_cases, check_contract


def test_negated_abs_question_accepts_concept():
    dataset = {'groups': [{'id': 'negation', 'domain': 'safety_negation',
                          'goal': [None, 'incident'], 'variants': ['Xe không mất phanh, ABS là gì?'],
                          'expectations': {'0': {'goal': ['concept']}}}], 'scenarios': []}
    case = build_cases(dataset, ['fresh'])[0]
    assert check_contract(case, {'http_status': 200, 'data': {'message': 'ABS giúp chống bó cứng phanh'},
                                 'context': {'active_goal': 'concept'}})['goal']


def test_routing_pass_does_not_certify_charging_price_answer():
    checks = check_contract({'domain': 'charging_network', 'cost_subject': 'charging'},
                            {'http_status': 200, 'data': {'message': 'VF8 Plus: giá niêm yết 1.079.000.000 VNĐ'}})
    assert checks['http']
    assert checks['answer_cost_subject'] is False


def test_negated_smoke_maintenance_override_changes_only_exact_variant_contracts():
    from copy import deepcopy
    import json
    from pathlib import Path
    dataset = json.loads((Path(__file__).resolve().parents[2] / 'eval/datasets/context_equivalence_v1.json').read_text(encoding='utf-8'))
    group = next(g for g in dataset['groups'] if g['id'] == 'hypothetical-hazard')
    assert group['variants'][4] == 'Xe không bốc khói, tôi hỏi cách bảo dưỡng'
    assert group['expectations']['4'] == {'goal': ['maintenance']}
    assert group['expectations']['3'] == {'goal': ['concept']}
    baseline = deepcopy(dataset)
    next(g for g in baseline['groups'] if g['id'] == group['id'])['expectations'].pop('4')
    before = {c['id']: c for c in build_cases(baseline, ['fresh', 'after_quote'])}
    after = {c['id']: c for c in build_cases(dataset, ['fresh', 'after_quote'])}
    changed = []
    for case_id, case in after.items():
        # The inherited expectations lookup is audit metadata, not a contract.
        old = {k: v for k, v in before[case_id].items() if k != 'expectations'}
        new = {k: v for k, v in case.items() if k != 'expectations'}
        if old != new:
            changed.append(case_id)
            assert old['goal'] == [None, 'incident']
            assert new['goal'] == ['maintenance']
            assert {k: v for k, v in old.items() if k != 'goal'} == {k: v for k, v in new.items() if k != 'goal'}
            assert case['cards'] == 'forbidden' and case['emergency'] is False
    assert set(changed) == {'hypothetical-hazard-4-fresh', 'hypothetical-hazard-4-after_quote'}
