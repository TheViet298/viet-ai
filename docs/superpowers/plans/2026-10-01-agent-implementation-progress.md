# Implementation ledger — plan: docs/superpowers/plans/2026-10-01-complete-agent-system.md

Execution resumed in existing `feature/agent-long` checkout. Existing staged documentation and src/config.py changes belong to the user; preserve them. No automatic commits/pushes.

Ruling: execute coupled graph/backend work inline and obtain independent final review — state, storage, nodes and API share contracts; retain already implemented files from before Superpowers became available — risk: author bias addressed by tests and final review.
Ruling: SQLite standard library instead of SQLAlchemy — existing app has no DB layer; sqlite supports transactions and the required local persistence — risk: later ORM migration.
Ruling: preserve emergency output while generating a brief; only authenticated customers persist cases — ADR-005 is authoritative over contradictory sample code.
Ruling: use check_missing_fields and named HITL arguments — actual guardrails contract is authoritative.
Ruling: distance <= 0.70 plus verified source registry, not fabricated status/dates — Chroma collection uses distances, not similarity.
Ruling: no fabricated performance baselines, no fake citations or service points — measured results and configured seed data only.
Ruling: use bundled Python 3.12 with existing .venv/Lib/site-packages — .venv executable points to missing Python; no reinstall needed.

| Task | Shared contract / finding | Status |
|---|---|---|
| 0 | Prompt artifacts consumed by 2 and all online nodes | Implemented; metadata/contract tests pass |
| 1 | Role/quota fields absent in existing state; extend schema | Implemented; masking, ownership/quota and emergency override tests pass |
| 2 | Context builder previously hardcodes prompts; external artifacts now used | Implemented; pinned budget, recency and memory compression tests pass |
| 3,7,8 | Brief overwrote emergency reply; must preserve safety output | Implemented; smoke/brake/turtle, minimum brief and trace/storage failure tests pass |
| 4,6,8 | Wrong missing-fields helper; intent continuation and required slots | Implemented; mixed incident/FAQ, component FAQ and sentiment routing tests pass |
| 5,7,8 | Missing RAG service; NO_SOURCE needs real handoff | Implemented; source/model/distance/injection checks and real-Chroma evaluation run |
| 6,7 | After two clarification turns generate Needs Information brief | Implemented; multi-turn persisted facts and brief tests pass |
| 9 | Existing API is routes.py; no customer.py/auth/session store exists | Implemented; trusted demo auth, cases, ownership, location and confirmation tests pass |
| 10 | Duplicate tasks consolidated; local recorder must be wired into graph | Implemented; node replay, provider usage, cloud fallback and PII tests pass |
| 11 | Dataset uses input/expected_staff_review; predictions must come from graph | Implemented; metric denominator tests and 45-case benchmark report |

Auth scope: add trusted bearer demo-token adapter for backend bridge; production OTP/user registration stays with backend owner. Vision/OCR remain out of scope.

Independent review found and fixed: mixed incident/FAQ bypass; staff status regression; explicit case selection ignored; generated FAQ PII persisted. Scoped re-review caught missing charging-failure phrases and bare component names incorrectly blocking FAQ; both reproduced RED and corrected GREEN. Staff lifecycle now stays authoritative, and backend case history records automated transitions.

Task 0–11: implementation verified by the consolidated 82-test suite. Production examples in the source plan were synchronized; duplicate Task 10 removed. Original step/commit checkboxes are retained as historical plan steps, not completion claims.

Final verification: `python -m pytest tests/ -q -p no:cacheprovider --basetemp=.test-runs/final-suite` → 82 passed. Targeted Ruff check → all checks passed.

Local `.venv/pyvenv.cfg` repointed to available bundled Python 3.12.14; original saved in ignored `.test-runs/pyvenv.cfg.original`. Existing packages imported successfully. No dependency installation. A subsequent user-authorized Gemini credential was saved only in ignored `.env`.

Benchmark: 30 triage + 15 RAG cases, offline Gemini / real Chroma. Safety recall 100% (one critical holdout); NO_SOURCE compliance 100% (five refusal cases); intent 76.67%, routing 60%, grounded citations 20%, staff-review agreement 70%, mean latency 0.201s. These are measured baseline results; four quality KPIs remain below target. Live Gemini connection and production structured triage were verified on 2026-10-03 with `gemini-3.8-flash`; the provider rejected the previously configured `gemini-2.5-flash`. Cloud tracing remains untested and is disabled locally during verification.

Delivery: changes remain in `feature/agent-long`, uncommitted. Existing staged user work remains intact. No merge, push, API deployment or publication was performed.

User-authorized live Gemini verification (2026-10-03): saved credential only in ignored `.env`; connection and production structured triage passed with `gemini-3.8-flash`. Added verified model to `.env.example`. Online/fallback evaluation completed 45 cases: intent 70%, routing 56.67%, grounded citations 20%, safety recall 100% (one critical), NO_SOURCE compliance 100% (five), review agreement 70%, mean latency 11.228s. Six parsed LLM events were recorded. Provider recheck confirmed `GoogleRateLimitError`; no claim of full online coverage or benchmark readiness. Results: `eval/results/agent-online/`. Regression verification after local configuration: 82 passed.
