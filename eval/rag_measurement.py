"""Evidence metrics and fail-closed acceptance validation, without an LLM judge."""
from __future__ import annotations

import math
import re


def measure_evidence(expected_ids: list[str] | None, retrieved_ids: list[str], k: int) -> dict:
    if k < 1:
        raise ValueError('k must be positive')
    retrieved = list(dict.fromkeys(retrieved_ids))[:k]
    expected = set(expected_ids or [])
    hits = len(expected & set(retrieved))
    return {'status': 'measured' if expected else 'unavailable', 'recall': hits / len(expected) if expected else None,
            'precision': hits / len(retrieved) if expected and retrieved else 0. if expected else None,
            'expected_count': len(expected), 'retrieved_count': len(retrieved), 'hits': hits, 'k': k,
            'retrieved_ids': retrieved}


def check_acceptance(report: dict, gate_config: dict) -> list[str]:
    required_metrics = {'evidence_recall_at_3', 'evidence_precision_at_3', 'grounded_answer_rate', 'no_source_compliance', 'critical_safety_recall'}
    required_coverage = {'critical', 'sourced', 'no_source', 'evidence_labeled'}
    thresholds, coverage = gate_config.get('thresholds'), gate_config.get('minimum_coverage')
    if (gate_config.get('report_version') != 1 or not isinstance(thresholds, dict) or not isinstance(coverage, dict)
        or not required_metrics <= thresholds.keys() or not required_coverage <= coverage.keys()
        or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in thresholds.values())
        or any(type(v) is not int or v < 1 for v in coverage.values())):
        return ['invalid_gate_configuration']
    failures = []
    if report.get('gate_kind') != 'acceptance':
        failures.append('not_acceptance_report')
    if report.get('report_version') != gate_config.get('report_version'):
        failures.append('report_version')
    metadata = report.get('metadata', {})
    if metadata.get('label_status') != 'approved':
        failures.append('labels_not_approved')
    provenance = metadata.get('provenance', {})
    for name in ('kb', 'model', 'prompt', 'dataset', 'mapping', 'config'):
        if not isinstance(provenance.get(name), str) or not re.fullmatch('[0-9a-f]{64}', provenance[name]):
            failures.append('missing_provenance:' + name)
    for name, minimum in gate_config['minimum_coverage'].items():
        count = report.get('coverage', {}).get(name)
        if type(count) is not int or count < minimum:
            failures.append('coverage:' + name)
    for name, threshold in gate_config['thresholds'].items():
        value = report.get('metrics', {}).get(name)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1 or value < threshold:
            failures.append('metric:' + name)
    return failures
