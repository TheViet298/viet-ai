import pytest


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


def test_src009_catalog_urls_verified_and_retrievable():
    from src.services.rag_service import RAGService, source_registry, valid_citation

    registry = source_registry()
    src009 = registry.get("SRC-009", {})
    approved_urls = src009.get("approved_urls", {})
    assert len(approved_urls) >= 15
    assert "https://vinfastauto.com/vn_vi/dat-coc-xe-vf9" in approved_urls
    assert "https://vinfastauto.com/vn_vi/dat-coc-xe-dien-vf3" in approved_urls
    assert "https://shop.vinfastauto.com/vn_vi/nerio-green.html" in approved_urls

    citation = {
        "source_id": "SRC-009",
        "url": "https://vinfastauto.com/vn_vi/dat-coc-xe-vf9",
        "status_code": 200,
        "verified_at": approved_urls["https://vinfastauto.com/vn_vi/dat-coc-xe-vf9"],
        "applicable_models": ["VF 9"],
        "distance": 0.25,
        "relevant_snippet": "Thông số chi tiết VinFast VF 9 - Phiên bản VF 9 Eco: Quãng đường 626km/lần sạc",
    }
    assert citation['verified_at'] == '2026-10-16'  # Product price section re-reviewed.
    assert valid_citation(citation, "VF 9")
    assert not valid_citation({**citation, 'verified_at': '2026-09-30'}, 'VF 9')

    rag = RAGService()
    raw = {
        "documents": [["Thông số chi tiết VinFast VF 9 - Phiên bản VF 9 Eco:\n- Quãng đường di chuyển (WLTP): 626km/lần sạc"]],
        "metadatas": [[{
            "source_id": "SRC-009",
            "url": "https://vinfastauto.com/vn_vi/dat-coc-xe-vf9",
            "applicable_models": "VF 9",
        }]],
        "distances": [[0.19]],
        "ids": [["SRC-009-0002"]],
    }
    filtered = rag.filter_results(raw, query="VF 9 Eco quãng đường di chuyển", vehicle_model="VF 9")
    assert filtered["status"] == "SUCCESS"
    assert len(filtered["citations"]) == 1
    assert filtered["citations"][0]["url"] == "https://vinfastauto.com/vn_vi/dat-coc-xe-vf9"


@pytest.mark.asyncio
async def test_rolling_cost_url_verified_and_answers_include_calculator_link():
    import pytest
    from src.services.rag_service import source_registry
    from src.services.knowledge_questions import sales_parts, answer_sales_question

    registry = source_registry()
    src009 = registry.get("SRC-009", {})
    approved_urls = src009.get("approved_urls", {})
    rolling_url = "https://shop.vinfastauto.com/vn_vi/chi-phi-lan-banh"
    assert rolling_url in approved_urls

    parts = sales_parts("Tôi muốn tư vấn các mẫu xe điện VinFast và giá lăn bánh", None)
    labels = [p[0] for p in parts]
    assert "Thông tin dòng xe" in labels
    assert "Giá lăn bánh" in labels

    res = await answer_sales_question("Cho tôi hỏi giá lăn bánh xe điện VinFast", None, "test-rolling")
    assert rolling_url in res["reply"]


