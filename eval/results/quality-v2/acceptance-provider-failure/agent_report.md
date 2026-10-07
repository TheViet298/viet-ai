# StateGraph evaluation

Time: 2026-10-03T16:17:03.605573+00:00
Mode: provider_failure; real local Chroma. Measured outputs; no substitute predictions. Missing samples report N/A.

| Metric | Result | MVP target | Status |
|---|---:|---:|---|
| critical_safety_recall | 1.0 | 1.0 | PASS |
| intent_accuracy | 1.0 | 0.85 | PASS |
| routing_accuracy | 1.0 | 0.8 | PASS |
| top_k_grounded_citation_rate | 0.35 | 0.85 | FAIL |
| no_source_compliance | 0.8 | 0.8 | PASS |
| avg_latency_s | 0.496 | 2.5 | PASS |
| staff_review_compliance | 0.9 | 0.85 | PASS |

Sample counts: `{"critical": 10, "sourced": 20, "no_source": 10, "review": 60}`.
Citation grounding checks expected source and answer keywords; it is not a semantic truth proof.
Dataset labels may conflict with current mandatory HITL policy; inspect per-case results before changing rules.
