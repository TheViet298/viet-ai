from src.services.rag_service import RAGService, source_registry


def test_diagnostics_explain_wrong_model_and_registry():
    service = RAGService()
    result = {
        "documents": [["Bảo hành VF5", "Nội dung không xác minh"]],
        "metadatas": [[{**source_registry()["SRC-002"], "source_id": "SRC-002", "applicable_models": "VF5"}, {"source_id": "UNKNOWN"}]],
        "distances": [[0.2, 0.3]], "ids": [["wrong-model", "bad-registry"]],
    }
    out = service.filter_results(result, "VF8")
    assert out["status"] == "NO_SOURCE"
    assert {c["reason"] for c in out["diagnostics"]["candidates"]} == {"model_mismatch", "registry_mismatch"}


def test_sentence_selection_preserves_number_and_condition():
    from src.services.rag_service import select_supported_evidence

    citation = {"relevant_snippet": "Thông tin khác.\nVF 8: bảo hành 10 năm hoặc 200.000 km tùy điều kiện nào đến trước.\nNội dung khác."}
    chosen = select_supported_evidence("Bảo hành VF8 bao lâu?", [citation])
    assert "10 năm hoặc 200.000 km tùy điều kiện nào đến trước" in chosen[0]["relevant_snippet"]


def test_variant_mismatch_does_not_supply_specification():
    meta = {**source_registry()["SRC-009"], "source_id": "SRC-009", "applicable_models": "VF7"}
    result = {"documents": [["VF7 Eco pin 59 kWh"]], "metadatas": [[meta]], "distances": [[0.2]], "ids": [["eco"]]}
    out = RAGService().filter_results(result, "VF7", query="Dung lượng pin VF7 Plus bao nhiêu kWh?")
    assert out["status"] == "NO_SOURCE"
