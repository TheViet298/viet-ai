# Knowledge coverage inventory and data acceptance

## Remediation inventory — 2026-10-19

Fresh inventory on the 2,196-chunk replica is saved in `eval/results/knowledge-remediation/coverage-before-2026-10-19.json`. It is not the historical 85/162 count or a factual answer score. The 20 scoped acquisition gaps are in `data/verified/knowledge_gap_register.json`.

Acquired candidates include the current VN VF5 product page (usable capacity and model-level colors), the app guide page and a web extraction of the maintenance page's VF3 table. Direct requests for schedule images and some pages returned HTTP403. Record this as an access/review blocker; do not label those images content-free. Review model/year/header/footnotes before normalizing any intervals. The PHP/Philippines VF3 launch specification cannot resolve VN Eco/Plus capacity. Exact service prices and availability still need an authoritative integration/source. Candidate acquisition does not change the active index.

`python scripts/audit_knowledge_coverage.py --index data/chroma-catalog-colors-v1 --output <report.json>` is read-only. The active index remains unchanged. Inventory availability does not certify retrieval or answer correctness.

The previous 189-cell/111-missing matrix is withdrawn: it assumed Eco/Plus for every model and excluded official_service maintenance/charging sources. The matrix now uses reviewed product applicability: VF3 Eco/Plus; VF5 unspecified (no named trim verified); VF6 Eco/Plus; VF7 Eco/Plus/Plus AWD; VF8 Eco/Plus; VF9 Eco/Plus; e34 unspecified. Unspecified cells remain useful for general services. A named trim in a chunk is still required for a trim-specific cell; general service coverage does not establish trim-specific technical facts.

`data/verified/vehicle_facts.json` is the canonical card, comparison, ranking and public price authority. Product pages' **Giá niêm yết** sections were reviewed on 2026-10-16, separately from retained technical-spec review dates. Prices have list/promotion distinction, source section, market, trim, drivetrain, conditions and explicit unknown model year/battery package/effective dates. VF7 Plus AWD has no independently verified price. Card prices and quote evidence share a seven-day review window. The two public-price JSON files are compatibility exports only; runtime uses the canonical helper. Never renew review dates from a successful HTTP status alone.

Legacy all-model ranking claims and generic fake manual snippets were removed. Ranking lists only scoped registry values and makes no cross-standard winner claim. Knowledge Hub articles link to the correct service/manual/policy pages; unsupported universal warranty, maintenance, CC01/BMS, timer-reset and electrical-installation recipes were removed. Synthetic support-insight publication is withheld until claim-level evidence review.

## Acquisition and release gates

- Manuals: the official portal [om.vinfastauto.com](https://om.vinfastauto.com/) is available but returns a JavaScript shell to the text reader. VF3/VF6/VF7/VF9/e34 model/year manuals remain unacquired and unregistered. Do not turn VF8 text or brochures into substitute manuals. The official [VF3 emergency responder guide](https://static-cms-prod.vinfastauto.com/VF3-ERG_VN_V4.pdf) is a concrete acquisition candidate, restricted to trained responders; it is not an owner repair guide.
- Prices: 95%-of-list VF8 values in the old index remain quarantined from numeric purchase answers pending promotion conditions/effective-date review. Do not infer a discount's eligibility from the arithmetic. An unverified AWD price remains null.
- Corpus: 26 normalized duplicate groups and 13 boilerplate candidates are review queues. Shared safety text across manuals must retain model/provenance unions; app login instructions can be useful. Build a side-by-side index only after reviewed decisions and rollback checks; do not edit the active collection.
- Images: 542 near-similar pairs are review candidates, not deletion approval. Preserve product assets. Require rights/provenance, vehicle/session grouping before split, model/year/view labels, unknown/non-VinFast examples and independent test images. Current vehicle and damage baselines have no test split; local asset additions do not train the runtime provider.
- Evaluation: draft acceptance/golden/pending labels cannot certify release. Independent reviewers must supply evidence spans/sections, subject/conditions, allowed abstention and executed handoff outcomes. Existing remediation regressions are development evidence, never independent holdout. No fabricated manual, image-rights label or independent approval is accepted.

These are external acquisition/review gates, not claims that the missing data is unavailable anywhere.

Read-only recheck on 16 October: 2,196 active chunks, 162 applicable cells, 85 available and 77 missing. This replaces the withdrawn matrix and does not measure correctness. `data/verified/index_cleanup_review.json` records 24 confirmed separator-only chunks proposed for exclusion from a future index; all other duplicate groups and 13 boilerplate candidates remain pending review. The current index was not rebuilt or edited.
