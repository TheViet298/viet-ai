# StateGraph evaluation

Time: 2026-10-03T13:18:42.929139+00:00
Mode: configured LLM and local Chroma. Measured outputs; no substitute predictions. Missing samples report N/A.

| Metric | Result | MVP target | Status |
|---|---:|---:|---|
| critical_safety_recall | 1.0 | 1.0 | PASS |
| intent_accuracy | 0.7 | 0.85 | FAIL |
| routing_accuracy | 0.5667 | 0.8 | FAIL |
| top_k_grounded_citation_rate | 0.2 | 0.85 | FAIL |
| no_source_compliance | 1.0 | 0.8 | PASS |
| avg_latency_s | 11.228 | 2.5 | FAIL |
| staff_review_compliance | 0.7 | 0.85 | FAIL |

Sample counts: `{"critical": 1, "sourced": 10, "no_source": 5, "review": 30}`.
Citation grounding checks expected source and answer keywords; it is not a semantic truth proof.
Dataset labels may conflict with current mandatory HITL policy; inspect per-case results before changing rules.

## Live integration evidence

Verified `gemini-3.8-flash` connection and production structured triage on 2026-10-03. The provider rejected `gemini-2.5-flash` as unavailable to new users. The evaluation recorded six successfully parsed LLM events; other calls may use deterministic fallback. A subsequent provider recheck returned `GoogleRateLimitError`, confirming a quota/rate-limit constraint. This is a mixed online/fallback benchmark, not evidence of 45 successful Gemini responses. Secrets remain in ignored `.env`; external cloud tracing was disabled.
