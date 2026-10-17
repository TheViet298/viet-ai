import pytest


def proof(**changes):
    return {'phase': 'general', 'requested_model': 'gpt-4o-mini', 'actual_model': 'gpt-4o-mini-2024-07-18',
            'success': True, 'parsed': True, 'total_tokens': 20, **changes}


@pytest.mark.parametrize('changes', [{'actual_model': 'wrong-model'}, {'phase': 'normalization'},
    {'success': False}, {'parsed': False}, {'total_tokens': None}, {'total_tokens': 0}, {'actual_model': None}])
def test_evidence_rejects_wrong_model_phase_fallback_and_missing_usage(changes):
    from eval.model_evidence import verify_calls
    assert verify_calls([proof(**changes)], [{'phase': 'general', 'model': 'gpt-4o-mini'}])


def test_snapshot_response_is_valid_but_arbitrary_prefix_is_not():
    from eval.model_evidence import verify_calls
    required = [{'phase': 'general', 'model': 'gpt-4o-mini'}]
    assert not verify_calls([proof()], required)
    assert verify_calls([proof(actual_model='gpt-4o-mini-wrong')], required)


def test_forbidden_calls_and_two_phase_requirements_are_enforced():
    from eval.model_evidence import verify_calls
    assert verify_calls([proof()], [], forbid_calls=True)
    assert verify_calls([proof()], [{'phase': 'general', 'model': 'gpt-4o-mini'},
                                   {'phase': 'normalization', 'model': 'gemini-2.5-flash-lite'}])


@pytest.mark.asyncio
async def test_recorder_uses_provider_response_not_declared_model():
    from types import SimpleNamespace

    from eval.model_evidence import RecordedModel
    rows = []

    class Fake:
        async def ainvoke(self, *args, **kwargs):
            return {'raw': SimpleNamespace(response_metadata={'model_name': 'actual-other-model'},
                usage_metadata={'input_tokens': 4, 'output_tokens': 2, 'total_tokens': 6}), 'parsed': object()}

    result = await RecordedModel(Fake(), 'requested-model', rows).ainvoke([])
    assert result['parsed'] is not None
    assert rows[0]['actual_model'] == 'actual-other-model' and rows[0]['total_tokens'] == 6
