# Agent system

The six-node StateGraph replaces the boilerplate: intake → safety → triage → clarification / verified RAG / case brief. Clarification stops after two turns; NO_SOURCE and incomplete incidents generate a human-review brief. Emergency replies survive brief generation and bypass location, Gemini and quota limits.

## Run

Use Python 3.11+ and `pip install -r requirements.txt`. Set `DATABASE_URL=sqlite:///./data/app.db`, `CHROMA_PERSIST_DIR=./data/chroma`. The existing `vinfast_knowledge_base` collection is used without re-ingestion. Its default ONNX embedding model must be installed/cached by the data pipeline. Missing/unavailable retrieval falls back to NO_SOURCE.

Gemini uses the existing `GOOGLE_API_KEY` and `MODEL_NAME`; the local environment was verified on 2026-10-03 with `MODEL_NAME=gemini-3.8-flash` after the provider rejected `gemini-2.5-flash` as unavailable to new users. Secrets remain in ignored `.env`. `AGENT_LLM_ENABLED=false` enables deterministic triage and extractive RAG. Online structured calls have an eight-second deadline and safe fallback. Prompts and pinned policy are in `prompts/`; changes must record actual evidence in `version_log.csv`.

Set distinct random `CUSTOMER_DEMO_TOKEN` and `STAFF_DEMO_TOKEN` values, then use `Authorization: Bearer <token>`. This is a demo identity adapter, not production login/OTP or real VinFast ownership verification. Each token represents one demo account. Backend owners can replace `optional_principal` with their trusted auth dependency. Do not send roles/customer IDs in chat bodies.

`POST /api/v1/chat` and `/public/chat` allow Guests. A server-issued HTTP-only cookie fixes the Guest session/quota across requests. `/customer/chat` requires Customer auth. Send the returned `session_id` for subsequent Customer turns; the backend reloads facts and counters from SQLite. The legacy `response` and empty `analysis` fields remain; no internal reasoning is returned. Staff preview through `/chat` does not create Customer cases.

Customer case endpoints enforce ownership. Staff queue/detail/action endpoints enforce Staff role. Resolve moves `In Progress → Resolved`; customer confirmation moves `Resolved → Closed` or `Reopened`. Case creation, brief and messages commit together. Concurrent session writes are rejected with 409 rather than overwriting a newer turn.

Location is optional through `/customer/location`; manual location discards GPS and NOT_SHARED clears it. Service point search returns three to five matching points when available, up to five otherwise. `fixtures/service_points.demo.json` contains clearly labeled fictional seed points; it is not a live directory or dispatch service. No EXIF/location extraction, OCR or vision is implemented.

SQLite stores sanitized state/messages/fact history and node traces. Replay means playback of recorded inputs/outputs with prompt hashes; it does not rerun nondeterministic Gemini or live tools. Unknown token usage/cost is null. Gemini usage is recorded when the provider supplies it. Optional `langfuse>=3,<4` callbacks degrade to local tracing when unavailable. Trace-write failures must not suppress emergency replies.

## Verify

`python -m pytest tests/ -q` runs offline regression tests with isolated SQLite databases and no Gemini/network requirement.

On this Windows checkout the local venv was repaired to use the available bundled Python 3.12.14. A reproducible sandbox command is `.venv\Scripts\python.exe -m pytest tests/ -q -p no:cacheprovider --basetemp=.test-runs/verification-YYYYMMDD`. Use a fresh test directory for each run.

`python scripts/run_agent_eval.py --offline` evaluates 30 triage and 15 RAG holdout cases against real local Chroma and produces `eval/results/agent/agent_results.json` and `agent_report.md`. Offline disables Gemini, not retrieval. The report uses real routing/review decisions; absent metric samples are N/A. NO_SOURCE compliance includes explicit boundary/safety refusals without citations, recorded separately as `fallback_kind`. Grounding checks source IDs and expected answer keywords, not semantic truth.

The holdout contains labels conflicting with the accepted mandatory HITL policy; do not weaken safety to match those labels. Offline baseline quality is reported honestly; passing unit tests is separate from meeting all benchmark targets. API deployment, production auth and live cloud tracing need environment integration checks.

A live integration run on 2026-10-03 passed connection and structured triage smoke checks. The 45-case online/fallback report is in `eval/results/agent-online/agent_report.md`; a provider recheck confirmed rate limiting, and only six parsed LLM events were recorded during the suite. Online quality targets remain unmet; use the report to distinguish connectivity from readiness.
