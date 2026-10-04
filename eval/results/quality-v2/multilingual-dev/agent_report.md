# StateGraph evaluation

Time: 2026-10-03T16:31:41.686960+00:00
Mode: offline; real local Chroma. Measured outputs; no substitute predictions. Missing samples report N/A.

| Metric | Result | MVP target | Status |
|---|---:|---:|---|
| critical_safety_recall | 1.0 | 1.0 | PASS |
| intent_accuracy | 0.7333 | 0.85 | FAIL |
| routing_accuracy | 0.5333 | 0.8 | FAIL |
| top_k_grounded_citation_rate | 0.0 | 0.85 | FAIL |
| no_source_compliance | 1.0 | 0.8 | PASS |
| avg_latency_s | 0.245 | 2.5 | PASS |
| staff_review_compliance | 0.7333 | 0.85 | FAIL |

Sample counts: `{"critical": 1, "sourced": 10, "no_source": 5, "review": 15}`.
Citation grounding checks expected source and answer keywords; it is not a semantic truth proof.
Dataset labels may conflict with current mandatory HITL policy; inspect per-case results before changing rules.
