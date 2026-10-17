from src.services.request_diagnostics import final_response_diagnostics


def test_snapshot_success_keeps_discarded_stage_error_separate():
    result = final_response_diagnostics(answer_path='snapshot', successful=True,
                                        stages=[{'prompt': 'rag_qa', 'outcome': 'timeout'}])
    assert result['final_outcome'] == 'success'
    assert result['answer_path'] == 'snapshot'
    assert result['stage_outcomes'][0]['outcome'] == 'timeout'
