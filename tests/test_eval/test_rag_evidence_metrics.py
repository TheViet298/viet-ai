def test_recall_before_and_after_budget():
    from eval.rag_measurement import measure_evidence
    assert measure_evidence(['A', 'B'], ['A', 'B', 'C'], 20)['recall'] == 1
    assert measure_evidence(['A', 'B'], ['A'], 3)['recall'] == .5


def test_missing_labels_are_unavailable():
    from eval.rag_measurement import measure_evidence
    assert measure_evidence(None, ['A'], 3)['recall'] is None
    assert measure_evidence([], ['A'], 3)['status'] == 'unavailable'


def test_duplicate_ids_do_not_inflate():
    from eval.rag_measurement import measure_evidence
    out = measure_evidence(['A', 'B'], ['A', 'A', 'C'], 3)
    assert out['recall'] == .5
    assert out['precision'] == .5
    assert out['retrieved_count'] == 2


def test_wrong_number_fails_required_facts():
    from scripts.run_agent_eval import grounded_answer
    assert not grounded_answer({'expected_source_id': 'SRC-002', 'required_answer_facts': ['12 ngày']},
                               {'response_type': 'FAQ_ANSWER', 'response': '20 ngày', 'rag_citations': [{'source_id': 'SRC-002'}]})


def test_partition_selection_keeps_holdout_out_of_development():
    from scripts.run_agent_eval import partition_cases
    cases = [{'id': str(i)} for i in range(30)]
    development = partition_cases(cases, 'development')
    holdout = partition_cases(cases, 'holdout')
    assert development and holdout
    assert not {c['id'] for c in development} & {c['id'] for c in holdout}
    assert len(development) + len(holdout) == 30
    assert partition_cases(cases, 'development') == development
