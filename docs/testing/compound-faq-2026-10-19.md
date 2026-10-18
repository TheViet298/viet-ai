# Compound FAQ regression audit — 2026-10-19

Branch: `viet-ai/test/agent-long`.

## Scope and findings

The original two quick-reply templates worked, but related questions could lose
subquestions or qualifiers. The initial regression batch reproduced 17 failures.
The unchanged backend baseline was 1,369 passed, one skipped, and six subtests passed.

Fixes cover charging instructions, charging tariffs, charging app features,
battery/vehicle warranty and maintenance. Two to five recognized topics are
handled independently, with an additional explicit question retained separately.
The existing sales, incident, emergency, booking and authorization flows remain
the authority for their actions.

| Boundary | Regression checks |
| --- | --- |
| Decomposition | Pairs, all five topics, duplicated questions, uppercase, unaccented Vietnamese, line breaks |
| Scope | Different models in different clauses; model year, mileage, commercial use, free-charging conditions |
| Specific questions | Ownership transfer, water damage, battery degradation and app reservations cannot be answered by a generic overview |
| Evidence | Independent citations; one failed lookup preserves the other answers; an answer with no sources does not claim to come from documentation |
| Budget | One shared turn deadline; an expired or exhausted deadline starts no further lookups |
| Safety | A current smoke/fire report takes priority; denied hazards do not invent an emergency |
| Actions | Warranty plus booking instructions keeps both requests and does not confirm a booking |
| English | Natural variants, scoped models, explicit exclusions, preservation of unrecognized qualifiers, translated partial answers |
| Conversation context | A single-topic prefix cannot introduce an unrequested topic into a compound question |

## Reproduce

```powershell
python -m pytest tests/test_agents/test_compound_faq_regressions.py tests/test_api/test_bilingual_chat_contract.py -q
python -m pytest -q
```

Tests use isolated SQLite databases and disable model calls through the existing
fixtures. This verifies application behavior independently of provider availability.
Unknown English qualifiers still require the existing guarded semantic translation
path; they are retained rather than discarded.

Local run logs are ignored under `.test-runs/compound-*.log`. These are automated
backend/API checks, not a deployed-provider or production-data audit.

## Final verification

- Added 49 regression cases for compound questions and bilingual API behavior.
- FAQ regressions, bilingual API checks and golden cases: **138 passed**.
- Full suite on the latest remote base (`a9e4d79`) plus these fixes:
  **1,497 passed, 4 skipped, 8 failed**, with six subtests passed.
- All eight failures were reproduced on an untouched archive of `a9e4d79`
  (8 failed, 15 passed in the affected test files). Seven concern observability
  root/usage accounting; one concerns a vehicle-context test double's positional
  argument signature. They are existing failures, not resolved by this FAQ patch.
- Local browser checks submitted one five-topic question in Vietnamese and
  English. Both displayed five answer sections and the corresponding sources.
  Screenshots are saved locally under `.test-runs/compound-five-*.jpg`.
- Automated model calls are mocked; these results do not certify live provider
  availability or a deployed environment. No coverage percentage was measured.

The remote branch was externally rewritten during this audit. Integration uses
its new `a9e4d79` base and reapplies only the charging, warranty, English and
compound-FAQ changes. The PostgreSQL tracer fix is preserved. Baseline comparison
logs are `.test-runs/baseline-confirmed-v2.log`; final targeted results are in
`.test-runs/faq-final-v2.log`, and the full suite log is
`.test-runs/compound-remote-final.log`.

## Input-language response policy

Responses now follow the detected language of each incoming message, regardless
of the selected VI/EN locale. An explicit request to answer in a language still
wins. For language-neutral input such as `VF8?` or `Plus?`, the selected locale
(or the previous conversation language when absent) supplies the fallback.

Regression checks cover both mismatched UI/input directions, compound questions
in both languages, explicit language requests, neutral short follow-ups and an
English → Vietnamese → English conversation with persisted reply languages.
Before the fix, 10 checks failed against the requested behavior. After the fix,
the language/API/compound regression group passes all 122 checks. Logs are
`.test-runs/language-input-red.log` and
`.test-runs/language-input-targeted-final.log`.

Full-suite verification after this policy change: **1,511 passed, 4 skipped,
8 failed**, with six subtests passed. The eight failing tests are the same
baseline failures listed above; no additional failing test was introduced.
Full log: `.test-runs/language-input-full.log`.
