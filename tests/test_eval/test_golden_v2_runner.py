from types import SimpleNamespace

import pytest

from scripts.run_golden_v2_eval import coverage, execute_case, judge, load_cases, probes


def test_all_production_model_phases_have_live_probes():
    assert {c['phase'] for c in probes()} == {'normalization', 'conversation_turn', 'triage',
        'general', 'rag_qa', 'memory', 'customer_translation'}
    assert {c['operation'] for c in load_cases() if c['kind'] == 'vision'} == {'route', 'dashboard', 'exterior'}


def test_default_live_selection_includes_long_hard_conversations():
    from scripts.run_golden_v2_eval import live_cases
    chosen = live_cases(load_cases())[:40]
    assert len(chosen) == 40
    assert sum(c['kind'] == 'probe' for c in chosen) == 7
    assert sum(c['kind'] == 'vision' for c in chosen) == 16
    assert sum(c['category'] == 'multiturn' for c in chosen) >= 4


@pytest.mark.asyncio
async def test_failed_first_contract_does_not_hide_late_emergency(monkeypatch):
    from src.agents import chatbot_agent
    seen = []

    async def chat(message, **kwargs):
        seen.append((message, kwargs['session_id']))
        return {'priority': 'LOW' if len(seen) == 1 else 'CRITICAL'}

    monkeypatch.setattr(chatbot_agent, 'process_chat_message', chat)
    case = {'kind': 'chat', 'retrieval': {'status': 'NO_SOURCE'}, 'turns': [
        {'input': 'Xe không nhận sạc', 'expected': {'priority': 'HIGH'}},
        {'input': 'Bây giờ xe đang cháy', 'expected': {'priority': 'CRITICAL'}}]}
    output = await execute_case(case, 'late-emergency')
    result = judge(case, output, [], live=False, settings=SimpleNamespace())
    assert len(seen) == 2 and {s[1] for s in seen} == {'late-emergency'}
    assert result['status'] == 'FAIL' and len(result['failed_checks']) == 1
    assert result['failed_checks'][0]['turn'] == 1


def test_coverage_requires_correct_case_as_well_as_real_model_call():
    settings = SimpleNamespace(model_name='main', normalization_model='norm', vision_model='vision',
                               vision_provider='openai', dashboard_vision_model='alternative')
    row = {'phase': 'general', 'requested_model': 'main', 'actual_model': 'main',
           'success': True, 'parsed': True, 'total_tokens': 20}
    cases = [{'id': 'case', 'status': 'FAIL', 'model_calls': [row]}]
    general = next(r for r in coverage(cases, settings) if r['phase'] == 'general')
    assert general['provider_confirmed_cases'] == ['case'] and general['correct_cases'] == []
    assert general['status'] == 'FAIL'


def test_long_live_conversation_requires_actual_memory_generation():
    settings = SimpleNamespace(model_name='main')
    case = {'kind': 'chat', 'turns': [{'input': 'update', 'expected': {'priority': 'MEDIUM'}}] * 7}
    result = judge(case, {'turns': [{'priority': 'MEDIUM'}] * 7}, [], live=True, settings=settings)
    assert result['status'] == 'BLOCKED'


def test_offline_critical_rejects_any_model_call():
    case = {'kind': 'chat', 'forbid_model_calls': True, 'turns': [
        {'input': 'Xe cháy', 'expected': {'priority': 'CRITICAL'}}]}
    result = judge(case, {'turns': [{'priority': 'CRITICAL'}]}, [{'phase': 'general'}],
                   live=False, settings=SimpleNamespace())
    assert result['status'] == 'FAIL' and 'forbidden_model_call' in result['evidence_errors']
