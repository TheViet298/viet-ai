def test_capture_keeps_table_headers_and_rows():
    from scripts.refresh_agent_sources import extract_blocks

    html = '<main><h1>Chính sách</h1><h2>Thời hạn bảo hành Ô tô</h2><table><tr><th>Dòng xe</th><th>Thời hạn</th></tr><tr><td>VF5</td><td>7 năm hoặc 160.000 km</td></tr></table></main>'
    blocks = extract_blocks(html)
    assert any('Dòng xe | Thời hạn' in b and 'VF5 | 7 năm hoặc 160.000 km' in b for b in blocks)


def test_catalog_alias_must_be_verified(monkeypatch):
    from src.services import rag_service as module

    url = 'https://vinfastauto.com/vn_vi/dat-coc-xe-dien-vf6'
    registry = {'SRC-009': {'url': 'https://vinfastauto.com/vn_vi/', 'verified_at': '2026-09-30', 'approved_urls': {url: '2026-10-03'}}}
    monkeypatch.setattr(module, 'source_registry', lambda: registry)
    citation = {'source_id': 'SRC-009', 'url': url, 'status_code': 200, 'verified_at': '2026-10-03', 'applicable_models': ['VF6'], 'distance': 0.2, 'relevant_snippet': 'VF6 Eco 485 km NEDC'}
    assert module.valid_citation(citation, 'VF6')
    citation['verified_at'] = '2026-09-30'
    assert not module.valid_citation(citation, 'VF6')
