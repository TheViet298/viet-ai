import pytest


def test_acceptance_requires_critical_and_no_source_coverage():
    from scripts.run_agent_eval import validate_acceptance_dataset

    with pytest.raises(ValueError, match="coverage"):
        validate_acceptance_dataset([{"id": "one", "kind": "triage", "expected_priority": "medium"}])


def test_duplicate_cases_cannot_inflate_denominators():
    from scripts.run_agent_eval import validate_acceptance_dataset

    with pytest.raises(ValueError, match="Duplicate"):
        validate_acceptance_dataset([{"id": "one"}, {"id": "one"}])
