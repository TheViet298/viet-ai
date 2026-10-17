"""Regression tests for trustworthy golden scoring and model attribution."""
import json
from pathlib import Path

import pytest

from eval.golden import evaluate_conversation, evaluate_turn
from scripts.run_live_model_eval import evaluate_live


def test_one_canonical_golden_dataset_preserves_all_cases():
    from scripts import run_golden_cloud_eval, run_golden_v2_eval
    root = Path(__file__).resolve().parents[2]
    target = root / 'eval/datasets/golden_testcases.jsonl'
    assert target.exists()
    cases = [json.loads(line) for line in target.read_text(encoding='utf-8').splitlines() if line.strip()]
    assert len(cases) == len({c['id'] for c in cases}) == 190
    assert sum(c['id'].startswith('GOLD-') for c in cases) == 60
    assert sum(c['id'].startswith('GOLD2-') for c in cases) == 120
    assert run_golden_cloud_eval.DATASET == run_golden_v2_eval.DATASET == target
    assert len(run_golden_v2_eval.load_cases()) == 190
    assert all(c['kind'] for c in run_golden_v2_eval.load_cases())
    assert not (target.parent / 'golden_testcases_v1.jsonl').exists()
    assert not (target.parent / 'golden_testcases_v2.jsonl').exists()


def test_greeting_and_nine_english_cases_check_customer_response_language():
    from scripts.run_golden_v2_eval import load_cases
    cases = [c for c in load_cases() if c['id'].startswith('LANG-')]
    assert len(cases) == 10
    assert sum(c['category'] == 'greeting' for c in cases) == 1
    assert sum(c['category'] == 'english' for c in cases) == 9
    assert all(c['kind'] == 'customer_chat' for c in cases)
    for case in cases:
        for turn in case['turns']:
            assert turn['expected']['language'] in {'vi', 'en'}
            assert 'message' in turn['nonempty']


@pytest.mark.parametrize('actual,expected', [(1, True), (False, 0), ({'flag': 1}, {'flag': True})])
def test_contract_rejects_boolean_number_confusion(actual, expected):
    assert not all(c['passed'] for c in evaluate_turn({'value': actual}, {'expected': {'value': expected}}))


@pytest.mark.parametrize('contract', [{'expected': {}}, {'expected': {}, 'containz': {'reply': ['safe']}}])
def test_empty_or_misspelled_contract_cannot_pass(contract):
    assert not all(c['passed'] for c in evaluate_conversation({'turns': [{}]}, {'turns': [contract]}))


def test_nonobject_turn_cannot_satisfy_absence_only_contract():
    assert not all(c['passed'] for c in evaluate_turn(None, {'expected': {}, 'forbidden': ['bad']}))


def test_approved_alternative_phrases_do_not_relax_required_facts():
    contract = {'expected': {'priority': 'HIGH'},
                'contains_any': {'reply': [['nhân viên xác nhận', 'nhân viên sẽ xác nhận'], ['CC01']]}}
    assert all(c['passed'] for c in evaluate_turn({'priority': 'HIGH', 'reply': 'Nhân viên sẽ xác nhận mã CC01'}, contract))
    assert not all(c['passed'] for c in evaluate_turn({'priority': 'HIGH', 'reply': 'Nhân viên sẽ xác nhận'}, contract))


def test_forbidden_customer_promises_do_not_reject_quoted_customer_input():
    contract = {'expected': {'needs_staff_review': True}, 'not_contains': {'reply': ['đã điều phối cứu hộ']}}
    output = {'needs_staff_review': True, 'reply': 'Chuyên viên sẽ kiểm tra.',
              'case_brief': {'summary': 'Khách yêu cầu nói đã điều phối cứu hộ.'}}
    assert all(c['passed'] for c in evaluate_turn(output, contract))
    assert not all(c['passed'] for c in evaluate_turn({**output, 'reply': 'Đã điều phối cứu hộ'}, contract))


@pytest.mark.parametrize('model,prompt', [('wrong-model', 'general'), ('gpt-4o-mini', 'normalization')])
def test_live_evidence_must_match_model_and_prompt(model, prompt):
    rows = [{'id': 'g', 'type': 'GENERATION', 'model': model, 'endTime': 'now',
             'usageDetails': {'total': 3}, 'totalCost': .001, 'metadata': {'prompt_name': prompt}},
            {'id': 'p', 'name': 'llm.outcome', 'metadata': {'outcome': 'parsed', 'prompt_name': prompt}}]
    case = {'kind': 'chat', 'expected_model': 'gpt-4o-mini', 'expected_prompt': 'general'}
    assert evaluate_live(case, {'http_status': 200, 'response': {'reply': 'fallback'}}, rows)['status'] != 'PASS'


def test_hard_dataset_has_reviewable_diverse_cases():
    from collections import Counter
    target = Path(__file__).resolve().parents[2] / 'eval/datasets/golden_testcases.jsonl'
    assert target.exists(), 'The approved hard-case dataset must exist'
    cases = [case for line in target.read_text(encoding='utf-8').splitlines() if line.strip()
             if (case := json.loads(line))['id'].startswith('GOLD2-')]
    assert len(cases) == len({c['id'] for c in cases}) == 120
    assert Counter(c['category'] for c in cases) == {
        'safety': 24, 'triage': 16, 'rag': 24, 'multiturn': 24, 'normalization': 16, 'vision': 16}
    root = target.parents[2]
    for case in cases:
        assert case['label_status'] == 'draft_policy_review'
        assert case['difficulty'] == 'hard' and case['risk_tags'] and case['rationale']
        assert (root / case['policy_ref']).is_file()
        assert case['provenance'] == 'development_regression'
        for turn in case['turns']:
            assert turn['input'].strip()
            assert turn['expected'] or turn.get('nonempty') or turn.get('forbidden') or turn.get('contains')
    assert sum(len(c['turns']) >= 6 for c in cases if c['category'] == 'multiturn') >= 12
