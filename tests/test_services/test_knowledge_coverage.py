from scripts.audit_knowledge_coverage import coverage_rows


def test_coverage_resolves_registry_before_declaring_missing_type():
    registry = {'s': {'source_type': 'official_catalog', 'verified_at': '2026-10-15',
                      'url': 'https://vinfastauto.com/catalog', 'applicable_models': ['VF8']}}
    rows = coverage_rows([{'source_id': 's', 'applicable_models': 'VF8'}], ['VF8 Plus quãng đường 475 km'], registry)
    row = next(r for r in rows if r['model'] == 'VF8' and r['trim'] == 'Plus' and r['domain'] == 'range')
    assert row['status'] == 'available'
    assert row['source_ids'] == ['s']
    assert any(r['model'] == 'VF7' and r['status'] == 'missing' for r in rows)


def test_unknown_source_applicability_is_not_available():
    rows = coverage_rows([{'source_id': 'unregistered'}], ['VF8 Plus quãng đường 475 km'], {})
    row = next(r for r in rows if r['model'] == 'VF8' and r['trim'] == 'Plus' and r['domain'] == 'range')
    assert row['status'] == 'unknown-applicability'
