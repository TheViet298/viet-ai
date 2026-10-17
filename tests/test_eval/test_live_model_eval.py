import pytest


def test_real_live_runner_assigns_model_and_phase_to_every_case():
    from types import SimpleNamespace
    from scripts.run_live_model_eval import expected_live_case, load_cases
    settings = SimpleNamespace(model_name='main', vision_model='vision', vision_provider='openai')
    cases = [expected_live_case(c, settings) for c in load_cases()]
    assert all(c['expected_model'] and c['expected_prompt'] for c in cases)
    assert {c['expected_prompt'] for c in cases} == {'general', 'vision.dashboard', 'vision.exterior'}


def test_live_suite_has_ten_real_model_cases_including_four_images():
    from scripts.run_live_model_eval import load_cases

    cases = load_cases()
    assert len(cases) == len({c['id'] for c in cases}) == 10
    assert sum(c['kind'] == 'chat' for c in cases) == 6
    assert sum(c['kind'] == 'upload' for c in cases) == 4
    assert not any(c.get('fault_injected') for c in cases)


def test_fallback_does_not_count_as_successful_model_call():
    from scripts.run_live_model_eval import evaluate_live

    result = {'http_status': 200, 'response': {'response': 'fallback'}}
    assert evaluate_live({'kind':'chat'}, result, [])['status'] == 'BLOCKED'


def test_attributed_live_case_accepts_provider_dated_snapshot():
    from scripts.run_live_model_eval import evaluate_live
    rows = [{'id': 'g', 'type': 'GENERATION', 'endTime': 'now', 'model': 'gpt-4o-mini-2024-07-18',
             'usageDetails': {'total': 3}, 'metadata': {'prompt_name': 'general'}},
            {'id': 'p', 'name': 'llm.outcome', 'metadata': {'outcome': 'parsed', 'prompt_name': 'general'}}]
    case = {'kind': 'chat', 'expected_model': 'gpt-4o-mini', 'expected_prompt': 'general'}
    assert evaluate_live(case, {'http_status': 200, 'response': {'reply': 'ok'}}, rows)['status'] == 'PASS'


def test_successful_generation_still_requires_application_parse():
    from scripts.run_live_model_eval import evaluate_live

    rows = [{'id':'g','type':'GENERATION','endTime':'now','usageDetails':{'input':2,'output':1,'total':3},'totalCost':0.001}]
    result = {'http_status':200,'response':{'response':'ok'}}
    assert evaluate_live({'kind':'chat'}, result, rows)['status'] == 'BLOCKED'
    rows += [{'id':'parse','name':'llm.outcome','metadata':{'outcome':'parsed'}}]
    assert evaluate_live({'kind':'chat'}, result, rows)['status'] == 'PASS'


def test_dashboard_checks_expected_symptom_not_only_http_200():
    from scripts.run_live_model_eval import evaluate_live

    rows = [{'id':'g','type':'GENERATION','endTime':'now','usageDetails':{'total':3},'totalCost':0.001}]
    result = {'http_status':200,'response':{'data':{'analysis_status':'ANALYZED','detected_signals':{'symptom_keys':['sensor_fault']}}}}
    assert evaluate_live({'kind':'upload','image_kind':'dashboard','expected_symptom':'low_pressure'},result,rows)['status']=='FAIL'
