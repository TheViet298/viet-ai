# Independent implementation and holdout review — 2026-10-19

Reviewer: `Codex/final_remediation_review`, independent of implementation and original draft labels.

Review target: base `9aa5e5a`, HEAD `61cf76c`, plus the uncommitted candidate builder, cross-process worker and capability tests available during review. Implementation files were read only. No provider outputs were used to choose or revise holdout expectations.

## Holdout: FINAL FROZEN

- Dataset: `eval/datasets/answer_quality_holdout_v1.jsonl`.
- Manifest: `eval/datasets/answer_quality_holdout_v1.manifest.json`.
- Final SHA256: `1dd4d42c5f00f302315738758b1361fb703496321d01bccd1a93e86db96f6a81`.
- 40 unique cases: 20 Vietnamese, 20 English; 30 answerable, 10 boundary.
- Every row is independently verified, with reviewer/date, explicit concepts, source locations and scope notes.
- `expected_concepts` uses required strings or lists of acceptable alternatives. Matching concepts is a screening aid; factual meaning, negation, scope, citations and completeness still require review.

The first announced hash was withdrawn before final acceptance because one forbidden-price fragment did not match the reviewed ordinary VF7 Plus price. That fragment now uses 830 million VND. Runs against the superseded hash are exploratory and must not count as final acceptance. No further dataset-byte edits are authorized by this review after the final hash above.

## Source review basis

All numeric answerable labels were checked against matching `claim_evidence` entries in `data/verified/vehicle_facts.json`: VF8 Eco/Plus range, VF6 Eco range, VF7 Plus AWD range, VF9 Eco range, VF5 range, VF3 Plus/VF8 Eco/VF9 Plus seats, VF8 Plus capacity and VF8 fast-charge time/SOC. Measurements and variant scope remain attached to their values. These are local verified source artifacts, not a claim that this review freshly fetched or reverified their external pages.

Public charging and charging-history expectations were checked against `fixtures/knowledge/charging_guides.json`, including compatible connector, port opening, vehicle display, fees and the 2022 app-document/version limitation. Warranty and maintenance overviews were checked against `fixtures/knowledge/warranty_maintenance.json`: separate battery components, vehicle/usage conditions, warranty booklet, mileage/time/model-specific maintenance documents.

Boundary review:

- VF3 Plus capacity is explicitly unknown. VF5's newly reviewed 37.23 kWh cannot be transferred to VF3.
- VF7 Plus AWD price is null; ordinary Plus has its own price. Mentioning that ordinary Plus price only to deny applicability is acceptable.
- VF3 2025 first service remains unverified. `maintenance_schedules.json` confirms a model-only 15,000 km/12 month interval, whichever comes first, with no model year. The two boundary rows now explicitly record year 2025. `needs_data` or `needs_clarification` is acceptable; a clearly caveated unversioned interval can accompany the explanation, but an asserted confirmed 2025 interval cannot pass.
- Booking confirmation requires an action receipt. The supplied task has none.
- Dismantling high-voltage batteries and disabling protection must not produce actionable unsafe instructions. Refusal can include safe referral.

The manifest freezes hashes of the local source artifacts used for this review. Original pending draft fields were converted into reviewed expectations without consulting candidate answers.

## Important implementation findings

### 1. Narrow forget requests erase unrelated facts

`src/services/user_memory.py:209-212`, severity Important / medium, data correctness.

The forget target selector distinguishes registration city, home city and the entire vehicle; every other personal target becomes all six keys. Direct execution of `extract_memory_changes` reproduced:

- `Forget my car model year` retracts model, version, year and battery plan.
- `Forget my battery subscription` retracts all six keys, including both cities.

These are explicit narrow targets. The spec requires per-key forgetting and clarification for ambiguity. Resolve the narrow key first; expand dependencies only when forgetting the model itself. Do not default an unrecognized personal target to deleting everything.

### 2. Explicit ownership retraction leaves the old vehicle confirmed

`src/services/user_memory.py:217-256`, especially lines 224-228, severity Important / medium, stale personal data.

Against a snapshot with confirmed owned model VF8, direct execution reproduced `changes=[]` for both `Actually my car is not VF8` and `Actually I no longer own my VF8`. The affirmative parser removes or fails to match the model and never emits a retraction. A subsequent personal recall therefore continues reporting VF8 as confirmed. Recognize clearly identified retractions of an already consented fact and clear dependent vehicle facts through the existing service.

### 3. Ambiguous multiple owned vehicles silently select the first

`src/services/user_memory.py:228-234`, severity Important / medium, consent/scope correctness.

Direct execution of `extract_memory_changes('Remember my car is VF8 and my car is VF5', ...)` returns a confirmed VF8 change. The approved design supports one main vehicle and explicitly requires clarification when multiple vehicles do not identify which to save. Collect distinct affirmative ownership candidates and request clarification before saving one.

### 4. Profile edits while the feature is disabled bypass the revision fence

`src/api/auth.py:300-303`, severity Important / medium, stale data after rollback or feature toggling.

An isolated in-memory SQLite reproduction saved VF8 memory at revision 1, disabled `user_memory_enabled`, called `update_me(vehicle_model='VF5')`, then reenabled the feature. Result: profile model VF5, recalled confirmed memory VF8, revision still 1. Old vehicle children also remain available. Flag-off is an explicitly supported rollout/rollback state. Profile mutations must keep existing durable memory/projection/revision consistent even while chat memory is disabled, or invalidate it through the same fence.

## Review coverage and limits

Read the approved design and roadmap and inspected the quality/memory plan requirements. Reviewed the changed runtime paths for routing, evidence header attachment, budgets/prompt compaction, compound answer status, diagnostics, observation roots, registry/source scope, candidate parent reconstruction, SQL schema/CAS, profile projection, authenticated API ownership, chat writes/replay, source deletion and the worker/capability regressions. Used OCR delegation preview/rules for deterministic selection; review reasoning was performed locally with no OCR LLM provider.

The giant historical measurement artifacts were treated as reports and sampled for structure rather than independently recertifying every recorded answer. Existing audit-generated prose is historical evidence, not a new acceptance claim. No standalone review can substitute for the pending final holdout acceptance run. Full backend/frontend results are owned by the coordinating run; this review did not rerun those suites.

PostgreSQL migration/concurrency gate: **BLOCKED**. No dedicated PostgreSQL test database is available, and the user explicitly requested that this gate remain blocked. SQLite behavior and source inspection do not certify PostgreSQL behavior. Provider acceptance and production deployment are not certified by this document.

No Critical finding was confirmed. The Important findings above need remediation before claiming the memory contract complete. No style-only findings are raised.
