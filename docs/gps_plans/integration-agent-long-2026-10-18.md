# GPS integration into feature/agent-long — 2026-10-18

## Provenance and scope

Source: `origin/merge/gps-into-test` at `6a8ae30d0f7fe5919c5368e14c9d095e6e99e38f`.
Target baseline: `feature/agent-long` at `f57f3937759ef6a666bfc58f40881a5b3366299f`.

Applied the GPS changes against the source merge's first-parent baseline `e218ecb` with a three-way patch, selecting GPS application code, API, importer, schema/migration, public fixtures, documentation and tests. This is a scoped integration, not a full merge of unrelated source history, datasets, hooks or project instructions.

`project-overview`, its illustration/mascot assets, thumbnail, presentation components and shared navigation/footer have no diff against the target baseline. Work in the original feature/ui-long checkout was preserved.

## Conflicts and corrections

One file had a Git conflict: `frontend/src/features/chat/hooks/useChat.ts` (two overlapping regions). Resolution preserves guest message-limit handling and adds nearby actions plus stable hydration. There are no unresolved index entries or conflict markers.

Runtime/integration fixes applied while verifying:

- Cancel the pending eight-second timeout after successful browser geolocation. A browser-clock regression reproduced the old behavior before the fix.
- Bind explicit staff/case GPS-sharing consent to the selected case; changing cases cannot write the previous case's coordinates to another case.
- Enforce demo/real scoping and case ownership on the legacy `/api/v1/cases/{case_id}/service-points` endpoint, matching the customer route.
- Normalize nearby seed coordinates for map markers; preserve provided nearby results over case recommendations and keep results from an expanded 100/200 km search.
- Make the nearby-search control reachable on mobile and align stale E2E selectors with the current cards.
- Declare missing importer dependencies (`pandas`, `openpyxl`, `scipy`). Restore the source branch's three public verified-vehicle catalog JSON files, without which the target backend could not import its existing knowledge service.

The case-sharing and map-data regressions fail before their fixes and pass afterwards. Independent read-only review confirmed the four final lifecycle/map findings resolved.

## Verification

All backend tests use temporary SQLite databases and disable LLM/tracing. Browser GPS uses synthetic coordinates, never the device's actual location. No remote database was modified.

| Check | Result |
| --- | --- |
| Frontend production build, including type checking | PASS (existing lint warnings remain) |
| Frontend Node tests | 177 passed |
| GPS backend tests | 90 passed, 3 skipped |
| GPS E2E against production build, Edge, widths 375/1440 | 18 passed, 6 skipped |
| New GPS regression harness tests | 8 passed, included in the Node total |
| Alembic upgrade on an empty temporary SQLite DB | PASS; revision `3d01_service_points` |
| Project-overview regression | 23 passed initially; the sole desktop CTA timing failure passed on isolated rerun |
| Git conflict and whitespace checks | PASS |

E2E covers deliberate GPS consent, keeping successful coordinates beyond eight seconds, manual reference areas without invented GPS, stop sharing, denied permission, timeout, stale callbacks/responses, network retry, login/FAQ/reload without a GPS prompt, and logout clearing consent.

Commands (from `frontend`, with frontend/backend test servers already running):

```powershell
npm test
npm run build
$env:GPS_QA_BASE_URL='http://127.0.0.1:3018'
$env:QA_BROWSER_CHANNEL='msedge'
npx playwright test -c playwright.gps.config.ts
```

Local ignored evidence is in `.test-runs/gps-backend-tests.log`, `gps-node-tests.log`, `gps-production-build.log`, `gps-production-e2e.log`, `gps-migration.log`, `gps-review-red.log`, `gps-review-green.log` and `gps-browser/`.

## Remaining external requirements

The source branch deliberately removed `fixtures/gps/service_points.snapshot.csv.gz`; `data/crawl/` is not committed either. The three backend skips are the two snapshot checks and the full crawl import check. An empty service-point DB therefore uses clearly labelled demo fallback, not a verified nationwide catalog. Production requires importing the actual service-point data using the staging import guide.

The six browser skips require the full catalog (snapshot/Hue searches) and/or a valid `NEXT_PUBLIC_VIETMAP_API_KEY` (tile/marker rendering). Real Vietmap tiles, full-catalog nationwide accuracy and physical-device location have not been verified. The marker coordinate contract and expanded result preservation are covered by runtime component tests; this does not establish live map-provider availability.

No production deployment or remote GPS data import was performed.
