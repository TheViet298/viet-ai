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
