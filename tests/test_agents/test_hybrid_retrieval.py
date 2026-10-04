def test_lexical_candidate_is_not_lost_behind_vector_top_k():
    from src.services.rag_service import rank_candidates

    rows = [
        ("Nội dung điều hòa trong xe", {}, 0.1, "vector-first"),
        ("Ứng dụng VinFast: Bấm chọn Điều hòa ở trang chủ để điều khiển từ xa", {}, 0.6, "supported"),
    ]
    ranked = rank_candidates("Bật điều hòa từ xa qua ứng dụng VinFast", rows)
    assert ranked[0][3] == "supported"


def test_evidence_excerpt_does_not_cut_off_last_condition():
    from src.services.rag_service import select_supported_evidence

    doc = "Nội dung khác.\nVF8 bảo hành 10 năm hoặc 200.000 km.\nTùy điều kiện nào đến trước.\nKhông áp dụng cho xe dịch vụ."
    result = select_supported_evidence("Bảo hành VF8 bao lâu?", [{"relevant_snippet": doc}])
    assert "Không áp dụng cho xe dịch vụ" in result[0]["relevant_snippet"]
