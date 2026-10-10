import pytest

from scripts.audit_natural_conversations import ROOT, load_cases, validate_output_directory


def test_runner_rejects_shared_or_existing_directory(tmp_path):
    with pytest.raises(ValueError):
        validate_output_directory(str(tmp_path))
    with pytest.raises(ValueError):
        validate_output_directory(str(ROOT / '.test-runs'))
    with pytest.raises(ValueError):
        validate_output_directory(str(ROOT / 'src'))


def test_runner_loads_turns_and_rejects_invalid_schema(tmp_path):
    dataset = tmp_path / 'cases.json'
    dataset.write_text('[{"id":"one","first":"A","followup":"B"}]', encoding='utf-8')
    assert load_cases(dataset)[0]['turns'] == ['A', 'B']
    dataset.write_text('[{"id":"invalid","turns":[null]}]', encoding='utf-8')
    with pytest.raises(ValueError):
        load_cases(dataset)
